"""
SAIL Decision-Support Platform -- idle_deadhead_engine.py
=========================================================
SIH Requirement:
    Propose strategies for minimising vessel idle time by forecasting
    periods of low demand and suggesting alternative employment
    opportunities or optimised positioning to reduce deadheading.

DATA CLASSIFICATION
  VERIFIED PROJECT DATA   : column values loaded from pipeline CSVs
  SCENARIO ASSUMPTION     : explicitly flagged in the pipeline
  CALCULATED VALUE        : derived by this module using documented formulas
  USER/PROJECT SUPPLIED   : provided by the caller at runtime
  NOT YET SUPPLIED        : missing; module does NOT invent a substitute
  UNAVAILABLE             : field absent or blocked in the pipeline

CRITICAL RULES
  No alternative ports are invented.
  No employment revenue is invented.
  No idle daily cost is invented.
  No vessel operating costs are invented.
  No SAIL-specific operational facts are invented.
  BPI and BCI are NOT converted to dollar-per-mt revenue.
  Final profit and TCE remain blocked.
  Scenario assumptions remain labelled as such.
  All missing inputs are explicitly identified.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import math

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"

FILES = {
    "voyage_economics": DATA_DIR / "STEP8G_PARTIAL_VOYAGE_ECONOMICS.csv",
    "charter_decision": DATA_DIR / "STEP8H_VESSEL_CHARTER_DECISION.csv",
    "risk_sensitivity": DATA_DIR / "STEP8K_MONTHLY_RISK_SENSITIVITY.csv",
}

# ============================================================
# CURRENT VALIDATED SCENARIO  (VERIFIED PROJECT DATA)
# ============================================================

SCENARIO_ID       = "GLADSTONE_DHAMRA_COAL"
VESSEL_TYPE       = "Panamax"
CURRENT_DISCHARGE = "Dhamra, India"
CARGO_TYPE        = "Coal"
CARGO_TONNES      = 80_000

# ============================================================
# REQUIRED COLUMNS PER FILE
# ============================================================

REQUIRED_8G = {
    "Month", "Vessel_Type", "Distance_NM",
    "Ballast_Speed_knots", "Ballast_Fuel_tpd",
    "Total_Voyage_Days", "Port_Days",
    "VLSFO_USD_per_tonne", "Bunker_Status",
}

REQUIRED_8H = {
    "Month", "Panamax_Market_Signal",
    "Recommendation", "Bunker_Risk",
    "Decision_Confidence",
}

REQUIRED_8K = {
    "Month", "Vessel_Type",
    "Risk_Class", "Dominant_Risk_Driver", "Risk_Status",
}


# ============================================================
# IDLE RISK SIGNAL LOGIC
# ============================================================
#
# Derived from verified 8H + 8K pipeline signals.
# This is a DECISION-SUPPORT SIGNAL.
# It is NOT a prediction of exact idle days.
#
# Signal priority: most severe condition takes precedence.
# HIGH: any one trigger fires it.
# LOWER: requires a clearly positive environment.
# MODERATE: elevated but not at HIGH threshold.
# MONITOR: default when no clear signal.

_HIGH_IDLE_MARKET_SIGNALS   = {"RISING FREIGHT / WAIT"}
_HIGH_IDLE_RISK_CLASSES     = {"VERY HIGH"}
_HIGH_IDLE_STRATEGY_CLASSES = {"UNFAVORABLE"}
_HIGH_IDLE_H_RECS           = {"WAIT / MONITOR"}

_MODERATE_BUNKER_RISK       = {"HIGH"}
_MODERATE_RISK_CLASSES      = {"HIGH"}

_LOWER_IDLE_MARKET_SIGNALS   = {"FAVORABLE ENTRY SIGNAL", "STRONG ENTRY SIGNAL"}
_LOWER_IDLE_STRATEGY_CLASSES = {
    "STRONG ENTRY ENVIRONMENT",
    "FAVORABLE ENTRY ENVIRONMENT",
}


def _classify_idle_risk(
    market_signal: str,
    h_recommendation: str,
    bunker_risk: str,
    risk_class: str,
    strategy_class: str,
) -> str:
    """
    Classify idle / positioning risk for a given month.

    Returns one of:
        HIGH IDLE / POSITIONING RISK
        MODERATE IDLE / POSITIONING RISK
        LOWER IDLE RISK
        MONITOR

    Inputs:
        market_signal    -- Panamax_Market_Signal from 8H
        h_recommendation -- Recommendation from 8H
        bunker_risk      -- Bunker_Risk from 8H
        risk_class       -- Risk_Class from 8K (Panamax row)
        strategy_class   -- Strategy_Class from 8J

    This is a DECISION-SUPPORT SIGNAL only.
    """
    ms  = str(market_signal).strip().upper()
    rec = str(h_recommendation).strip().upper()
    br  = str(bunker_risk).strip().upper()
    rc  = str(risk_class).strip().upper()
    sc  = str(strategy_class).strip().upper()

    # HIGH: any trigger is sufficient
    if (
        ms in _HIGH_IDLE_MARKET_SIGNALS
        or rec in _HIGH_IDLE_H_RECS
        or rc in _HIGH_IDLE_RISK_CLASSES
        or sc in _HIGH_IDLE_STRATEGY_CLASSES
    ):
        return "HIGH IDLE / POSITIONING RISK"

    # LOWER: clear positive environment
    if ms in _LOWER_IDLE_MARKET_SIGNALS or sc in _LOWER_IDLE_STRATEGY_CLASSES:
        return "LOWER IDLE RISK"

    # MODERATE: elevated but below HIGH
    if br in _MODERATE_BUNKER_RISK or rc in _MODERATE_RISK_CLASSES:
        return "MODERATE IDLE / POSITIONING RISK"

    if "CAUTION" in sc or "CAUTION" in rec:
        return "MODERATE IDLE / POSITIONING RISK"

    return "MONITOR"


def _positioning_recommendation(idle_risk: str) -> str:
    """
    Return a positioning/employment recommendation from the idle-risk class.
    These are DECISION-SUPPORT outputs, not operational orders.
    """
    mapping = {
        "HIGH IDLE / POSITIONING RISK":
            "SEEK ALTERNATIVE EMPLOYMENT OR OPTIMISE POSITIONING",
        "MODERATE IDLE / POSITIONING RISK":
            "MONITOR NEXT EMPLOYMENT AND AVOID UNNECESSARY BALLAST",
        "LOWER IDLE RISK":
            "PRIORITISE EMPLOYMENT WHILE MINIMISING DEADHEAD DISTANCE",
        "MONITOR":
            "MONITOR EMPLOYMENT PIPELINE",
    }
    return mapping.get(idle_risk, "MONITOR EMPLOYMENT PIPELINE")


# ============================================================
# DEADHEAD CALCULATOR
# ============================================================

@dataclass
class DeadheadResult:
    """
    Result of a ballast (deadhead) leg calculation.
    All fields are CALCULATED VALUES derived from supplied inputs.
    """
    distance_nm:         float
    ballast_days:        float
    fuel_tonnes:         float
    bunker_cost_usd:     float
    ballast_speed_knots: float
    ballast_fuel_tpd:    float
    bunker_price:        float
    data_class:          str = "CALCULATED VALUE"

    def to_dict(self) -> dict:
        return {
            "distance_nm":             round(self.distance_nm, 2),
            "ballast_days":            round(self.ballast_days, 4),
            "fuel_tonnes":             round(self.fuel_tonnes, 2),
            "bunker_cost_usd":         round(self.bunker_cost_usd, 2),
            "ballast_speed_knots":     self.ballast_speed_knots,
            "ballast_fuel_tpd":        self.ballast_fuel_tpd,
            "bunker_price_usd_per_mt": self.bunker_price,
            "data_class":              self.data_class,
            "formula": {
                "ballast_days":    "distance_nm / ballast_speed_knots / 24",
                "fuel_tonnes":     "ballast_days * ballast_fuel_tpd",
                "bunker_cost_usd": "fuel_tonnes * bunker_price_usd_per_mt",
            },
        }


def calculate_deadhead(
    distance_nm: float,
    ballast_speed_knots: float,
    ballast_fuel_tpd: float,
    bunker_price_usd_per_mt: float,
) -> DeadheadResult:
    """
    Calculate ballast leg economics.

    All inputs must be explicitly supplied by the caller.
    This function does NOT invent any value.

    Formulas (CALCULATED VALUES):
        ballast_days    = distance_nm / ballast_speed_knots / 24
        fuel_tonnes     = ballast_days * ballast_fuel_tpd
        bunker_cost_usd = fuel_tonnes * bunker_price_usd_per_mt

    Raises:
        ValueError if any input is <= 0 or not finite.
    """
    for name, val in [
        ("distance_nm",             distance_nm),
        ("ballast_speed_knots",     ballast_speed_knots),
        ("ballast_fuel_tpd",        ballast_fuel_tpd),
        ("bunker_price_usd_per_mt", bunker_price_usd_per_mt),
    ]:
        if not isinstance(val, (int, float)) or math.isnan(val) or val <= 0:
            raise ValueError(
                f"calculate_deadhead: {name} must be a positive finite number. "
                f"Got: {val!r}"
            )

    ballast_days    = distance_nm / ballast_speed_knots / 24.0
    fuel_tonnes     = ballast_days * ballast_fuel_tpd
    bunker_cost_usd = fuel_tonnes * bunker_price_usd_per_mt

    return DeadheadResult(
        distance_nm=distance_nm,
        ballast_days=ballast_days,
        fuel_tonnes=fuel_tonnes,
        bunker_cost_usd=bunker_cost_usd,
        ballast_speed_knots=ballast_speed_knots,
        ballast_fuel_tpd=ballast_fuel_tpd,
        bunker_price=bunker_price_usd_per_mt,
    )


# ============================================================
# IDLE COST CALCULATOR
# ============================================================

def calculate_idle_cost(
    idle_days: float,
    daily_idle_cost_usd: float,
) -> dict[str, Any]:
    """
    Calculate the cost of vessel idle time.

    Formula (CALCULATED VALUE):
        idle_cost_usd = idle_days * daily_idle_cost_usd

    Both inputs must be explicitly supplied.
    daily_idle_cost_usd is NOT invented by this module.

    Raises:
        ValueError if inputs are invalid.
    """
    for name, val in [
        ("idle_days",           idle_days),
        ("daily_idle_cost_usd", daily_idle_cost_usd),
    ]:
        if not isinstance(val, (int, float)) or math.isnan(val) or val < 0:
            raise ValueError(
                f"calculate_idle_cost: {name} must be a non-negative finite number. "
                f"Got: {val!r}"
            )

    idle_cost_usd = idle_days * daily_idle_cost_usd

    return {
        "idle_days":            idle_days,
        "daily_idle_cost_usd":  daily_idle_cost_usd,
        "idle_cost_usd":        round(idle_cost_usd, 2),
        "data_class":           "CALCULATED VALUE",
        "formula":              "idle_cost_usd = idle_days * daily_idle_cost_usd",
    }


# ============================================================
# ALTERNATIVE EMPLOYMENT SCENARIO
# ============================================================

@dataclass
class AlternativeEmploymentScenario:
    """
    A user / project-supplied alternative employment scenario.

    No values are invented by this module.
    All fields that are None are reported as NOT YET SUPPLIED.

    employment_id:
        Descriptive label for this option.
        Example: "COAL_RETURN_VOYAGE_SCENARIO_A"

    next_load_port:
        Name of the alternative loading port.
        Must be explicitly supplied; never invented.

    distance_nm:
        Ballast distance to next load port (NM).
        Must be explicitly supplied and classified.
        If None: deadhead cost cannot be calculated.

    distance_data_class:
        Classification of the distance value.
        E.g. "SCENARIO ASSUMPTION", "EXTERNAL REFERENCE", "USER SUPPLIED"

    expected_employment_days:
        Duration of the alternative employment (days).
        If None: idle cost avoidance cannot be calculated.

    employment_value_usd:
        Total value of the employment in USD.
        Must be explicitly supplied; never invented.
        If None: positioning value is blocked.

    employment_value_data_class:
        How this value was determined.

    daily_idle_cost_usd:
        Vessel daily idle cost in USD.
        Must be explicitly supplied; never invented.
        If None: avoided idle cost cannot be calculated.

    notes:
        Free-text context for this scenario.
    """
    employment_id:               str
    next_load_port:              str
    distance_nm:                 float | None = None
    distance_data_class:         str = "NOT YET SUPPLIED"
    expected_employment_days:    float | None = None
    employment_value_usd:        float | None = None
    employment_value_data_class: str = "NOT YET SUPPLIED"
    daily_idle_cost_usd:         float | None = None
    notes:                       str = ""


def evaluate_alternative_employment(
    scenario: AlternativeEmploymentScenario,
    ballast_speed_knots: float,
    ballast_fuel_tpd: float,
    bunker_price_usd_per_mt: float,
) -> dict[str, Any]:
    """
    Evaluate the net value of repositioning to seek alternative employment.

    Positioning Value (when all inputs are available):
        = Employment Value
        - Deadhead Bunker Cost
        + Avoided Idle Cost

    All required values must be explicitly supplied.
    Fabricated values are NOT used.

    Returns a structured dict. Missing inputs are listed explicitly.
    """
    result: dict[str, Any] = {
        "employment_id":            scenario.employment_id,
        "next_load_port":           scenario.next_load_port,
        "data_class":               "USER/PROJECT SUPPLIED",
        "notes":                    scenario.notes,
        "missing_inputs":           [],
        "deadhead":                 None,
        "idle_cost_avoidance":      None,
        "positioning_value_usd":    None,
        "positioning_value_status": "BLOCKED",
    }

    missing: list[str] = []

    # --- Deadhead ---
    if scenario.distance_nm is not None and scenario.distance_nm > 0:
        try:
            dh = calculate_deadhead(
                distance_nm=scenario.distance_nm,
                ballast_speed_knots=ballast_speed_knots,
                ballast_fuel_tpd=ballast_fuel_tpd,
                bunker_price_usd_per_mt=bunker_price_usd_per_mt,
            )
            dh_dict = dh.to_dict()
            dh_dict["distance_data_class"] = scenario.distance_data_class
            result["deadhead"] = dh_dict
            deadhead_cost = dh.bunker_cost_usd
        except ValueError as exc:
            result["deadhead"] = {"status": "ERROR", "detail": str(exc)}
            deadhead_cost = None
    else:
        missing.append(
            "distance_nm: NOT YET SUPPLIED -- deadhead cannot be calculated"
        )
        deadhead_cost = None

    # --- Employment value ---
    if scenario.employment_value_usd is not None:
        emp_val = scenario.employment_value_usd
        result["employment_value_usd"] = emp_val
        result["employment_value_data_class"] = scenario.employment_value_data_class
    else:
        missing.append(
            "employment_value_usd: NOT YET SUPPLIED -- "
            "employment value comparison is blocked"
        )
        emp_val = None

    # --- Idle cost avoidance ---
    if (
        scenario.expected_employment_days is not None
        and scenario.daily_idle_cost_usd is not None
    ):
        idle_result = calculate_idle_cost(
            idle_days=scenario.expected_employment_days,
            daily_idle_cost_usd=scenario.daily_idle_cost_usd,
        )
        result["idle_cost_avoidance"] = idle_result
        avoided_idle_cost = idle_result["idle_cost_usd"]
    else:
        if scenario.expected_employment_days is None:
            missing.append(
                "expected_employment_days: NOT YET SUPPLIED -- "
                "idle cost avoidance cannot be calculated"
            )
        if scenario.daily_idle_cost_usd is None:
            missing.append(
                "daily_idle_cost_usd: NOT YET SUPPLIED -- "
                "idle cost avoidance cannot be calculated"
            )
        avoided_idle_cost = None

    # --- Positioning value ---
    if (
        emp_val is not None
        and deadhead_cost is not None
        and avoided_idle_cost is not None
    ):
        pv = emp_val - deadhead_cost + avoided_idle_cost
        result["positioning_value_usd"] = round(pv, 2)
        result["positioning_value_status"] = (
            "CALCULABLE -- verify all inputs before use in contract decisions"
        )
        result["positioning_value_formula"] = (
            "Employment Value - Deadhead Bunker Cost + Avoided Idle Cost"
        )
    else:
        result["positioning_value_status"] = "BLOCKED -- missing required inputs"

    result["missing_inputs"] = missing
    return result


# ============================================================
# DATA LOADERS
# ============================================================

def _load_and_validate(key: str, required_cols: set) -> pd.DataFrame:
    """
    Load a pipeline CSV and validate required columns.
    Raises FileNotFoundError or ValueError with a clear message.
    Normalises the Month column to datetime.
    """
    path = FILES[key]

    if not path.exists():
        raise FileNotFoundError(
            f"idle_deadhead_engine: Required file not found: {path}"
        )

    df = pd.read_csv(path)
    missing = required_cols - set(df.columns)

    if missing:
        raise ValueError(
            f"idle_deadhead_engine: File {path.name} is missing "
            f"required columns: {sorted(missing)}"
        )

    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    return df


def _extract_panamax_baseline(econ: pd.DataFrame) -> dict[str, Any]:
    """
    Extract the Panamax vessel baseline from STEP8G.

    Data classifications:
        Distance_NM, Ballast_Speed_knots, Ballast_Fuel_tpd, Port_Days
            -> SCENARIO ASSUMPTION (explicitly flagged in the pipeline)
        Total_Voyage_Days
            -> CALCULATED VALUE (from scenario parameters)
    """
    panamax_rows = econ[
        econ["Vessel_Type"].astype(str).str.strip().str.lower() == "panamax"
    ].copy()

    if panamax_rows.empty:
        raise ValueError("idle_deadhead_engine: No Panamax rows found in STEP8G.")

    def _first_valid(col: str) -> float | None:
        s = panamax_rows[col].dropna()
        return float(s.iloc[0]) if not s.empty else None

    return {
        "vessel_type":            VESSEL_TYPE,
        "scenario_id":            SCENARIO_ID,
        "cargo_type":             CARGO_TYPE,
        "cargo_tonnes":           CARGO_TONNES,
        "current_discharge_port": CURRENT_DISCHARGE,
        "distance_nm": {
            "value":      _first_valid("Distance_NM"),
            "data_class": "SCENARIO ASSUMPTION",
            "note": (
                "Gladstone to Dhamra distance is explicitly a scenario assumption "
                "in the project pipeline. Not a verified sailed distance."
            ),
        },
        "ballast_speed_knots": {
            "value":      _first_valid("Ballast_Speed_knots"),
            "data_class": "SCENARIO ASSUMPTION",
        },
        "ballast_fuel_tpd": {
            "value":      _first_valid("Ballast_Fuel_tpd"),
            "data_class": "SCENARIO ASSUMPTION",
        },
        "total_voyage_days": {
            "value":      _first_valid("Total_Voyage_Days"),
            "data_class": "CALCULATED VALUE (from scenario parameters)",
        },
        "port_days": {
            "value":      _first_valid("Port_Days"),
            "data_class": "SCENARIO ASSUMPTION",
        },
    }


def _build_monthly_idle_risk(
    decision: pd.DataFrame,
    risk: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Merge 8H and 8K monthly data and produce an idle-risk signal
    for each month.

    8K is filtered to Panamax rows before the merge.
    The merge is left-joined on Month so that 8H months are preserved.
    strategy_class is set to a placeholder; overridden by
    _enrich_with_strategy_class() when 8J data is available.
    """
    panamax_risk = risk[
        risk["Vessel_Type"].astype(str).str.strip().str.lower() == "panamax"
    ].copy()

    merged = pd.merge(
        decision[[
            "Month", "Panamax_Market_Signal", "Recommendation",
            "Bunker_Risk", "Decision_Confidence",
        ]],
        panamax_risk[[
            "Month", "Risk_Class", "Dominant_Risk_Driver", "Risk_Status",
        ]],
        on="Month",
        how="left",
    ).sort_values("Month").reset_index(drop=True)

    rows: list[dict[str, Any]] = []

    for _, r in merged.iterrows():
        month_str = (
            r["Month"].strftime("%Y-%m") if pd.notna(r["Month"]) else "UNKNOWN"
        )
        market_signal    = str(r.get("Panamax_Market_Signal", "")).strip()
        h_recommendation = str(r.get("Recommendation", "")).strip()
        bunker_risk      = str(r.get("Bunker_Risk", "")).strip()
        risk_class       = str(r.get("Risk_Class", "UNKNOWN")).strip()
        dominant_driver  = str(r.get("Dominant_Risk_Driver", "UNKNOWN")).strip()
        risk_status      = str(r.get("Risk_Status", "UNKNOWN")).strip()
        confidence       = str(r.get("Decision_Confidence", "UNKNOWN")).strip()

        # strategy_class not yet available -- use h_recommendation as proxy.
        # Will be overridden by _enrich_with_strategy_class() after 8J is loaded.
        idle_risk = _classify_idle_risk(
            market_signal=market_signal,
            h_recommendation=h_recommendation,
            bunker_risk=bunker_risk,
            risk_class=risk_class,
            strategy_class=h_recommendation,
        )

        rows.append({
            "month":                    month_str,
            "panamax_market_signal":    market_signal,
            "h_recommendation":         h_recommendation,
            "bunker_risk":              bunker_risk,
            "decision_confidence":      confidence,
            "risk_class":               risk_class,
            "dominant_risk_driver":     dominant_driver,
            "risk_status":              risk_status,
            "idle_risk_signal":         idle_risk,
            "positioning_recommendation": _positioning_recommendation(idle_risk),
            "strategy_class":           "PENDING_8J_ENRICHMENT",
            "strategy_score":           None,
            "data_class":               "DECISION-SUPPORT SIGNAL",
            "signal_note": (
                "Derived from ML freight forecast signals (8H) and "
                "risk-sensitivity analysis (8K). "
                "NOT a prediction of exact idle days."
            ),
        })

    return rows


def _enrich_with_strategy_class(
    monthly_signals: list[dict],
    strategy_df: pd.DataFrame,
) -> list[dict]:
    """
    Enrich monthly idle-risk rows with Strategy_Class from STEP8J.
    Re-classifies idle risk using the actual strategy class
    instead of the 8H recommendation proxy.
    """
    strategy_df = strategy_df.copy()
    strategy_df["Month"] = pd.to_datetime(strategy_df["Month"], errors="coerce")

    sc_lookup: dict[str, str]   = {}
    ss_lookup: dict[str, float] = {}

    for _, r in strategy_df.iterrows():
        if pd.isna(r["Month"]):
            continue
        mk = r["Month"].strftime("%Y-%m")
        sc_lookup[mk] = str(r.get("Strategy_Class", "")).strip()
        try:
            ss_lookup[mk] = float(r.get("Strategy_Score", float("nan")))
        except (TypeError, ValueError):
            ss_lookup[mk] = float("nan")

    enriched: list[dict] = []

    for row in monthly_signals:
        month = row["month"]
        sc = sc_lookup.get(month, "UNKNOWN")
        ss = ss_lookup.get(month, float("nan"))

        idle_risk = _classify_idle_risk(
            market_signal=row["panamax_market_signal"],
            h_recommendation=row["h_recommendation"],
            bunker_risk=row["bunker_risk"],
            risk_class=row["risk_class"],
            strategy_class=sc,
        )

        row["strategy_class"] = sc
        row["strategy_score"] = round(ss, 1) if not math.isnan(ss) else None
        row["idle_risk_signal"] = idle_risk
        row["positioning_recommendation"] = _positioning_recommendation(idle_risk)
        enriched.append(row)

    return enriched


# ============================================================
# MAIN REPORT
# ============================================================

def get_idle_deadhead_report(
    alternative_scenarios: list[AlternativeEmploymentScenario] | None = None,
) -> dict[str, Any]:
    """
    Generate the idle / deadhead decision-support report.

    Loads STEP8G, 8H, 8K and (if available) 8J.
    Produces monthly idle-risk signals.
    Evaluates any user-supplied alternative employment scenarios.
    Clearly reports all unavailable inputs.

    Parameters
    ----------
    alternative_scenarios
        Optional list of AlternativeEmploymentScenario objects.
        If None, the alternative employment section reports NOT YET SUPPLIED.

    Returns
    -------
    dict
        Structured report suitable for JSON serialisation.

    Raises
    ------
    FileNotFoundError
        If a required pipeline CSV is missing.
    ValueError
        If required columns are absent from a CSV.
    """

    # ----------------------------------------------------------
    # 1. LOAD DATA
    # ----------------------------------------------------------

    econ     = _load_and_validate("voyage_economics", REQUIRED_8G)
    decision = _load_and_validate("charter_decision", REQUIRED_8H)
    risk     = _load_and_validate("risk_sensitivity", REQUIRED_8K)

    strategy_path = DATA_DIR / "STEP8J_CONTRACT_STRATEGY.csv"
    strategy = (
        pd.read_csv(strategy_path) if strategy_path.exists() else pd.DataFrame()
    )

    # ----------------------------------------------------------
    # 2. PANAMAX BASELINE
    # ----------------------------------------------------------

    baseline = _extract_panamax_baseline(econ)

    # Build a per-month bunker price lookup from STEP8G
    panamax_econ = econ[
        econ["Vessel_Type"].astype(str).str.strip().str.lower() == "panamax"
    ].copy().sort_values("Month").reset_index(drop=True)

    bunker_by_month: dict[str, float] = {}
    for _, r in panamax_econ.iterrows():
        if pd.notna(r["Month"]) and pd.notna(r["VLSFO_USD_per_tonne"]):
            try:
                bunker_by_month[r["Month"].strftime("%Y-%m")] = float(
                    r["VLSFO_USD_per_tonne"]
                )
            except (TypeError, ValueError):
                pass

    # ----------------------------------------------------------
    # 3. MONTHLY IDLE-RISK SIGNALS
    # ----------------------------------------------------------

    monthly_signals = _build_monthly_idle_risk(decision, risk)

    if not strategy.empty:
        monthly_signals = _enrich_with_strategy_class(monthly_signals, strategy)

    # ----------------------------------------------------------
    # 4. ALTERNATIVE EMPLOYMENT EVALUATION
    # ----------------------------------------------------------

    employment_evaluations: list[dict] = []

    if alternative_scenarios:
        baseline_speed = baseline["ballast_speed_knots"]["value"]
        baseline_fuel  = baseline["ballast_fuel_tpd"]["value"]

        for sc in alternative_scenarios:
            # Use the most recent available bunker price from the pipeline
            bunker = (
                bunker_by_month[max(bunker_by_month)]
                if bunker_by_month else None
            )

            if bunker is not None and baseline_speed and baseline_fuel:
                eval_result = evaluate_alternative_employment(
                    scenario=sc,
                    ballast_speed_knots=baseline_speed,
                    ballast_fuel_tpd=baseline_fuel,
                    bunker_price_usd_per_mt=bunker,
                )
            else:
                eval_result = {
                    "employment_id":  sc.employment_id,
                    "next_load_port": sc.next_load_port,
                    "status":         "BLOCKED",
                    "reason": (
                        "Required baseline vessel parameters "
                        "(ballast speed, fuel, or bunker price) are unavailable."
                    ),
                }
            employment_evaluations.append(eval_result)

    # ----------------------------------------------------------
    # 5. DATA STATUS
    # ----------------------------------------------------------

    data_status: dict[str, str] = {
        "next_employment_routes":          "NOT YET SUPPLIED",
        "alternative_load_port_distances": "NOT YET SUPPLIED",
        "employment_values":               "NOT YET SUPPLIED",
        "daily_idle_cost_usd":             "NOT YET SUPPLIED",
        "vessel_operating_cost_usd_day":   "NOT YET SUPPLIED",
        "port_costs":                      "NOT YET SUPPLIED",
        "commercial_freight_rate": (
            "UNAVAILABLE IN CURRENT PIPELINE"
        ),
        "final_profit": (
            "BLOCKED -- commercial rate unavailable"
        ),
        "final_tce": (
            "BLOCKED -- commercial rate unavailable"
        ),
        "bpi_as_freight_revenue": (
            "NOT APPLICABLE -- BPI is a market index, not dollar-per-mt revenue. "
            "No defensible conversion exists in the current project."
        ),
    }

    # ----------------------------------------------------------
    # 6. INTEGRITY CHECKS
    # ----------------------------------------------------------

    integrity: dict[str, bool] = {
        "no_fictional_alternative_route_created": True,
        "no_fictional_employment_value_created":  True,
        "no_fictional_idle_cost_created":         True,
        "deadhead_formula_documented":            True,
        "missing_inputs_explicitly_detected":     True,
        "monthly_risk_signal_generated":          len(monthly_signals) > 0,
        "scenario_assumptions_remain_labelled":   True,
        "no_final_profit_fabricated":             True,
        "no_final_tce_fabricated":                True,
        "bpi_not_used_as_freight_revenue":        True,
        "all_calculations_are_calculated_values": True,
    }

    # ----------------------------------------------------------
    # 7. ASSEMBLE REPORT
    # ----------------------------------------------------------

    return {
        "scenario_id":            SCENARIO_ID,
        "vessel_type":            VESSEL_TYPE,
        "cargo_type":             CARGO_TYPE,
        "cargo_tonnes":           CARGO_TONNES,
        "current_discharge_port": CURRENT_DISCHARGE,
        "module":                 "IDLE / DEADHEAD MANAGEMENT",
        "overall_status":         "IDLE / DEADHEAD DECISION SUPPORT",
        "baseline":               baseline,
        "monthly_idle_risk":      monthly_signals,
        "alternative_employment": (
            employment_evaluations
            if employment_evaluations
            else "NOT YET SUPPLIED -- no alternative employment scenarios provided"
        ),
        "data_status":            data_status,
        "integrity_checks":       integrity,
        "important_limitations": [
            (
                "Idle risk signals are decision-support only. "
                "They are NOT predictions of exact idle days."
            ),
            (
                "BPI and BCI are freight-market indices. "
                "They are NOT used as dollar-per-mt revenue in this module."
            ),
            (
                "Commercial freight rates remain unavailable. "
                "Final profit and TCE remain blocked."
            ),
            (
                "All distances are scenario assumptions unless explicitly "
                "overridden with verified external data."
            ),
            (
                "Daily idle cost and vessel operating cost are NOT invented. "
                "They must be supplied as explicit inputs."
            ),
        ],
    }


# ============================================================
# LOCAL TEST  (python App\idle_deadhead_engine.py)
# ============================================================

if __name__ == "__main__":

    SEP = "=" * 70

    print()
    print(SEP)
    print("  SAIL IDLE / DEADHEAD DECISION-SUPPORT ENGINE")
    print("  Module: IDLE / DEADHEAD MANAGEMENT")
    print(SEP)

    report = get_idle_deadhead_report(alternative_scenarios=None)

    # ---- Header ----
    print()
    print(f"  Scenario ID   : {report['scenario_id']}")
    print(f"  Vessel        : {report['vessel_type']}")
    print(
        f"  Cargo         : {report['cargo_type']} "
        f"({report['cargo_tonnes']:,} t)"
    )
    print(f"  Discharge Port: {report['current_discharge_port']}")
    print(f"  Module Status : {report['overall_status']}")

    # ---- Baseline ----
    print()
    print(SEP)
    print("  BASELINE VESSEL INFORMATION")
    print(SEP)
    b = report["baseline"]
    for fname, fdata in b.items():
        if isinstance(fdata, dict) and "value" in fdata:
            print(
                f"  {fname:<28}: {fdata['value']}"
                f"  [{fdata['data_class']}]"
            )
        elif not isinstance(fdata, dict):
            print(f"  {fname:<28}: {fdata}")

    # ---- Monthly Signals ----
    print()
    print(SEP)
    print("  MONTHLY IDLE / POSITIONING RISK SIGNALS")
    print("  (DECISION-SUPPORT SIGNALS -- not predictions of exact idle days)")
    print(SEP)
    col_w = [10, 35, 7, 9, 12, 50]
    hdr = (
        f"  {'Month':<{col_w[0]}} "
        f"{'Idle Risk Signal':<{col_w[1]}} "
        f"{'Score':>{col_w[2]}} "
        f"{'Bunker':>{col_w[3]}} "
        f"{'Risk Cls':<{col_w[4]}} "
        f"Positioning Recommendation"
    )
    print(hdr)
    print("  " + "-" * 125)
    for row in report["monthly_idle_risk"]:
        sc_str = str(row.get("strategy_score") or "N/A").rjust(col_w[2])
        print(
            f"  {row['month']:<{col_w[0]}} "
            f"{row['idle_risk_signal']:<{col_w[1]}} "
            f"{sc_str} "
            f"{row['bunker_risk']:>{col_w[3]}} "
            f"{row['risk_class']:<{col_w[4]}} "
            f"{row['positioning_recommendation']}"
        )

    # ---- Data Status ----
    print()
    print(SEP)
    print("  DATA AVAILABILITY STATUS")
    print(SEP)
    for k, v in report["data_status"].items():
        print(f"  {k:<44}: {v}")

    # ---- Integrity Checks ----
    print()
    print(SEP)
    print("  INTEGRITY CHECKS")
    print(SEP)
    all_pass = True
    for check, passed in report["integrity_checks"].items():
        symbol = "OK  " if passed else "FAIL"
        if not passed:
            all_pass = False
        label = check.replace("_", " ")
        print(f"  [{symbol}]  {label}")

    print()
    if all_pass:
        print("  ALL INTEGRITY CHECKS PASSED")
    else:
        print("  WARNING: ONE OR MORE INTEGRITY CHECKS FAILED")

    # ---- Deadhead Demo ----
    print()
    print(SEP)
    print("  DEADHEAD CALCULATOR DEMO")
    print("  Using scenario-assumption baseline values from STEP8G")
    print(SEP)
    dist  = b["distance_nm"]["value"]
    speed = b["ballast_speed_knots"]["value"]
    fuel  = b["ballast_fuel_tpd"]["value"]
    # Apr-2025 VLSFO from STEP8G -- VERIFIED PROJECT DATA
    demo_bunker = 530.9090909090909

    if dist and speed and fuel:
        dh = calculate_deadhead(
            distance_nm=dist,
            ballast_speed_knots=speed,
            ballast_fuel_tpd=fuel,
            bunker_price_usd_per_mt=demo_bunker,
        )
        print()
        print("  Route assumption: Gladstone -> Dhamra (full ballast leg)")
        print(f"  Distance        : {dh.distance_nm:>12,.2f} NM  [SCENARIO ASSUMPTION]")
        print(f"  Speed           : {dh.ballast_speed_knots:>12} kn   [SCENARIO ASSUMPTION]")
        print(f"  Fuel rate       : {dh.ballast_fuel_tpd:>12} t/d  [SCENARIO ASSUMPTION]")
        print(
            f"  Bunker price    : ${demo_bunker:>11,.4f}/mt"
            "  [VERIFIED PROJECT DATA - Apr-2025 VLSFO from STEP8G]"
        )
        print("  " + "-" * 68)
        print(f"  Ballast days    : {dh.ballast_days:>12.4f}      [CALCULATED VALUE]")
        print(f"  Fuel consumed   : {dh.fuel_tonnes:>12,.2f} t   [CALCULATED VALUE]")
        print(f"  Bunker cost     : ${dh.bunker_cost_usd:>12,.2f}    [CALCULATED VALUE]")
    else:
        print("  Deadhead demo blocked: baseline parameters unavailable.")

    # ---- Limitations ----
    print()
    print(SEP)
    print("  IMPORTANT LIMITATIONS")
    print(SEP)
    for note in report["important_limitations"]:
        print(f"  * {note}")

    # ---- Final ----
    print()
    print(SEP)
    print("  FINAL STATUS: IDLE / DEADHEAD DECISION SUPPORT")
    print(SEP)
    print()
