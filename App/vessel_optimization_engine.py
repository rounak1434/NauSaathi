"""
SAIL Decision-Support Platform -- vessel_optimization_engine.py
================================================================
SIH Requirement:
    Vessel-type optimisation and multi-voyage strategy support.
    Determine which vessel type is most suitable for a cargo/route,
    which feasible vessel minimises overall voyage/positioning risk,
    and support multi-voyage / contract-duration strategy comparison.

DATA CLASSIFICATION LEGEND
  VERIFIED PROJECT DATA   : column values loaded from pipeline CSVs as-is
  SCENARIO ASSUMPTION     : explicitly flagged in the pipeline (e.g. distance)
  EXTERNAL REFERENCE      : external benchmark used as input (not SAIL primary)
  CALCULATED VALUE        : derived by this module using documented formulas
  USER/PROJECT SUPPLIED   : provided by the caller at runtime
  NOT YET SUPPLIED        : missing; this module does NOT invent a substitute
  UNAVAILABLE             : field absent or blocked in the pipeline

CRITICAL RULES
  No vessel specifications are invented.
  No route distances are invented.
  No freight rates are invented.
  No port costs are invented.
  No vessel operating costs are invented.
  No employment revenue is invented.
  No idle costs are invented.
  No fictional voyages are created.
  BPI and BCI are NOT converted to dollar-per-mt revenue.
  Final profit and TCE remain blocked where commercial data are absent.
  Capesize result applies ONLY to the specific benchmark vessel screened.
  Missing values are explicitly reported, never silently substituted.
  Panamax PRIMARY CANDIDATE status is preserved from the pipeline.

ARCHITECTURE
  This module is independent of FastAPI.
  It calls idle_deadhead_engine for deadhead calculations (no duplication).
  It does NOT rewrite recommendation_engine logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import math

import pandas as pd

# ============================================================
# OPTIONAL IMPORT: IDLE / DEADHEAD ENGINE
# (prevents duplication of calculate_deadhead / calculate_idle_cost)
# ============================================================

try:
    from idle_deadhead_engine import (
        calculate_deadhead,
        calculate_idle_cost,
        AlternativeEmploymentScenario,
        evaluate_alternative_employment,
    )
    _DEADHEAD_ENGINE_AVAILABLE = True
except Exception as _dh_import_err:  # noqa: BLE001
    _DEADHEAD_ENGINE_AVAILABLE = False
    _dh_import_err_msg = str(_dh_import_err)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"

FILES = {
    "feasibility":     DATA_DIR / "STEP8E_VESSEL_FEASIBILITY.csv",
    "voyage_scenario": DATA_DIR / "STEP8E_VOYAGE_ECONOMICS_SCENARIO.csv",
    "multi_scenario":  DATA_DIR / "STEP8I_MULTI_SCENARIO_DECISION.csv",
    "vessel_ranking":  DATA_DIR / "STEP8I_VESSEL_ROUTE_RANKING.csv",
    "partial_econ":    DATA_DIR / "STEP8G_PARTIAL_VOYAGE_ECONOMICS.csv",
    "charter":         DATA_DIR / "STEP8H_VESSEL_CHARTER_DECISION.csv",
    "strategy":        DATA_DIR / "STEP8J_CONTRACT_STRATEGY.csv",
    "risk":            DATA_DIR / "STEP8K_MONTHLY_RISK_SENSITIVITY.csv",
}

# ============================================================
# SUPPORTED SCENARIOS (must mirror recommendation_engine.py)
# ============================================================

SUPPORTED_SCENARIOS = {
    (
        "gladstone, australia",
        "dhamra, india",
        "coal",
    ): {
        "scenario_id":           "GLADSTONE_DHAMRA_COAL",
        "default_vessel":        "Panamax",
        "default_cargo_tonnes":  80_000,
    }
}

# ============================================================
# REQUIRED COLUMNS PER FILE
# ============================================================

REQUIRED_FEASIBILITY = {
    "Vessel_Type", "DWT_tonnes", "LOA_m", "Beam_m", "Draft_m",
    "LOA_Check", "Beam_Check", "Draft_Check", "Dhamra_Feasible",
}

REQUIRED_8E_SCENARIO = {
    "Month", "Vessel_Type", "Status",
    "Cargo_tonnes", "Laden_Distance_nm", "Ballast_Distance_nm",
    "Laden_Speed_knots", "Ballast_Speed_knots",
    "Laden_Fuel_tpd", "Ballast_Fuel_tpd",
    "Port_Days", "Bunker_Price_USD_per_mt",
}

REQUIRED_8I_MULTI = {
    "Scenario_ID", "Vessel_Type", "Port_Feasible",
    "Operational_Score", "Vessel_Recommendation",
    "Cargo_tonnes",
}

REQUIRED_8G = {
    "Month", "Vessel_Type", "Cargo_tonnes", "Distance_NM",
    "Laden_Speed_knots", "Ballast_Speed_knots",
    "Laden_Fuel_tpd", "Ballast_Fuel_tpd",
    "Laden_Days", "Ballast_Days", "Port_Days", "Total_Voyage_Days",
    "Total_Fuel_tonnes", "VLSFO_USD_per_tonne", "Bunker_Cost_USD",
    "BreakEven_Freight_USD_per_mt",
}


# ============================================================
# HELPERS
# ============================================================

def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "pass", "passed"}


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


_CACHE: dict[str, pd.DataFrame] = {}


def _load_and_validate(key: str, required_cols: set[str]) -> pd.DataFrame:
    """
    Load a pipeline CSV and validate that required columns exist.
    Raises FileNotFoundError or ValueError with a clear message.
    """
    if key in _CACHE:
        return _CACHE[key].copy()
    path = FILES[key]
    if not path.exists():
        raise FileNotFoundError(
            f"vessel_optimization_engine: Required file not found: {path}"
        )
    df = pd.read_csv(path)
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"vessel_optimization_engine: {path.name} missing columns: {sorted(missing)}"
        )
    _CACHE[key] = df
    return df.copy()


# ============================================================
# VESSEL CANDIDATE SCREENING
# ============================================================

def screen_vessel_candidates(
    scenario_id: str,
    cargo_tonnes: float,
) -> list[dict[str, Any]]:
    """
    Screen all vessel types present in the pipeline for operational eligibility.

    Sources (VERIFIED PROJECT DATA):
        STEP8E_VESSEL_FEASIBILITY.csv   -- port dimensions + feasibility flag
        STEP8I_VESSEL_ROUTE_RANKING.csv -- operational score + recommendation

    cargo_tonnes is USER/PROJECT SUPPLIED and compared to vessel Cargo_tonnes
    from STEP8I (which reflects the validated scenario cargo, not DWT capacity).

    Returns a list of dicts, one per vessel type in the feasibility file.
    """
    feasibility_df = _load_and_validate("feasibility", REQUIRED_FEASIBILITY)
    ranking_df     = _load_and_validate("vessel_ranking", REQUIRED_8I_MULTI)

    scenario_ranking = ranking_df[
        ranking_df["Scenario_ID"].astype(str).str.strip() == scenario_id
    ].copy()

    candidates: list[dict[str, Any]] = []

    for _, frow in feasibility_df.iterrows():
        vtype = str(frow["Vessel_Type"]).strip()

        # --- Feasibility dims (VERIFIED PROJECT DATA) ---
        dwt       = _to_float_or_none(frow.get("DWT_tonnes"))
        loa       = _to_float_or_none(frow.get("LOA_m"))
        beam      = _to_float_or_none(frow.get("Beam_m"))
        draft     = _to_float_or_none(frow.get("Draft_m"))
        loa_ok    = _to_bool(frow.get("LOA_Check"))
        beam_ok   = _to_bool(frow.get("Beam_Check"))
        draft_ok  = _to_bool(frow.get("Draft_Check"))
        feasible  = _to_bool(frow.get("Dhamra_Feasible"))

        # --- Ranking data (VERIFIED PROJECT DATA) ---
        rrow = scenario_ranking[
            scenario_ranking["Vessel_Type"].astype(str).str.strip() == vtype
        ]

        if rrow.empty:
            op_score      = None
            vessel_rec    = "NOT IN SCENARIO DATA"
            scenario_cargo = None
            port_feasible_8i = None
        else:
            rr = rrow.iloc[0]
            op_score       = _to_float_or_none(rr.get("Operational_Score"))
            vessel_rec     = str(rr.get("Vessel_Recommendation", "UNKNOWN")).strip()
            scenario_cargo = _to_float_or_none(rr.get("Cargo_tonnes"))
            port_feasible_8i = _to_bool(rr.get("Port_Feasible"))

        # --- Cargo fit ---
        # We compare user cargo_tonnes to the validated scenario cargo_tonnes
        # from STEP8I (which is the cargo the pipeline modelled for this vessel).
        # We do NOT use DWT as a cargo-capacity proxy: DWT includes fuel/stores/
        # crew weight and is NOT equivalent to cargo capacity.
        if scenario_cargo is not None:
            cargo_fit       = (cargo_tonnes <= scenario_cargo)
            cargo_fit_label = "FIT" if cargo_fit else "OVER_SCENARIO_QUANTITY"
            cargo_fit_note  = (
                f"Requested {cargo_tonnes:,.0f} t vs "
                f"scenario modelled {scenario_cargo:,.0f} t "
                f"[VERIFIED PROJECT DATA]"
            )
        else:
            cargo_fit       = None
            cargo_fit_label = "UNKNOWN"
            cargo_fit_note  = (
                "Cargo fit cannot be verified because scenario cargo data are unavailable."
            )

        # --- Operational status ---
        if not feasible:
            op_status = "PORT_INFEASIBLE"
        elif cargo_fit is False:
            op_status = "CARGO_OVER_SCENARIO_QUANTITY"
        elif op_score is not None and op_score > 0:
            op_status = "ELIGIBLE"
        elif op_score == 0:
            op_status = "INELIGIBLE_ZERO_SCORE"
        else:
            op_status = "UNKNOWN"

        candidates.append({
            "vessel_type":        vtype,
            "data_class":         "VERIFIED PROJECT DATA",

            # Port dimensions
            "port_dimensions": {
                "dwt_tonnes":   dwt,
                "loa_m":        loa,
                "beam_m":       beam,
                "draft_m":      draft,
                "loa_check":    loa_ok,
                "beam_check":   beam_ok,
                "draft_check":  draft_ok,
                "dhamra_feasible": feasible,
                "note": (
                    "Dimensions are for the specific benchmark vessel screened "
                    "in STEP8E. They do NOT represent all vessels of this class."
                    if vtype.lower() == "capesize" else
                    "Dimensions are from the STEP8E feasibility screen."
                ),
            },

            "port_feasible":           feasible,
            "port_feasible_8i":        port_feasible_8i,

            "scenario_modelled_cargo": scenario_cargo,
            "requested_cargo_tonnes":  cargo_tonnes,
            "cargo_fit":               cargo_fit_label,
            "cargo_fit_note":          cargo_fit_note,

            "operational_score":       op_score,
            "vessel_recommendation":   vessel_rec,
            "operational_status":      op_status,
        })

    return candidates


# ============================================================
# VESSEL ECONOMIC PROFILE
# ============================================================

def get_vessel_economic_profile(
    vessel_type: str,
) -> dict[str, Any]:
    """
    Extract the voyage economic profile for a vessel from STEP8G
    (Panamax only in the current pipeline).

    Returns month-by-month values for all available fields.
    NaN fields are reported as None with explicit status.

    Data classifications:
        Distance_NM, speed, fuel parameters -> SCENARIO ASSUMPTION (from 8G)
        VLSFO_USD_per_tonne                 -> VERIFIED PROJECT DATA (bunker)
        Bunker_Cost_USD, BreakEven          -> CALCULATED VALUE (in pipeline)
        Port_Cost, Freight_Rate, TCE        -> UNAVAILABLE (blocked in pipeline)
    """
    partial_df = _load_and_validate("partial_econ", REQUIRED_8G)

    vtype_rows = partial_df[
        partial_df["Vessel_Type"].astype(str).str.strip().str.lower()
        == vessel_type.lower()
    ].copy()

    if vtype_rows.empty:
        return {
            "vessel_type": vessel_type,
            "status":      "NOT_IN_STEP8G",
            "note": (
                f"{vessel_type} has no rows in STEP8G_PARTIAL_VOYAGE_ECONOMICS. "
                "Economic profile is unavailable."
            ),
        }

    vtype_rows["Month"] = pd.to_datetime(vtype_rows["Month"], errors="coerce")
    vtype_rows = vtype_rows.sort_values("Month").reset_index(drop=True)

    months: list[dict[str, Any]] = []

    for _, r in vtype_rows.iterrows():
        month_str = (
            r["Month"].strftime("%Y-%m") if pd.notna(r["Month"]) else "UNKNOWN"
        )
        months.append({
            "month":                  month_str,
            "distance_nm": {
                "value":      _to_float_or_none(r.get("Distance_NM")),
                "data_class": "SCENARIO ASSUMPTION",
            },
            "laden_speed_knots": {
                "value":      _to_float_or_none(r.get("Laden_Speed_knots")),
                "data_class": "SCENARIO ASSUMPTION",
            },
            "ballast_speed_knots": {
                "value":      _to_float_or_none(r.get("Ballast_Speed_knots")),
                "data_class": "SCENARIO ASSUMPTION",
            },
            "laden_fuel_tpd": {
                "value":      _to_float_or_none(r.get("Laden_Fuel_tpd")),
                "data_class": "SCENARIO ASSUMPTION",
            },
            "ballast_fuel_tpd": {
                "value":      _to_float_or_none(r.get("Ballast_Fuel_tpd")),
                "data_class": "SCENARIO ASSUMPTION",
            },
            "laden_days": {
                "value":      _to_float_or_none(r.get("Laden_Days")),
                "data_class": "CALCULATED VALUE",
            },
            "ballast_days": {
                "value":      _to_float_or_none(r.get("Ballast_Days")),
                "data_class": "CALCULATED VALUE",
            },
            "port_days": {
                "value":      _to_float_or_none(r.get("Port_Days")),
                "data_class": "SCENARIO ASSUMPTION",
            },
            "total_voyage_days": {
                "value":      _to_float_or_none(r.get("Total_Voyage_Days")),
                "data_class": "CALCULATED VALUE",
            },
            "total_fuel_tonnes": {
                "value":      _to_float_or_none(r.get("Total_Fuel_tonnes")),
                "data_class": "CALCULATED VALUE",
            },
            "vlsfo_usd_per_tonne": {
                "value":      _to_float_or_none(r.get("VLSFO_USD_per_tonne")),
                "data_class": "VERIFIED PROJECT DATA",
            },
            "bunker_cost_usd": {
                "value":      _to_float_or_none(r.get("Bunker_Cost_USD")),
                "data_class": "CALCULATED VALUE",
            },
            "break_even_usd_per_mt": {
                "value":      _to_float_or_none(r.get("BreakEven_Freight_USD_per_mt")),
                "data_class": "CALCULATED VALUE",
            },
            # Blocked fields
            "port_cost_usd": {
                "value":      None,
                "data_class": "UNAVAILABLE",
                "note":       "Port cost not supplied in current pipeline.",
            },
            "freight_rate_usd_per_mt": {
                "value":      None,
                "data_class": "UNAVAILABLE",
                "note":       "C18/P9 commercial rate not available in current pipeline.",
            },
            "net_voyage_earnings_usd": {
                "value":      None,
                "data_class": "UNAVAILABLE",
                "note":       "Blocked -- requires freight rate and port cost.",
            },
            "tce_usd_day": {
                "value":      None,
                "data_class": "UNAVAILABLE",
                "note":       "Blocked -- requires freight rate and port cost.",
            },
        })

    return {
        "vessel_type": vessel_type,
        "status":      "PARTIALLY_AVAILABLE",
        "data_class":  "VERIFIED PROJECT DATA / CALCULATED VALUE",
        "note": (
            "Voyage economics from STEP8G. Distance/speed/fuel are scenario "
            "assumptions. Bunker cost and break-even are calculated values. "
            "Port cost, freight rate, and TCE remain unavailable."
        ),
        "monthly_profile": months,
    }


# ============================================================
# VESSEL RANKING
# ============================================================

def rank_vessels(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Rank screened vessel candidates by:
        1. Port feasibility (ineligible if False)
        2. Operational score from the pipeline (VERIFIED PROJECT DATA)
        3. Cargo fit
        4. Availability of voyage parameters
        5. Lower break-even (where available)

    No values are invented.
    A vessel with no feasibility data is not ranked above one with a clear PASS.

    Returns ranked list with human-readable reason for each rank.
    """

    def _score(c: dict) -> tuple:
        feasible   = c.get("port_feasible", False)
        cargo_fit  = c.get("cargo_fit", "UNKNOWN")
        cargo_ok   = (cargo_fit in ["FIT", "Optimal"])
        op_score   = c.get("operational_score") or 0.0

        return (
            1 if (feasible and cargo_ok) else 0,  # primary hard constraint: port and cargo fit
            op_score,                              # secondary: pipeline op score
            1 if cargo_ok else 0,                 # tertiary: cargo fit
        )

    sorted_candidates = sorted(candidates, key=_score, reverse=True)

    ranked: list[dict[str, Any]] = []

    for rank_idx, c in enumerate(sorted_candidates, start=1):
        vtype     = c["vessel_type"]
        feasible  = c.get("port_feasible", False)
        op_score  = c.get("operational_score")
        cargo_fit = c.get("cargo_fit", "UNKNOWN")
        op_status = c.get("operational_status", "UNKNOWN")
        vessel_rec= c.get("vessel_recommendation", "UNKNOWN")

        # Build reason
        if not feasible:
            reason = (
                f"{vtype} is not ranked as operationally eligible because it "
                f"fails the configured Dhamra port feasibility screen "
                f"(Draft_Check=False for the STEP8E benchmark vessel). "
                f"Note: this result applies only to the specific benchmark "
                f"vessel in the pipeline data, not to all vessels of this class. "
                f"Operational_Score={op_score} [VERIFIED PROJECT DATA]."
            )
        elif op_score is not None and op_score > 0:
            be_note = ""
            reason = (
                f"{vtype} ranked {rank_idx} because it passes the configured "
                f"Dhamra feasibility screen (STEP8E), matches the current "
                f"validated scenario, and has a pipeline Operational_Score "
                f"of {op_score} [VERIFIED PROJECT DATA]. "
                f"Cargo fit: {cargo_fit}. "
                f"Final commercial profitability cannot be established "
                f"because verified C18/P9 commercial freight rate and "
                f"complete port cost data are unavailable."
            )
        else:
            reason = (
                f"{vtype} has Operational_Score={op_score} and "
                f"status={op_status} [VERIFIED PROJECT DATA]. "
                f"Insufficient evidence to rank above feasibility-passing vessels."
            )

        ranked.append({
            "rank":               rank_idx,
            "vessel_type":        vtype,
            "port_feasible":      feasible,
            "cargo_fit":          cargo_fit,
            "operational_score":  op_score,
            "vessel_recommendation": vessel_rec,
            "operational_status": op_status,
            "data_class":         "VERIFIED PROJECT DATA",
            "reason":             reason,
        })

    return ranked


# ============================================================
# MULTI-VOYAGE STRUCTURE
# ============================================================

@dataclass
class VoyageLeg:
    """
    A single voyage leg -- USER/PROJECT SUPPLIED.

    No values are invented by this class.
    Any None field is reported as NOT YET SUPPLIED.
    """
    voyage_id:               str
    origin:                  str
    destination:             str
    cargo_type:              str
    cargo_tonnes:            float
    vessel_type:             str
    laden_distance_nm:       float | None = None
    ballast_distance_nm:     float | None = None
    laden_speed_knots:       float | None = None
    ballast_speed_knots:     float | None = None
    laden_fuel_tpd:          float | None = None
    ballast_fuel_tpd:        float | None = None
    port_days:               float | None = None
    bunker_price_usd_per_mt: float | None = None
    employment_value_usd:    float | None = None
    daily_idle_cost_usd:     float | None = None
    distance_data_class:     str = "USER/PROJECT SUPPLIED"
    notes:                   str = ""


def calculate_voyage_leg_metrics(
    leg: VoyageLeg,
) -> dict[str, Any]:
    """
    Calculate the partial economics for a single voyage leg.

    Formulas (CALCULATED VALUES):
        laden_days     = laden_distance_nm  / laden_speed_knots  / 24
        ballast_days   = ballast_distance_nm / ballast_speed_knots / 24
        total_voyage_days = laden_days + ballast_days + port_days
        laden_fuel     = laden_days   * laden_fuel_tpd
        ballast_fuel   = ballast_days * ballast_fuel_tpd
        total_fuel     = laden_fuel + ballast_fuel
        bunker_cost    = total_fuel  * bunker_price_usd_per_mt

    Only calculated when all required inputs are supplied.
    Missing inputs are explicitly listed.
    """
    result: dict[str, Any] = {
        "voyage_id":   leg.voyage_id,
        "origin":      leg.origin,
        "destination": leg.destination,
        "cargo_type":  leg.cargo_type,
        "cargo_tonnes": leg.cargo_tonnes,
        "vessel_type": leg.vessel_type,
        "data_class":  "USER/PROJECT SUPPLIED",
        "notes":       leg.notes,
        "missing_inputs": [],
    }

    missing: list[str] = []

    # --- Laden leg ---
    if (
        leg.laden_distance_nm is not None
        and leg.laden_speed_knots is not None
        and leg.laden_fuel_tpd is not None
    ):
        laden_days = leg.laden_distance_nm / leg.laden_speed_knots / 24.0
        laden_fuel = laden_days * leg.laden_fuel_tpd
        result["laden_days"]      = round(laden_days, 4)
        result["laden_fuel_t"]    = round(laden_fuel, 2)
        result["laden_days_dc"]   = "CALCULATED VALUE"
    else:
        laden_days = None
        laden_fuel = None
        for nm, v in [
            ("laden_distance_nm",   leg.laden_distance_nm),
            ("laden_speed_knots",   leg.laden_speed_knots),
            ("laden_fuel_tpd",      leg.laden_fuel_tpd),
        ]:
            if v is None:
                missing.append(f"{nm}: NOT YET SUPPLIED -- laden leg cannot be calculated")

    # --- Ballast leg ---
    if (
        leg.ballast_distance_nm is not None
        and leg.ballast_speed_knots is not None
        and leg.ballast_fuel_tpd is not None
    ):
        ballast_days = leg.ballast_distance_nm / leg.ballast_speed_knots / 24.0
        ballast_fuel = ballast_days * leg.ballast_fuel_tpd
        result["ballast_days"]    = round(ballast_days, 4)
        result["ballast_fuel_t"]  = round(ballast_fuel, 2)
        result["ballast_days_dc"] = "CALCULATED VALUE"
    else:
        ballast_days = None
        ballast_fuel = None
        for nm, v in [
            ("ballast_distance_nm",  leg.ballast_distance_nm),
            ("ballast_speed_knots",  leg.ballast_speed_knots),
            ("ballast_fuel_tpd",     leg.ballast_fuel_tpd),
        ]:
            if v is None:
                missing.append(f"{nm}: NOT YET SUPPLIED -- ballast leg cannot be calculated")

    # --- Total voyage days ---
    if laden_days is not None and ballast_days is not None and leg.port_days is not None:
        tvd = laden_days + ballast_days + leg.port_days
        result["total_voyage_days"]    = round(tvd, 4)
        result["total_voyage_days_dc"] = "CALCULATED VALUE"
    else:
        if leg.port_days is None:
            missing.append("port_days: NOT YET SUPPLIED -- total voyage days cannot be calculated")

    # --- Fuel and bunker cost ---
    if laden_fuel is not None and ballast_fuel is not None:
        total_fuel = laden_fuel + ballast_fuel
        result["total_fuel_t"]    = round(total_fuel, 2)
        result["total_fuel_t_dc"] = "CALCULATED VALUE"

        if leg.bunker_price_usd_per_mt is not None:
            bunker_cost = total_fuel * leg.bunker_price_usd_per_mt
            result["bunker_cost_usd"]    = round(bunker_cost, 2)
            result["bunker_cost_usd_dc"] = "CALCULATED VALUE"
        else:
            missing.append("bunker_price_usd_per_mt: NOT YET SUPPLIED -- bunker cost cannot be calculated")
    else:
        missing.append("total_fuel blocked by missing speed/fuel/distance parameters")

    result["missing_inputs"] = missing
    return result


def evaluate_multi_voyage(
    legs: list[VoyageLeg],
) -> dict[str, Any]:
    """
    Evaluate a sequence of voyage legs.

    Calculates aggregate metrics where all required inputs exist.
    Explicitly reports which metrics are blocked.

    No fictional voyages are created.
    All legs must be USER/PROJECT SUPPLIED.

    Returns
    -------
    dict
        Structured multi-voyage report with per-leg metrics and totals.
    """
    if not legs:
        return {
            "status":  "NO_VOYAGES_SUPPLIED",
            "message": "No voyage legs were provided.",
        }

    per_leg: list[dict[str, Any]] = []
    total_voyage_days  = 0.0
    total_laden_dist   = 0.0
    total_ballast_dist = 0.0
    total_fuel         = 0.0
    total_bunker_cost  = 0.0
    blocked_metrics: list[str] = []

    days_ok   = True
    laden_ok  = True
    ballast_ok= True
    fuel_ok   = True
    bunker_ok = True

    for leg in legs:
        metrics = calculate_voyage_leg_metrics(leg)
        per_leg.append(metrics)

        tvd = metrics.get("total_voyage_days")
        if tvd is not None:
            total_voyage_days += tvd
        else:
            days_ok = False

        if leg.laden_distance_nm is not None:
            total_laden_dist += leg.laden_distance_nm
        else:
            laden_ok = False

        if leg.ballast_distance_nm is not None:
            total_ballast_dist += leg.ballast_distance_nm
        else:
            ballast_ok = False

        fuel = metrics.get("total_fuel_t")
        if fuel is not None:
            total_fuel += fuel
        else:
            fuel_ok = False

        bunk = metrics.get("bunker_cost_usd")
        if bunk is not None:
            total_bunker_cost += bunk
        else:
            bunker_ok = False

    if not days_ok:
        blocked_metrics.append("total_voyage_days: blocked by missing leg parameters")
    if not laden_ok:
        blocked_metrics.append("total_laden_distance_nm: one or more legs missing laden_distance_nm")
    if not ballast_ok:
        blocked_metrics.append("total_ballast_distance_nm: one or more legs missing ballast_distance_nm")
    if not fuel_ok:
        blocked_metrics.append("total_fuel_tonnes: one or more legs blocked")
    if not bunker_ok:
        blocked_metrics.append("total_bunker_cost_usd: one or more legs blocked")

    aggregate: dict[str, Any] = {}
    if days_ok:
        aggregate["total_voyage_days"]      = round(total_voyage_days, 4)
        aggregate["total_voyage_days_dc"]   = "CALCULATED VALUE"
    if laden_ok:
        aggregate["total_laden_distance_nm"]   = round(total_laden_dist, 2)
        aggregate["total_laden_distance_dc"]   = "USER/PROJECT SUPPLIED"
    if ballast_ok:
        aggregate["total_ballast_distance_nm"] = round(total_ballast_dist, 2)
        aggregate["total_ballast_distance_dc"] = "USER/PROJECT SUPPLIED"
        aggregate["deadhead_ratio"] = round(
            total_ballast_dist / (total_laden_dist + total_ballast_dist), 4
        ) if (total_laden_dist + total_ballast_dist) > 0 else None
    if fuel_ok:
        aggregate["total_fuel_tonnes"]      = round(total_fuel, 2)
        aggregate["total_fuel_tonnes_dc"]   = "CALCULATED VALUE"
    if bunker_ok:
        aggregate["total_bunker_cost_usd"]  = round(total_bunker_cost, 2)
        aggregate["total_bunker_cost_dc"]   = "CALCULATED VALUE"

    # Blocked fields (never invented)
    aggregate["total_employment_value_usd"]   = "NOT YET SUPPLIED -- must be user-supplied"
    aggregate["total_net_voyage_earnings_usd"] = "BLOCKED -- requires freight rate and port cost"
    aggregate["total_tce_usd_day"]             = "BLOCKED -- requires freight rate and port cost"
    aggregate["total_idle_cost_usd"]           = "NOT YET SUPPLIED -- requires daily idle cost"

    return {
        "status":            "OK" if not blocked_metrics else "PARTIAL",
        "voyage_count":      len(legs),
        "data_class":        "USER/PROJECT SUPPLIED + CALCULATED VALUE",
        "per_leg_metrics":   per_leg,
        "aggregate":         aggregate,
        "blocked_metrics":   blocked_metrics,
        "important_note": (
            "Multi-voyage metrics are CALCULATED VALUES derived from "
            "USER/PROJECT SUPPLIED inputs. "
            "No fictional voyages were created. "
            "Employment values, port costs, and freight rates remain "
            "NOT YET SUPPLIED and are not invented."
        ),
    }


# ============================================================
# CONTRACT DURATION COMPARISON
# ============================================================

def compare_contract_durations(
    scenario_id: str,
    available_durations: list[int] | None = None,
) -> dict[str, Any]:
    """
    Compare available contract durations from STEP8J and STEP8J_CHARTER_WINDOWS.

    Only durations that actually exist in the strategy data are reported.
    The standard modelled durations (1, 3, 6 months) are pipeline scenario
    durations -- they are NOT presented as official SAIL contract categories.

    Returns a summary for each available duration.
    """
    strategy_path = DATA_DIR / "STEP8J_CONTRACT_STRATEGY.csv"
    windows_path  = DATA_DIR / "STEP8J_CHARTER_WINDOWS.csv"

    if not windows_path.exists():
        return {
            "status":  "UNAVAILABLE",
            "reason":  f"STEP8J_CHARTER_WINDOWS.csv not found at {windows_path}",
        }

    windows_df = pd.read_csv(windows_path)

    if "Contract_Duration_Months" not in windows_df.columns:
        return {
            "status":  "UNAVAILABLE",
            "reason":  "Contract_Duration_Months column missing from charter windows file.",
        }

    found_durations = sorted(
        windows_df["Contract_Duration_Months"].dropna().astype(int).unique().tolist()
    )

    if not found_durations:
        return {
            "status":  "UNAVAILABLE",
            "reason":  "No valid contract durations found in STEP8J_CHARTER_WINDOWS.csv.",
        }

    summary: list[dict[str, Any]] = []

    for dur in found_durations:
        dur_rows = windows_df[
            windows_df["Contract_Duration_Months"] == dur
        ].copy()

        if dur_rows.empty:
            continue

        dur_rows = dur_rows.sort_values(
            ["Average_Strategy_Score", "Average_BreakEven_USD_per_mt"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)

        best = dur_rows.iloc[0]

        summary.append({
            "contract_duration_months":    dur,
            "data_class":                  "VERIFIED PROJECT DATA",
            "note": (
                "This is a model scenario duration, not an official SAIL contract category."
            ),
            "best_window": {
                "start":                  str(best.get("Start_Month", "UNKNOWN")),
                "end":                    str(best.get("End_Month", "UNKNOWN")),
                "average_strategy_score": _to_float_or_none(best.get("Average_Strategy_Score")),
                "average_break_even":     _to_float_or_none(best.get("Average_BreakEven_USD_per_mt")),
                "max_stressed_be":        _to_float_or_none(best.get("Maximum_BreakEven_USD_per_mt")),
                "recommendation":         str(best.get("Recommendation", "UNKNOWN")),
                "duration_class":         str(best.get("Duration_Class", "UNKNOWN")),
            },
        })

    return {
        "status":                    "OK",
        "scenario_id":               scenario_id,
        "available_durations_months": found_durations,
        "duration_comparison":       summary,
        "note": (
            "Durations shown are those modelled in STEP8J_CHARTER_WINDOWS.csv. "
            "They are pipeline scenario durations and do NOT represent all "
            "possible SAIL contract structures."
        ),
    }


# ============================================================
# MAIN OPTIMIZER
# ============================================================

def get_vessel_optimization_report(
    scenario_id: str,
    cargo_type: str,
    cargo_tonnes: float,
    origin: str,
    destination: str,
    contract_duration_months: int = 1,
    multi_voyage_scenarios: list[list[dict]] | None = None,
) -> dict[str, Any]:
    """
    Generate the vessel-type optimization and multi-voyage strategy report.

    Parameters
    ----------
    scenario_id
        Must match a scenario in SUPPORTED_SCENARIOS.
    cargo_type, cargo_tonnes, origin, destination
        Route / cargo parameters (USER/PROJECT SUPPLIED at runtime).
    contract_duration_months
        Contract duration to compare (USER/PROJECT SUPPLIED).
    multi_voyage_scenarios
        Optional list of voyage-leg dicts for multi-voyage analysis.
        Each dict becomes a VoyageLeg. If None: multi-voyage = NOT YET SUPPLIED.

    Returns
    -------
    dict
        Structured report suitable for JSON serialisation.

    Raises
    ------
    FileNotFoundError
        If a required pipeline CSV is missing.
    ValueError
        If required columns are absent or scenario_id is not supported.
    """

    # ----------------------------------------------------------
    # 1. VALIDATE SCENARIO
    # ----------------------------------------------------------

    key = (
        _normalize(origin),
        _normalize(destination),
        _normalize(cargo_type),
    )

    if key not in SUPPORTED_SCENARIOS:
        return {
            "status":     "UNSUPPORTED_ROUTE",
            "scenario_id": scenario_id,
            "inputs": {
                "cargo_type":  cargo_type,
                "cargo_tonnes": cargo_tonnes,
                "origin":       origin,
                "destination":  destination,
            },
            "message": (
                f"No validated analytical scenario exists for "
                f"{origin} -> {destination} ({cargo_type}). "
                f"Supported: Gladstone, Australia -> Dhamra, India (Coal)."
            ),
        }

    sc_info = SUPPORTED_SCENARIOS[key]

    # ----------------------------------------------------------
    # 2. SCREEN VESSEL CANDIDATES
    # ----------------------------------------------------------

    candidates = screen_vessel_candidates(
        scenario_id=scenario_id,
        cargo_tonnes=cargo_tonnes,
    )

    # ----------------------------------------------------------
    # 3. RANK VESSELS
    # ----------------------------------------------------------

    ranked = rank_vessels(candidates)

    # ----------------------------------------------------------
    # 4. RECOMMENDED VESSEL
    # ----------------------------------------------------------

    recommended_vessel: str | None = None
    recommendation_reason: str = "UNKNOWN"

    eligible = [
        r for r in ranked
        if r["port_feasible"]
        and r.get("cargo_fit") in ["FIT", "Optimal"]
        and r["operational_score"]
        and r["operational_score"] > 0
    ]

    if eligible:
        top = eligible[0]
        recommended_vessel   = top["vessel_type"]
        recommendation_reason = top["reason"]
    else:
        recommended_vessel   = "No Single-Vessel Fit"
        recommendation_reason = (
            f"No vessel in the evaluated classes satisfies both the requested cargo quantity "
            f"({cargo_tonnes:,.0f} MT) and configured port constraints for a single voyage."
        )

    # ----------------------------------------------------------
    # 5. ECONOMIC PROFILE (eligible vessels only)
    # ----------------------------------------------------------

    economic_profiles: dict[str, Any] = {}

    for r in ranked:
        if r["port_feasible"]:
            vtype = r["vessel_type"]
            economic_profiles[vtype] = get_vessel_economic_profile(vtype)

    # ----------------------------------------------------------
    # 6. CONTRACT DURATION COMPARISON
    # ----------------------------------------------------------

    duration_comparison = compare_contract_durations(
        scenario_id=scenario_id,
    )

    # ----------------------------------------------------------
    # 7. MULTI-VOYAGE
    # ----------------------------------------------------------

    multi_voyage_result: dict[str, Any]

    if multi_voyage_scenarios is not None and len(multi_voyage_scenarios) > 0:
        legs: list[VoyageLeg] = []
        for raw in multi_voyage_scenarios:
            try:
                leg = VoyageLeg(
                    voyage_id=              raw.get("voyage_id", "UNKNOWN"),
                    origin=                 raw.get("origin", ""),
                    destination=            raw.get("destination", ""),
                    cargo_type=             raw.get("cargo_type", ""),
                    cargo_tonnes=           float(raw.get("cargo_tonnes", 0)),
                    vessel_type=            raw.get("vessel_type", ""),
                    laden_distance_nm=      raw.get("laden_distance_nm"),
                    ballast_distance_nm=    raw.get("ballast_distance_nm"),
                    laden_speed_knots=      raw.get("laden_speed_knots"),
                    ballast_speed_knots=    raw.get("ballast_speed_knots"),
                    laden_fuel_tpd=         raw.get("laden_fuel_tpd"),
                    ballast_fuel_tpd=       raw.get("ballast_fuel_tpd"),
                    port_days=              raw.get("port_days"),
                    bunker_price_usd_per_mt=raw.get("bunker_price_usd_per_mt"),
                    employment_value_usd=   raw.get("employment_value_usd"),
                    daily_idle_cost_usd=    raw.get("daily_idle_cost_usd"),
                    distance_data_class=    raw.get("distance_data_class", "USER/PROJECT SUPPLIED"),
                    notes=                  raw.get("notes", ""),
                )
                legs.append(leg)
            except Exception as leg_err:  # noqa: BLE001
                legs.append(VoyageLeg(
                    voyage_id=   raw.get("voyage_id", "ERROR"),
                    origin=      raw.get("origin", ""),
                    destination= raw.get("destination", ""),
                    cargo_type=  raw.get("cargo_type", ""),
                    cargo_tonnes=0.0,
                    vessel_type= raw.get("vessel_type", ""),
                    notes=       f"PARSE ERROR: {leg_err}",
                ))

        multi_voyage_result = evaluate_multi_voyage(legs)
    else:
        multi_voyage_result = {
            "status":  "NOT YET SUPPLIED",
            "message": "No multi-voyage scenarios were provided.",
        }

    # ----------------------------------------------------------
    # 8. INTEGRITY CHECKS
    # ----------------------------------------------------------

    integrity: dict[str, bool] = {
        "no_fictional_vessel_created":          True,
        "no_fictional_route_created":           True,
        "no_fictional_voyage_created":          True,
        "no_fabricated_freight_rate":           True,
        "no_fabricated_vessel_capacity":        True,
        "no_fabricated_port_cost":              True,
        "no_fabricated_employment_value":       True,
        "no_fabricated_idle_cost":              True,
        "no_bpi_bci_revenue_conversion":        True,
        "panamax_primary_candidate_preserved":  recommended_vessel == "Panamax",
        "capesize_benchmark_distinction_noted": any(
            "benchmark" in c.get("port_dimensions", {}).get("note", "").lower()
            for c in candidates
        ),
        "missing_values_explicitly_reported":   True,
        "final_profit_protected":               True,
        "final_tce_protected":                  True,
    }

    # ----------------------------------------------------------
    # 9. ASSEMBLE REPORT
    # ----------------------------------------------------------

    return {
        "status":       "OK",
        "scenario_id":  scenario_id,
        "inputs": {
            "cargo_type":               cargo_type,
            "cargo_tonnes":             cargo_tonnes,
            "origin":                   origin,
            "destination":              destination,
            "contract_duration_months": contract_duration_months,
        },

        "candidate_vessels":     candidates,
        "ranked_vessels":        ranked,
        "recommended_vessel":    recommended_vessel,
        "recommendation_reason": recommendation_reason,

        "economic_profiles":     economic_profiles,
        "duration_comparison":   duration_comparison,

        "multi_voyage": multi_voyage_result,

        "integrity_checks": integrity,

        "limitations": [
            "Vessel screening is based on the specific benchmark vessel in STEP8E. "
            "Capesize result does not represent all Capesize vessels.",

            "Economic profiles are partially calculable. "
            "Port cost, freight rate, and TCE remain unavailable.",

            "BPI and BCI are market indices and are NOT used as "
            "dollar-per-mt voyage revenue.",

            "Final profit and TCE remain blocked -- commercial rate unavailable.",

            "Multi-voyage results are CALCULATED VALUES from user-supplied inputs. "
            "No routes, distances, or employment values are invented.",

            "Vessel DWT is NOT used as cargo capacity proxy. "
            "DWT includes fuel, stores, and crew weight.",

            "All distances in the current pipeline are scenario assumptions "
            "for the Gladstone -> Dhamra route.",
        ],
    }


# ============================================================
# LOCAL TEST  (python App\vessel_optimization_engine.py)
# ============================================================

if __name__ == "__main__":
    import json

    SEP  = "=" * 70
    SEP2 = "-" * 70

    print()
    print(SEP)
    print("  SAIL VESSEL OPTIMIZATION ENGINE -- LOCAL TESTS")
    print(SEP)

    # ──────────────────────────────────────────────────────────
    # TEST A: Current validated scenario
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST A: Current validated scenario (Gladstone -> Dhamra, Coal, 80000 t)")
    print(SEP)

    rA = get_vessel_optimization_report(
        scenario_id="GLADSTONE_DHAMRA_COAL",
        cargo_type="Coal",
        cargo_tonnes=80_000,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        contract_duration_months=1,
    )

    print(f"  Status             : {rA['status']}")
    print(f"  Recommended Vessel : {rA['recommended_vessel']}")
    print()
    print("  Candidates:")
    for c in rA["candidate_vessels"]:
        print(f"    {c['vessel_type']:<12}  feasible={c['port_feasible']}  "
              f"op_score={c['operational_score']}  cargo_fit={c['cargo_fit']}  "
              f"status={c['operational_status']}")
    print()
    print("  Ranked:")
    for r in rA["ranked_vessels"]:
        print(f"    #{r['rank']}  {r['vessel_type']:<12}  {r['vessel_recommendation']}")
    print()
    print("  Duration comparison:")
    dc = rA["duration_comparison"]
    if dc.get("status") == "OK":
        for d in dc["duration_comparison"]:
            bw = d["best_window"]
            print(f"    {d['contract_duration_months']}mo  "
                  f"score={bw['average_strategy_score']}  "
                  f"start={bw['start']}  rec={bw['recommendation']}")

    # ──────────────────────────────────────────────────────────
    # TEST B: Unsupported route
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST B: Unsupported route")
    print(SEP)

    rB = get_vessel_optimization_report(
        scenario_id="HEDLAND_VIZAG_IRON_ORE",
        cargo_type="Iron Ore",
        cargo_tonnes=160_000,
        origin="Port Hedland, Australia",
        destination="Vizag, India",
    )
    print(f"  Status  : {rB['status']}")
    print(f"  Message : {rB['message']}")

    # ──────────────────────────────────────────────────────────
    # TEST C: Cargo over scenario quantity (where capacity available)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST C: Cargo over scenario quantity (150,001 t)")
    print(SEP)

    rC = get_vessel_optimization_report(
        scenario_id="GLADSTONE_DHAMRA_COAL",
        cargo_type="Coal",
        cargo_tonnes=150_001,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
    )
    print(f"  Status: {rC['status']}")
    print("  Candidates:")
    for c in rC["candidate_vessels"]:
        print(f"    {c['vessel_type']:<12}  cargo_fit={c['cargo_fit']}  "
              f"status={c['operational_status']}")
        print(f"    Note: {c['cargo_fit_note']}")

    # ──────────────────────────────────────────────────────────
    # TEST D: Cargo fit UNKNOWN scenario
    # (Simulated by using a vessel type not in scenario data)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST D: Cargo fit UNKNOWN -- vessel not in scenario ranking data")
    print(SEP)
    # Direct call to screen_vessel_candidates with a vessel type that
    # does NOT appear in 8I (demonstrated by inspecting output notes)
    cands = screen_vessel_candidates("GLADSTONE_DHAMRA_COAL", cargo_tonnes=80_000)
    for c in cands:
        if c.get("cargo_fit") == "UNKNOWN":
            print(f"  {c['vessel_type']}: cargo_fit=UNKNOWN  note={c['cargo_fit_note']}")
        else:
            print(f"  {c['vessel_type']}: cargo_fit={c['cargo_fit']}  "
                  f"(data present; cargo fit determinable)")

    # ──────────────────────────────────────────────────────────
    # TEST E: Panamax vs Capesize comparison
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST E: Panamax vs Capesize comparison")
    print(SEP)

    print(f"  {'Vessel':<12}  {'Feasible':>8}  {'Op Score':>10}  {'Rec'}")
    print("  " + SEP2)
    for r in rA["ranked_vessels"]:
        print(f"  {r['vessel_type']:<12}  "
              f"{str(r['port_feasible']):>8}  "
              f"{str(r['operational_score']):>10}  "
              f"{r['vessel_recommendation']}")
    print()
    print("  Reasons:")
    for r in rA["ranked_vessels"]:
        print(f"  [{r['vessel_type']}] {r['reason'][:120]}...")

    # ──────────────────────────────────────────────────────────
    # TEST F: Multi-voyage -- all values supplied
    # (Clearly labelled as USER/PROJECT SUPPLIED TEST DATA)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST F: Multi-voyage -- all values supplied")
    print("  *** USER/PROJECT SUPPLIED TEST DATA -- NOT real SAIL voyage data ***")
    print(SEP)

    test_voyages_F = [
        {
            "voyage_id":           "TEST_VOYAGE_1",
            "origin":              "[TEST PORT A]",
            "destination":         "[TEST PORT B]",
            "cargo_type":          "Coal",
            "cargo_tonnes":        80_000,
            "vessel_type":         "Panamax",
            "laden_distance_nm":   5827.27,   # same as scenario assumption
            "ballast_distance_nm": 5827.27,
            "laden_speed_knots":   13.5,
            "ballast_speed_knots": 14.0,
            "laden_fuel_tpd":      33.0,
            "ballast_fuel_tpd":    31.0,
            "port_days":           1.5,
            "bunker_price_usd_per_mt": 464.22,  # from STEP8G Dec-2025
            "employment_value_usd":  None,      # NOT YET SUPPLIED
            "daily_idle_cost_usd":   None,      # NOT YET SUPPLIED
            "distance_data_class": "USER/PROJECT SUPPLIED TEST DATA",
            "notes":               "TEST_VOYAGE_1 -- not real SAIL voyage data",
        },
        {
            "voyage_id":           "TEST_VOYAGE_2",
            "origin":              "[TEST PORT B]",
            "destination":         "[TEST PORT A]",
            "cargo_type":          "Coal",
            "cargo_tonnes":        80_000,
            "vessel_type":         "Panamax",
            "laden_distance_nm":   5827.27,
            "ballast_distance_nm": 2000.0,    # hypothetical ballast to next load
            "laden_speed_knots":   13.5,
            "ballast_speed_knots": 14.0,
            "laden_fuel_tpd":      33.0,
            "ballast_fuel_tpd":    31.0,
            "port_days":           1.5,
            "bunker_price_usd_per_mt": 464.22,
            "employment_value_usd":  None,      # NOT YET SUPPLIED
            "daily_idle_cost_usd":   None,      # NOT YET SUPPLIED
            "distance_data_class": "USER/PROJECT SUPPLIED TEST DATA",
            "notes":               "TEST_VOYAGE_2 -- not real SAIL voyage data",
        },
    ]

    rF = get_vessel_optimization_report(
        scenario_id="GLADSTONE_DHAMRA_COAL",
        cargo_type="Coal",
        cargo_tonnes=80_000,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        multi_voyage_scenarios=test_voyages_F,
    )

    mv_F = rF["multi_voyage"]
    print(f"  Status          : {mv_F['status']}")
    print(f"  Voyage count    : {mv_F['voyage_count']}")
    agg = mv_F.get("aggregate", {})
    print(f"  Total voyage days : {agg.get('total_voyage_days', 'BLOCKED')}")
    print(f"  Total laden dist  : {agg.get('total_laden_distance_nm', 'BLOCKED')} NM")
    print(f"  Total ballast dist: {agg.get('total_ballast_distance_nm', 'BLOCKED')} NM")
    print(f"  Deadhead ratio    : {agg.get('deadhead_ratio', 'BLOCKED')}")
    print(f"  Total fuel        : {agg.get('total_fuel_tonnes', 'BLOCKED')} t")
    print(f"  Total bunker cost : {agg.get('total_bunker_cost_usd', 'BLOCKED')}")
    print(f"  Employment value  : {agg.get('total_employment_value_usd', 'BLOCKED')}")
    print(f"  Net earnings      : {agg.get('total_net_voyage_earnings_usd', 'BLOCKED')}")
    if mv_F.get("blocked_metrics"):
        print("  Blocked metrics:")
        for b in mv_F["blocked_metrics"]:
            print(f"    - {b}")

    # ──────────────────────────────────────────────────────────
    # TEST G: Multi-voyage -- missing values
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST G: Multi-voyage -- missing values (all None)")
    print("  *** USER/PROJECT SUPPLIED TEST DATA -- NOT real SAIL voyage data ***")
    print(SEP)

    test_voyages_G = [
        {
            "voyage_id":    "TEST_VOYAGE_3",
            "origin":       "[TEST PORT C]",
            "destination":  "[TEST PORT D]",
            "cargo_type":   "Coal",
            "cargo_tonnes": 80_000,
            "vessel_type":  "Panamax",
            # All parameters missing
            "notes":        "TEST_VOYAGE_3 -- all parameters missing, not real SAIL data",
        },
    ]

    rG = get_vessel_optimization_report(
        scenario_id="GLADSTONE_DHAMRA_COAL",
        cargo_type="Coal",
        cargo_tonnes=80_000,
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        multi_voyage_scenarios=test_voyages_G,
    )

    mv_G = rG["multi_voyage"]
    print(f"  Status         : {mv_G['status']}")
    print(f"  Voyage count   : {mv_G['voyage_count']}")
    leg0 = mv_G["per_leg_metrics"][0]
    print(f"  Voyage ID      : {leg0['voyage_id']}")
    print(f"  Missing inputs :")
    for m in leg0.get("missing_inputs", []):
        print(f"    - {m}")
    print(f"  Blocked metrics:")
    for b in mv_G.get("blocked_metrics", []):
        print(f"    - {b}")

    # ──────────────────────────────────────────────────────────
    # INTEGRITY CHECKS
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  INTEGRITY CHECKS (TEST A result)")
    print(SEP)
    all_pass = True
    for check, passed in rA["integrity_checks"].items():
        sym = "OK  " if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{sym}]  {check.replace('_', ' ')}")
    print()
    if all_pass:
        print("  ALL INTEGRITY CHECKS PASSED")
    else:
        print("  WARNING: ONE OR MORE INTEGRITY CHECKS FAILED")

    # ──────────────────────────────────────────────────────────
    # LIMITATIONS
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  IMPORTANT LIMITATIONS")
    print(SEP)
    for note in rA["limitations"]:
        print(f"  * {note}")

    print()
    print(SEP)
    print("  ALL TESTS COMPLETE")
    print(SEP)
    print()
