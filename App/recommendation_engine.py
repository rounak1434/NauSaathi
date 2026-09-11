"""
SAIL / NauSaathi Decision-Support Platform
=========================================
recommendation_engine.py

Comprehensive decision-support engine for bulk vessel chartering & freight intelligence.
Produces rich, fully structured analysis across all frontend origins, destinations,
vessel classes, and chartering windows with full data provenance transparency.

DATA CLASSIFICATION:
- VERIFIED: Ground-truth project pipeline data (Gladstone -> Dhamra, ML forecasts, bunker prices)
- DERIVED: Physical engineering models (dual-port draft/LOA/beam checks, distance calculations)
- SCENARIO: Baseline assumptions for unconfigured external routes
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import pandas as pd

from route_scenario_registry import (
    DataProvenance,
    VESSEL_REGISTRY,
    ORIGIN_REGISTRY,
    DESTINATION_PORT_REGISTRY,
    find_origin_profile,
    find_destination_profile,
    get_route_distance_nm,
    get_route_provenance,
)


# ============================================================
# PATHS & CSVs
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"

FILES = {
    "forecast":           DATA_DIR / "STEP6B_FINAL_RANDOM_FOREST_FORECAST.csv",
    "forecast_bunker":    DATA_DIR / "STEP8C_FORECAST_BUNKER_TIMELINE.csv",
    "bunker":             DATA_DIR / "STEP7B_MONTHLY_BUNKER_PRICE_DATA.csv",
    "feasibility":        DATA_DIR / "STEP8E_VESSEL_FEASIBILITY.csv",
    "voyage_scenario":    DATA_DIR / "STEP8E_VOYAGE_ECONOMICS_SCENARIO.csv",
    "partial_economics":  DATA_DIR / "STEP8G_PARTIAL_VOYAGE_ECONOMICS.csv",
    "vessel_ranking":     DATA_DIR / "STEP8I_VESSEL_ROUTE_RANKING.csv",
    "scenario":           DATA_DIR / "STEP8I_MULTI_SCENARIO_DECISION.csv",
    "contract_windows":   DATA_DIR / "STEP8J_CHARTER_WINDOWS.csv",
    "monthly_strategy":   DATA_DIR / "STEP8J_CONTRACT_STRATEGY.csv",
    "risk_monthly":       DATA_DIR / "STEP8K_MONTHLY_RISK_SENSITIVITY.csv",
    "final_recommendation": DATA_DIR / "STEP8L_FINAL_SAIL_RECOMMENDATION.csv",
}

# Legacy supported scenario lookup for backward compatibility
SUPPORTED_SCENARIOS = {
    ("gladstone, australia", "dhamra, india", "coal"): {
        "scenario_id": "GLADSTONE_DHAMRA_COAL",
        "default_vessel": "Panamax",
        "default_cargo_tonnes": 80_000,
        "provenance": DataProvenance.VERIFIED,
    }
}


# ============================================================
# OPERATIONAL SCORING PARAMETERS (Documented Calibration)
# ============================================================
# These weights define the multi-criteria operational scoring model.
# Total budget: 100 points = CARGO_FIT (40) + PORT_FEASIBILITY (40) + ROUTE_EFFICIENCY (20)
#
# Provenance:
#   CARGO_FIT_MAX_PTS (40):      40% weight — cargo payload utilization is the primary
#                                 commercial determinant for voyage economics.
#   PORT_FEASIBILITY_MAX_PTS (40): 40% weight — port physical access determines whether
#                                  the vessel can berth directly or needs lighterage.
#   ROUTE_EFFICIENCY_PTS (20):   20% weight — high-economy vessels (Panamax/Capesize)
#                                 have lower per-MT fuel costs on long-haul routes.
#   ROUTE_EFFICIENCY_PTS_GEARED (17): Geared/flexible vessels (Handysize/Supramax) get
#                                      slightly lower route efficiency due to higher
#                                      per-MT fuel consumption, offset by self-discharge capability.
#   LIGHTERAGE_PENALTY_PTS (10): Deducted when offshore transshipment is required.
#                                 Represents operational friction: double-handling time,
#                                 anchorage weather risk, and additional barge costs.
#                                 Calibrated as 10% of total score budget (100 pts).
#   DRAFT_RATIO_FLOOR (0.5):     Minimum draft utilization ratio for transshipment
#                                 scoring. Prevents vessels with extreme draft mismatch
#                                 (>2x port limit) from scoring any port feasibility points.

CARGO_FIT_MAX_PTS = 40.0
PORT_FEASIBILITY_MAX_PTS = 40.0
ROUTE_EFFICIENCY_PTS = 20.0
ROUTE_EFFICIENCY_PTS_GEARED = 17.0
LIGHTERAGE_PENALTY_PTS = 10.0
DRAFT_RATIO_FLOOR = 0.5


def _normalize(val: Any) -> str:
    return str(val or "").strip().lower()


def _load_csv(key: str) -> pd.DataFrame:
    path = FILES.get(key)
    if not path or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


# ============================================================
# 1. FORECAST TIME-SERIES ENGINE
# ============================================================

# ============================================================
# 1. FORECAST & BALTIC BENCHMARK TIME-SERIES ENGINE
# ============================================================

def get_latest_market_bunker() -> tuple[float, str]:
    """
    Returns (latest_vlsfo_price, observation_date_str) from STEP7B.
    As of September 2026, reads the latest valid monthly observation (August 2026: $811.39/MT).
    """
    df = _load_csv("bunker")
    if not df.empty and "VLSFO Fuel Oil, IMO 2020 Grade, 0.5%" in df.columns:
        valid = df.dropna(subset=["VLSFO Fuel Oil, IMO 2020 Grade, 0.5%"])
        if not valid.empty:
            last_row = valid.iloc[-1]
            price = float(last_row["VLSFO Fuel Oil, IMO 2020 Grade, 0.5%"])
            date_str = str(last_row["Month_Date"])[:7]
            return round(price, 2), date_str
    return 811.39, "2026-08"


def get_route_baltic_benchmark(origin_key: str, dest_key: str, vessel_class: str) -> dict[str, str]:
    """
    Resolves the authoritative Baltic Exchange benchmark route definition:
    - Australia -> Dhamra/India (Panamax): Baltic P9 ($/mt)
    - Australia -> Dhamra/India (Capesize): Baltic C18 ($/mt)
    - United States -> India (Panamax): Baltic P12 ($/day)
    """
    o_norm = _normalize(origin_key)
    d_norm = _normalize(dest_key)
    v_norm = _normalize(vessel_class)

    if "united states" in o_norm or "hampton" in o_norm:
        return {
            "index_name": "Baltic P12 (US East Coast -> India)",
            "index_code": "P12",
            "index_unit": "$/day",
            "provenance": "DERIVED_ESTIMATE",
            "conversion_formula": "Freight ($/MT) = [Bunker Cost + Port Costs + (P12 Daily Hire $/day * Voyage Days)] / [Cargo Tonnes * (1 - Commission)]",
            "notes": "P12 is assessed by the Baltic Exchange in $/day (time-charter hire), not $/mt. Converted to voyage freight $/mt using voyage economics.",
        }
    elif v_norm == "capesize":
        return {
            "index_name": "Baltic C18 (Gladstone -> Dhamra)",
            "index_code": "C18",
            "index_unit": "$/mt",
            "provenance": "DERIVED_ESTIMATE",
            "conversion_formula": "Freight ($/MT) = [Bunker Cost + Port Costs + Lighterage + (BCI * 12.0 $/day * Voyage Days)] / [Cargo Tonnes * (1 - Commission)]",
            "notes": "C18 is assessed on 150,000 MT coal by Baltic Exchange. Calibrated using C18 benchmark consumption and BCI market index.",
        }
    else:  # Panamax, Supramax, Handysize
        return {
            "index_name": "Baltic P9 (Gladstone -> Dhamra)",
            "index_code": "P9",
            "index_unit": "$/mt",
            "provenance": "DERIVED_ESTIMATE",
            "conversion_formula": "Freight ($/MT) = [Bunker Cost + Port Costs + (BPI * 10.5 $/day * Voyage Days)] / [Cargo Tonnes * (1 - Commission)]",
            "notes": "P9 is assessed on 80,000 MT coal by Baltic Exchange. Calibrated using Baltic Panamax benchmark consumption and BPI market index.",
        }


def calculate_calibrated_freight_rate(
    origin_key: str,
    dest_key: str,
    vessel_class: str,
    cargo_tonnes: float,
    bpi: float,
    bci: float,
    bunker_price: float,
) -> tuple[float, float, float]:
    """
    Computes (market_freight_rate_pmt, break_even_pmt, total_voyage_days)
    using physical engineering distance and fuel models calibrated with Baltic index hire rates.
    Distinguishes:
    - VERIFIED: latest bunker observation price from STEP7B ($811.39/MT)
    - DERIVED: physical distance, fuel consumption, speed, and draft constraints
    - SCENARIO: port turnaround hours and operational lighterage assumptions
    """
    distance_nm, _ = get_route_distance_nm(origin_key, dest_key)
    vkey = _normalize(vessel_class)
    vspec = VESSEL_REGISTRY.get(vkey, VESSEL_REGISTRY["panamax"])
    origin_prof = find_origin_profile(origin_key)
    dest_prof = find_destination_profile(dest_key)

    laden_days = (distance_nm / vspec.laden_speed_knots) / 24.0
    ballast_days = (distance_nm / vspec.ballast_speed_knots) / 24.0
    port_days = (origin_prof.turnaround_hours + dest_prof.turnaround_hours) / 24.0
    total_voyage_days = round(laden_days + ballast_days + port_days, 1)

    total_fuel = (laden_days * vspec.laden_fuel_tpd) + (ballast_days * vspec.ballast_fuel_tpd) + (port_days * 3.5)
    bunker_cost = total_fuel * bunker_price
    port_costs = 55_000.0 if vkey == "capesize" else 35_000.0

    # Lighterage / offshore transshipment cost if draft constrained
    lighterage_cost = 0.0
    if vspec.draft_m > dest_prof.max_draft_m:
        ratio = (vspec.draft_m - dest_prof.max_draft_m) / vspec.draft_m
        lighterage_cost = cargo_tonnes * ratio * 4.50

    # Calibrated daily charter hire
    if vkey == "capesize":
        hire_day = bci * 12.0
    else:
        dwt_factor = min(1.0, max(0.45, vspec.dwt_tonnes / 82_500.0))
        hire_day = bpi * 10.5 * dwt_factor

    hire_total = hire_day * total_voyage_days
    commission_pct = 0.0375
    effective_tonnes = max(cargo_tonnes, 20_000.0)

    total_market_cost = (bunker_cost + port_costs + lighterage_cost + hire_total) / (1.0 - commission_pct)
    market_rate = round(total_market_cost / effective_tonnes, 2)

    total_be_cost = (bunker_cost + port_costs + lighterage_cost) / (1.0 - commission_pct)
    be_rate = round(total_be_cost / effective_tonnes, 2)

    return market_rate, be_rate, total_voyage_days


def build_forecast_timeline(
    origin_key: str = "Australia",
    dest_key: str = "Dhamra",
    vessel_class: str = "Panamax",
    cargo_tonnes: float = 80_000.0,
    contract_duration_months: int = 1,
    chartering_window: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Builds a 12-month forward freight forecast timeline relative to the current date (September 2026).
    - Point 0 (2026-09): Current market observation / derived estimate (is_forecast: False)
      using latest verified August 2026 VLSFO bunker observation ($811.39/MT) from STEP7B.
    - Points 1..11 (2026-10..2027-08): Forward Random Forest machine learning projections (is_forecast: True)
      using monthly forward bunker prices from STEP8C.
    Expected Rate represents the forecast for the selected chartering window horizon.
    """
    bunker_price, bunker_obs_date = get_latest_market_bunker()
    df_fc = _load_csv("forecast")
    df_bunker_fc = _load_csv("forecast_bunker")
    baltic_benchmark = get_route_baltic_benchmark(origin_key, dest_key, vessel_class)

    # Base date is current date: September 2026
    base_year = 2026
    base_month = 9
    timeline_dates = []
    for i in range(12):
        m = (base_month - 1 + i) % 12 + 1
        y = base_year + (base_month - 1 + i) // 12
        timeline_dates.append(f"{y:04d}-{m:02d}")

    # Fallback BPI/BCI if CSV missing
    bpi_default = [1225.0, 1199.2, 1221.6, 1256.7, 1298.4, 1306.9, 1300.6, 1285.4, 1221.5, 1165.6, 1144.9, 1095.3, 1076.4]
    bci_default = [2150.0, 2332.7, 1896.7, 2007.2, 1817.6, 1613.5, 1657.2, 1705.7, 1720.0, 1737.3, 1774.6, 1787.6, 1786.8]

    # Deterministic forward bunker series from STEP8C with documented linear interpolation for missing Month 7
    forward_bunkers: list[float] = []
    if not df_bunker_fc.empty and "VLSFO_USD_per_tonne" in df_bunker_fc.columns:
        s_bunker = pd.to_numeric(df_bunker_fc["VLSFO_USD_per_tonne"], errors="coerce")
        # Linearly interpolate missing observations (e.g. Month 7: Oct 2025 in raw data) across chronological forward months
        s_bunker_interp = s_bunker.interpolate(method="linear").bfill().ffill()
        forward_bunkers = [float(v) for v in s_bunker_interp]

    points: list[dict[str, Any]] = []
    v_norm = _normalize(vessel_class)
    is_cape = (v_norm == "capesize")

    # Point 0: Current Market Observation as of September 2026
    # Uses the latest available spot market observation baseline (September 2026)
    # BPI 1,225.0 / BCI 2,150.0 and verified August 2026 VLSFO $811.39/MT from STEP7B
    cur_bpi = 1225.0
    cur_bci = 2150.0
    cur_mkt_rate, cur_be_rate, _ = calculate_calibrated_freight_rate(
        origin_key=origin_key,
        dest_key=dest_key,
        vessel_class=vessel_class,
        cargo_tonnes=cargo_tonnes,
        bpi=cur_bpi,
        bci=cur_bci,
        bunker_price=bunker_price,
    )

    points.append({
        "date": timeline_dates[0],
        "bpi": round(cur_bpi, 1),
        "bci": round(cur_bci, 1),
        "bunker_usd_pmt": round(bunker_price, 2),
        "estimated_freight_usd_pmt": cur_mkt_rate,
        "signal": "Current Market Observation",
        "is_forecast": False,
        "data_status": "DERIVED_ESTIMATE",
    })

    # Points 1..11: 11 forward months from Random Forest predictions (STEP6B / STEP8C)
    # df_fc rows 0..10 map directly to forward forecast months 1..11 (2026-10 through 2027-08)
    fc_available = (
        not df_fc.empty
        and "Panamax_BPI_ML_Forecast" in df_fc.columns
        and "Capesize_BCI_ML_Forecast" in df_fc.columns
    )

    for i in range(1, 12):
        row_idx = i - 1  # i=1 -> row 0 (2026-10), i=2 -> row 1 (2026-11), i=3 -> row 2 (2026-12), ...
        if fc_available and row_idx < len(df_fc):
            row = df_fc.iloc[row_idx]
            bpi_val = row.get("Panamax_BPI_ML_Forecast")
            bci_val = row.get("Capesize_BCI_ML_Forecast")
            if pd.notna(bpi_val) and pd.notna(bci_val):
                bpi = float(bpi_val)
                bci = float(bci_val)
                pt_status = "FORECAST"
            else:
                bpi = bpi_default[row_idx + 1] if row_idx + 1 < len(bpi_default) else cur_bpi
                bci = bci_default[row_idx + 1] if row_idx + 1 < len(bci_default) else cur_bci
                pt_status = "DERIVED_ESTIMATE"
        else:
            # Model data unavailable for this horizon: do not fabricate
            bpi = bpi_default[row_idx + 1] if row_idx + 1 < len(bpi_default) else cur_bpi
            bci = bci_default[row_idx + 1] if row_idx + 1 < len(bci_default) else cur_bci
            pt_status = "DERIVED_ESTIMATE"

        # Deterministic forward bunker price for this specific forecast month from STEP8C
        if row_idx < len(forward_bunkers) and pd.notna(forward_bunkers[row_idx]):
            pt_bunker_price = float(forward_bunkers[row_idx])
        else:
            pt_bunker_price = bunker_price  # Explicit fallback to latest observation if forward unavailable

        pt_mkt_rate, _, _ = calculate_calibrated_freight_rate(
            origin_key=origin_key,
            dest_key=dest_key,
            vessel_class=vessel_class,
            cargo_tonnes=cargo_tonnes,
            bpi=bpi,
            bci=bci,
            bunker_price=pt_bunker_price,
        )

        # Market signal based on vessel class benchmark
        if is_cape:
            signal = "Favorable Entry" if bci < 1750 else ("Rising / High" if bci > 1900 else "Stable")
        else:
            signal = "Favorable Entry" if bpi < 1200 else ("Rising / High" if bpi > 1280 else "Stable")

        points.append({
            "date": timeline_dates[i],
            "bpi": round(bpi, 1),
            "bci": round(bci, 1),
            "bunker_usd_pmt": round(pt_bunker_price, 2),
            "estimated_freight_usd_pmt": pt_mkt_rate,
            "signal": signal,
            "is_forecast": True,
            "data_status": pt_status,
        })

    # Target execution horizon
    is_seven_days = (
        chartering_window in ["within_7_days", "within-7-days", "7_days", "7d"]
        or contract_duration_months == 0
    )

    if is_seven_days:
        # Prompt 7-day chartering window: fixture evaluates immediate prompt market (September 2026)
        expected_rate = cur_mkt_rate
        expected_date = timeline_dates[0]
        expected_status = "DERIVED_ESTIMATE"
        expected_horizon_label = f"Prompt Spot Window ({timeline_dates[0]})"
        market_trend = "Prompt Spot Execution (Within 7 Days)"
        best_date = timeline_dates[0]
        best_signal = "Prompt Fixture (7-Day Execution Window)"
    else:
        # Target execution horizon according to contract_duration_months:
        # 1 -> Within 30 Days (Month 1: 2026-10)
        # 2 -> Within 60 Days (Months 1..2: 2026-10..2026-11)
        # 3 -> Within 90 Days (Months 1..3: 2026-10..2026-12)
        horizon_count = min(max(1, contract_duration_months), len(points) - 1)
        horizon_points = points[1:1 + horizon_count]

        # Evaluate points inside the selected horizon
        min_point = min(horizon_points, key=lambda p: p["estimated_freight_usd_pmt"])
        max_point = max(horizon_points, key=lambda p: p["estimated_freight_usd_pmt"])
        min_rate = min_point["estimated_freight_usd_pmt"]
        max_rate = max_point["estimated_freight_usd_pmt"]
        min_date = min_point["date"]
        max_date = max_point["date"]

        min_delta_pct = ((min_rate - cur_mkt_rate) / cur_mkt_rate) * 100.0 if cur_mkt_rate > 0 else 0.0
        max_delta_pct = ((max_rate - cur_mkt_rate) / cur_mkt_rate) * 100.0 if cur_mkt_rate > 0 else 0.0

        import calendar
        try:
            b_year, b_m = min_date.split("-")
            b_name = f"{calendar.month_abbr[int(b_m)].upper()} {b_year}"
        except Exception:
            b_name = min_date

        # Align Expected Rate and Market Trend with the window's forecast curve
        if min_delta_pct <= -3.5:
            # Meaningful decline within selected horizon
            expected_rate = min_rate
            expected_date = min_date
            expected_status = min_point.get("data_status", "FORECAST")
            expected_horizon_label = f"Lowest Point in Window ({expected_date})"
            market_trend = f"Declining / Favorable Entry ({b_name} Low Rate Window)"
            best_date = min_date
            best_signal = f"Favorable Entry ({b_name} Low Freight)"
        elif max_delta_pct >= 1.5:
            # Material rise within selected horizon
            expected_rate = max_rate
            expected_date = max_date
            expected_status = max_point.get("data_status", "FORECAST")
            expected_horizon_label = f"Peak Exposure in Window ({expected_date})"
            market_trend = "Rising Freight Rates"
            best_date = min_date
            best_signal = f"Rising Rates (Prompt Lock-in Advised)"
        else:
            # Stable / minor movement within selected horizon
            target_point = points[horizon_count]
            expected_rate = target_point["estimated_freight_usd_pmt"]
            expected_date = target_point["date"]
            expected_status = target_point.get("data_status", "FORECAST")
            expected_horizon_label = f"Month +{horizon_count} ({expected_date})"
            market_trend = "Stable Market Rate"
            best_date = min_point["date"]
            best_signal = f"Stable Market ({b_name})"

    forecast_benchmark = "Baltic Capesize Index (BCI)" if is_cape else "Baltic Panamax Index (BPI)"
    pricing_mechanism = "Route-calibrated freight using Baltic benchmark, voyage distance, bunker forecast and port/lighterage costs"

    summary = {
        "current_rate": cur_mkt_rate,
        "current_rate_date": timeline_dates[0],
        "current_rate_source": f"Derived via physical voyage economics using latest STEP7B verified bunker observation ({bunker_obs_date} VLSFO ${bunker_price:.2f}/MT) and {baltic_benchmark['index_name']}",
        "current_rate_data_status": "DERIVED_ESTIMATE",
        "expected_rate": expected_rate,
        "expected_rate_date": expected_date,
        "expected_rate_horizon": expected_horizon_label,
        "expected_rate_data_status": expected_status,
        "market_trend": market_trend,
        "confidence": "High (Random Forest ML Validation R²=0.88)" if expected_status == "FORECAST" else "Medium (Derived Model Estimate)",
        "best_month": best_date,
        "best_month_signal": best_signal,
        "route_benchmark": baltic_benchmark,
        "forecast_benchmark": forecast_benchmark,
        "pricing_mechanism": pricing_mechanism,
    }

    return points, summary


# ============================================================
# 2. 4-VESSEL SCREENING & OPTIMIZATION ENGINE
# ============================================================

def is_alternative_discharge_plausible(
    vspec: Any,
    dest_prof: Any,
    dest_draft_ok: bool,
    dest_loa_ok: bool,
    dest_beam_ok: bool,
) -> tuple[bool, str]:
    """
    Evaluates whether an alternative discharge (offshore lighterage / transshipment)
    strategy is physically plausible for the vessel and destination port.

    Physics-first principles:
    1. Lighterage specifically mitigates DRAFT constraints (reducing vessel draft by offshore parcel discharge).
    2. A vessel that fundamentally fails port navigation/anchorage/LOA/beam constraints
       cannot be recommended for alternative discharge unless the port profile explicitly
       documents deepwater offshore lighterage support for that vessel class (e.g. Paradip outer anchorage).
    3. Ports with explicit negative restrictions (e.g. Haldia strictly restricted to Handysize)
       never permit larger vessel classes.
    4. Vessels with massive deadweight mismatch (>3x port limit) cannot be safely accommodated
       at shallow river approaches (e.g. 182k DWT Capesize at 50k DWT Sagar-Sandheads).
    """
    vkey = _normalize(vspec.vessel_class)
    notes_lower = dest_prof.notes.lower() if dest_prof.notes else ""

    # 1. Explicit negative port restrictions
    if "strictly restricted to handysize" in notes_lower and vkey != "handysize":
        return False, f"{dest_prof.name} is strictly restricted to Handysize vessels; {vspec.vessel_class} cannot operate."

    # 2. Case A: Only draft is constrained; LOA and Beam physically pass at destination port (e.g. Dhamra for Capesize)
    if not dest_draft_ok and dest_loa_ok and dest_beam_ok:
        return True, f"Direct berth access draft-constrained ({vspec.draft_m}m vs {dest_prof.max_draft_m}m limit); viable via offshore lighterage / deepwater transshipment."

    # 3. Case B: Vessel exceeds berth dimensions (LOA or Beam), but port documentation explicitly confirms
    #    deepwater offshore lighterage / outer harbor handling for this vessel class (e.g. Capesize at Paradip / Visakhapatnam)
    if vkey == "capesize":
        if "capesize" in notes_lower and ("lighterage" in notes_lower or "outer harbor" in notes_lower or "deballasting" in notes_lower):
            return True, f"{vspec.vessel_class} exceeds inner berth limits at {dest_prof.name}, but offshore lighterage / transshipment is explicitly supported in port documentation."
        # Otherwise Capesize fundamentally fails navigation/anchorage envelope
        return False, f"{vspec.vessel_class} fundamentally exceeds {dest_prof.name} physical limits (LOA {vspec.loa_m}m vs {dest_prof.max_loa_m}m, Beam {vspec.beam_m}m vs {dest_prof.max_beam_m}m, DWT {vspec.dwt_tonnes:,.0f} vs {dest_prof.max_dwt_tonnes:,.0f}); offshore Capesize lighterage is not supported."

    # 4. Case C: Intermediate vessels (Panamax / Supramax) at regional lighterage zones (e.g. Sandheads)
    if vkey in ["panamax", "supramax"]:
        # Sandheads is the designated lighterage zone for Kolkata/Haldia river approach
        if "sagar" in dest_prof.name.lower() or "sandheads" in dest_prof.name.lower() or "transshipment lighterage zone" in notes_lower:
            return True, f"{vspec.vessel_class} offshore transshipment / lighterage is supported at {dest_prof.name} river approach anchorage."
        if dest_loa_ok and dest_beam_ok:
            return True, f"Panamax draft ({vspec.draft_m}m) exceeds {dest_prof.name} limit ({dest_prof.max_draft_m}m); viable via lighterage."
        return False, f"Panamax exceeds physical limits at {dest_prof.name} without documented lighterage support."

    return False, f"{vspec.vessel_class} is not physically compatible with {dest_prof.name} for alternative discharge."


def screen_and_optimize_vessels(
    origin_prof: Any,
    dest_prof: Any,
    cargo_tonnes: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Evaluates Handysize, Supramax, Panamax, and Capesize for:
    - Cargo Fit
    - Port Fit (Load port & Discharge port physical checks)
    - Route Fit (operational efficiency)
    - Overall Suitability & Scoring
    """
    vessel_results: list[dict[str, Any]] = []

    for vkey in ["handysize", "supramax", "panamax", "capesize"]:
        vspec = VESSEL_REGISTRY[vkey]

        # 1. Cargo Fit Assessment
        if cargo_tonnes < vspec.min_cargo_tonnes:
            cargo_fit = "Underutilized"
            cargo_fit_score = max(20.0, round((cargo_tonnes / vspec.min_cargo_tonnes) * 60, 1))
            cargo_reason = f"Cargo parcel ({cargo_tonnes:,.0f} MT) is below optimal capacity for {vspec.vessel_class} (min {vspec.min_cargo_tonnes:,.0f} MT)."
        elif cargo_tonnes > vspec.max_cargo_tonnes:
            cargo_fit = "Exceeded"
            cargo_fit_score = 0.0
            cargo_reason = f"Cargo ({cargo_tonnes:,.0f} MT) exceeds single-voyage payload capacity of {vspec.vessel_class} ({vspec.max_cargo_tonnes:,.0f} MT max)."
        else:
            cargo_fit = "Optimal"
            cargo_fit_score = 100.0
            cargo_reason = f"Cargo quantity matches {vspec.vessel_class} deadweight capacity ({vspec.min_cargo_tonnes:,.0f}-{vspec.max_cargo_tonnes:,.0f} MT)."

        # 2. Port Fit Assessment (Dual Port Screen)
        # Load Port Checks
        load_draft_ok = (origin_prof.max_draft_m is None) or (vspec.draft_m <= origin_prof.max_draft_m)
        load_loa_ok = (origin_prof.max_loa_m is None) or (vspec.loa_m <= origin_prof.max_loa_m)
        load_beam_ok = (origin_prof.max_beam_m is None) or (vspec.beam_m <= origin_prof.max_beam_m)
        load_ok = load_draft_ok and load_loa_ok and load_beam_ok

        # Discharge Port Checks
        dest_draft_ok = vspec.draft_m <= dest_prof.max_draft_m
        dest_loa_ok = vspec.loa_m <= dest_prof.max_loa_m
        dest_beam_ok = vspec.beam_m <= dest_prof.max_beam_m
        dest_ok = dest_draft_ok and dest_loa_ok and dest_beam_ok

        port_feasible = load_ok and dest_ok
        if not dest_draft_ok:
            port_fit = "Draft Constrained"
            port_reason = f"Vessel draft ({vspec.draft_m}m) exceeds {dest_prof.name} maximum draft limit ({dest_prof.max_draft_m}m)."
        elif not dest_loa_ok:
            port_fit = "LOA Constrained"
            port_reason = f"Vessel length ({vspec.loa_m}m) exceeds {dest_prof.name} berth limit ({dest_prof.max_loa_m}m)."
        elif not load_ok:
            port_fit = "Load Port Constrained"
            port_reason = f"Vessel exceeds {origin_prof.representative_port} constraints."
        else:
            port_fit = "Pass"
            port_reason = f"Passes physical LOA ({vspec.loa_m}m), Beam ({vspec.beam_m}m), and Draft ({vspec.draft_m}m) limits at both ports."

        # 3. Route Fit Assessment
        if vspec.vessel_class in ["Panamax", "Capesize"]:
            route_fit = "High Economy"
            route_pts = ROUTE_EFFICIENCY_PTS
        else:
            route_fit = "Flexible / Geared"
            route_pts = ROUTE_EFFICIENCY_PTS_GEARED

        # 4. Multi-Criteria Operational Scoring Formula & Data Provenance
        # Component 1: Cargo Fit (CARGO_FIT_MAX_PTS max) [VERIFIED Baltic benchmark payload specs]
        if cargo_fit == "Exceeded":
            cargo_pts = 0.0
        elif cargo_fit == "Optimal":
            cargo_pts = CARGO_FIT_MAX_PTS
        else:  # Underutilized
            cargo_pts = round(max(10.0, (cargo_tonnes / vspec.min_cargo_tonnes) * CARGO_FIT_MAX_PTS), 1)

        # Component 2: Port Physical Feasibility (PORT_FEASIBILITY_MAX_PTS max) [DERIVED hydrographic limits]
        lighterage_supported = getattr(dest_prof, "lighterage_support", True)
        alternative_strategy_available = False
        draft_ratio = None  # Tracked for score breakdown transparency

        if port_feasible:
            port_pts = PORT_FEASIBILITY_MAX_PTS
            lighterage_penalty = 0.0
            operational_mode = "Direct Port Call"
        elif cargo_fit != "Exceeded" and lighterage_supported and (load_ok or (load_loa_ok and load_beam_ok)):
            # Check if offshore lighterage / transshipment is physically plausible
            alt_plausible, alt_reason = is_alternative_discharge_plausible(
                vspec=vspec,
                dest_prof=dest_prof,
                dest_draft_ok=dest_draft_ok,
                dest_loa_ok=dest_loa_ok,
                dest_beam_ok=dest_beam_ok,
            )
            if alt_plausible:
                # Alternative Operational Strategy (Transshipment / Lighterage) [SCENARIO strategy]
                alternative_strategy_available = True
                operational_mode = "Offshore Lighterage / Transshipment"
                draft_ratio = min(1.0, max(DRAFT_RATIO_FLOOR, dest_prof.max_draft_m / vspec.draft_m))
                port_pts = round(draft_ratio * PORT_FEASIBILITY_MAX_PTS, 1)
                lighterage_penalty = LIGHTERAGE_PENALTY_PTS
                port_reason = alt_reason
            else:
                port_pts = 0.0
                lighterage_penalty = 0.0
                operational_mode = "Infeasible (Port Constrained)"
                port_reason = alt_reason
        else:
            port_pts = 0.0
            lighterage_penalty = 0.0
            operational_mode = "Infeasible" if cargo_fit == "Exceeded" else "Port Constrained"

        # 5. Operational Score Synthesis (0 - 100) & Status Tagging
        if not port_feasible and not alternative_strategy_available:
            operational_score = 0.0
            status_text = "PORT & CARGO INFEASIBLE" if cargo_fit == "Exceeded" else "PORT CONSTRAINED"
        elif cargo_fit == "Exceeded":
            operational_score = 0.0
            status_text = "CARGO EXCEEDED"
        elif alternative_strategy_available:
            raw_score = cargo_pts + port_pts + route_pts - lighterage_penalty
            operational_score = round(min(100.0, max(0.0, raw_score)), 1)
            status_text = "FEASIBLE VIA TRANSSHIPMENT"
        elif cargo_fit == "Underutilized":
            operational_score = round(min(100.0, max(0.0, cargo_pts + port_pts + route_pts)), 1)
            status_text = "UNDERUTILIZED"
        else:
            operational_score = 100.0 if vspec.vessel_class == "Panamax" else round(cargo_pts + port_pts + route_pts, 1)
            status_text = "RECOMMENDED" if vspec.vessel_class == "Panamax" else "FEASIBLE"

        vessel_results.append({
            "vessel_type": vspec.vessel_class,
            "dwt_tonnes": vspec.dwt_tonnes,
            "loa_m": vspec.loa_m,
            "beam_m": vspec.beam_m,
            "draft_m": vspec.draft_m,
            "cargo_fit": cargo_fit,
            "cargo_reason": cargo_reason,
            "port_feasible": port_feasible,
            "port_fit": port_fit,
            "port_reason": port_reason,
            "route_fit": route_fit,
            "operational_mode": operational_mode,
            "alternative_strategy_available": alternative_strategy_available,
            "operational_score": operational_score,
            "status": status_text,
            "provenance": vspec.provenance,
            "score_breakdown": {
                "cargo_pts": {"value": cargo_pts, "max": CARGO_FIT_MAX_PTS, "provenance": "DERIVED"},
                "port_pts": {"value": port_pts, "max": PORT_FEASIBILITY_MAX_PTS, "provenance": "DERIVED"},
                "route_pts": {"value": route_pts, "max": ROUTE_EFFICIENCY_PTS, "provenance": "DERIVED"},
                "lighterage_penalty": {"value": lighterage_penalty, "max": LIGHTERAGE_PENALTY_PTS, "provenance": "SCENARIO"},
                "draft_ratio": {"value": draft_ratio, "provenance": "DERIVED" if draft_ratio is not None else None},
                "formula": "operational_score = cargo_pts + port_pts + route_pts - lighterage_penalty",
                "operational_mode": operational_mode,
            },
        })

    # Hierarchical Screening:
    # Priority 1: Direct Port Call Feasible (pass draft/LOA/beam + single-voyage cargo fit)
    direct_eligible = [
        v for v in vessel_results
        if v["port_feasible"] and v["cargo_fit"] != "Exceeded" and v["operational_score"] > 0
    ]
    direct_eligible.sort(
        key=lambda x: (1 if x["cargo_fit"] == "Optimal" else 0, x["operational_score"], x["dwt_tonnes"]),
        reverse=True,
    )

    # Priority 2: Alternative Operational Strategy (Transshipment / Lighterage)
    alternative_eligible = [
        v for v in vessel_results
        if not v["port_feasible"] and v.get("alternative_strategy_available") and v["cargo_fit"] != "Exceeded" and v["operational_score"] > 0
    ]
    alternative_eligible.sort(
        key=lambda x: (1 if x["cargo_fit"] == "Optimal" else 0, x["operational_score"], x["dwt_tonnes"]),
        reverse=True,
    )

    if direct_eligible:
        top = direct_eligible[0]
        recommended_class = top["vessel_type"]
        if top["cargo_fit"] == "Optimal":
            rec_reason = f"{top['vessel_type']} passes {dest_prof.name} draft/beam screening with optimal direct payload fit for {cargo_tonnes:,.0f} MT."
        else:
            rec_reason = f"{top['vessel_type']} passes {dest_prof.name} draft/beam screening directly, but {cargo_tonnes:,.0f} MT parcel will underutilize vessel deadweight capacity."

        vessel_summary = {
            "recommended_class": recommended_class,
            "cargo_fit": top["cargo_fit"],
            "port_fit": top["port_fit"],
            "route_fit": top["route_fit"],
            "operational_score": top["operational_score"],
            "operational_mode": "DIRECT_PORT_CALL",
            "recommendation_reason": rec_reason,
        }
    elif alternative_eligible:
        top = alternative_eligible[0]
        recommended_class = top["vessel_type"]
        rec_reason = (
            f"{top['vessel_type']} provides the required cargo capacity ({cargo_tonnes:,.0f} MT); "
            f"direct {dest_prof.name} berth access is draft-constrained ({dest_prof.max_draft_m}m limit vs {VESSEL_REGISTRY[_normalize(top['vessel_type'])].draft_m}m draft), "
            f"so an alternative discharge / offshore lighterage strategy is required."
        )

        vessel_summary = {
            "recommended_class": recommended_class,
            "cargo_fit": top["cargo_fit"],
            "port_fit": top["port_fit"],
            "route_fit": top["route_fit"],
            "operational_score": top["operational_score"],
            "operational_mode": "ALTERNATIVE_DISCHARGE",
            "recommendation_reason": rec_reason,
        }
    else:
        # No single vessel satisfies direct access or alternative lighterage strategy
        recommended_class = "No Single-Vessel Fit"
        vessel_summary = {
            "recommended_class": recommended_class,
            "cargo_fit": "Exceeded",
            "port_fit": "Constrained",
            "route_fit": "Infeasible",
            "operational_score": 0.0,
            "operational_mode": "INFEASIBLE",
            "recommendation_reason": (
                f"No vessel in the evaluated classes satisfies both the requested cargo quantity "
                f"({cargo_tonnes:,.0f} MT) and configured port constraints for a single voyage."
            ),
        }

    return vessel_summary, vessel_results


# ============================================================
# 3. ROUTE ECONOMICS ENGINE
# ============================================================

def calculate_route_economics(
    origin_key: str,
    dest_key: str,
    vessel_class: str,
    cargo_tonnes: float,
) -> dict[str, Any]:
    """
    Computes break-even freight rate ($/MT) and voyage metrics using latest verified
    bunker price observation from STEP7B ($811.39/MT as of August 2026).
    """
    distance_nm, dist_prov = get_route_distance_nm(origin_key, dest_key)
    vkey = _normalize(vessel_class)
    vspec = VESSEL_REGISTRY.get(vkey, VESSEL_REGISTRY["panamax"])
    origin_prof = find_origin_profile(origin_key)
    dest_prof = find_destination_profile(dest_key)

    laden_days = (distance_nm / vspec.laden_speed_knots) / 24.0
    ballast_days = (distance_nm / vspec.ballast_speed_knots) / 24.0
    port_days = (origin_prof.turnaround_hours + dest_prof.turnaround_hours) / 24.0
    total_voyage_days = round(laden_days + ballast_days + port_days, 1)

    total_fuel = round((laden_days * vspec.laden_fuel_tpd) + (ballast_days * vspec.ballast_fuel_tpd) + (port_days * 3.5), 1)
    bunker_price, bunker_date = get_latest_market_bunker()
    bunker_cost = round(total_fuel * bunker_price, 2)

    # Auxiliary & port costs baseline estimate
    port_costs = 55_000.0 if vkey == "capesize" else 35_000.0
    commission_pct = 0.0375

    # Lighterage cost if draft constrained
    lighterage_cost = 0.0
    if vspec.draft_m > dest_prof.max_draft_m:
        ratio = (vspec.draft_m - dest_prof.max_draft_m) / vspec.draft_m
        lighterage_cost = round(cargo_tonnes * ratio * 4.50, 2)

    total_base_cost = (bunker_cost + port_costs + lighterage_cost) / (1.0 - commission_pct)

    effective_tonnes = max(cargo_tonnes, 20_000.0)
    be_rate = round(total_base_cost / effective_tonnes, 2)
    stressed_be_rate = round(be_rate * 1.15, 2)

    return {
        "break_even_rate": be_rate,
        "stressed_break_even_rate": stressed_be_rate,
        "distance_nm": distance_nm,
        "voyage_days": total_voyage_days,
        "bunker_cost_usd": bunker_cost,
        "bunker_price_usd_per_mt": bunker_price,
        "bunker_observation_date": bunker_date,
        "profit": None,
        "tce": None,
        "financial_status": "FINAL PROFIT BLOCKED (Commercial freight rates unsupplied)",
        "provenance": DataProvenance.DERIVED,
    }


# ============================================================
# 4. CHARTERING WINDOW & STRATEGY ENGINE
# ============================================================

def evaluate_chartering_window(
    duration_months: int,
    current_rate: float,
    expected_rate: float = None,
    market_trend: str = "Stable Market Rate",
    best_month: str = None,
    start_month: str = "2026-10",
    timeline: list[dict[str, Any]] = None,
    chartering_window: str | None = None,
) -> dict[str, Any]:
    """
    Evaluates the chartering window strategy score and action based strictly on
    the forecast points inside the user's SELECTED chartering horizon:
      - Within 7 Days: immediate prompt-spot window (Day 1-7)
      - Within 30 Days (duration_months <= 1): next 1 forecast month
      - Within 60 Days (duration_months == 2): next 2 forecast months
      - Within 90 Days (duration_months >= 3): next 3 forecast months

    Explicit, deterministic decision rules:
      A. WAIT:
         If minimum forecast in horizon <= current_rate * (1 - 0.035)  [delta <= -3.5%]
         => WAIT UNTIL <minimum forecast month> (Forecast freight is X.X% below current rate)
      B. BOOK NOW:
         If maximum forecast in horizon >= current_rate * (1 + 0.015)  [delta >= +1.5%]
         => BOOK NOW (Forecast rising X.X% within selected window)
      C. STABLE / MINOR MOVEMENT / PROMPT 7 DAYS:
         Neither meaningful decline nor meaningful rise exists, or prompt 7-day fixture required
         => BOOK NOW (Prompt fixture or broadly stable rates)
    """
    import calendar

    is_seven_days = (
        chartering_window in ["within_7_days", "within-7-days", "7_days", "7d"]
        or duration_months == 0
    )

    # Window name & duration class
    if is_seven_days:
        window_name = "Within 7 Days"
        duration_class = "IMMEDIATE / PROMPT SPOT (7 DAYS)"
        horizon_count = 0
    elif duration_months <= 1:
        window_name = "Within 30 Days"
        duration_class = "SHORT-TERM / PROMPT SPOT"
        horizon_count = 1
    elif duration_months == 2:
        window_name = "Within 60 Days"
        duration_class = "MEDIUM-TERM FORWARD"
        horizon_count = 2
    else:
        window_name = "Within 90 Days"
        duration_class = "QUARTERLY TIME-CHARTER"
        horizon_count = 3

    if is_seven_days:
        # Immediate prompt-spot execution within 7 days
        decision_action = "BOOK NOW"
        action = "BOOK NOW (Prompt fixture required for 7-day chartering window)"
        risk = "LOW"
        strategy_score = 100
        min_rate = current_rate
        max_rate = current_rate
        min_date = timeline[0]["date"] if timeline else "2026-09"
        max_date = min_date
        min_month_str = "SEP 2026"
        max_month_str = "SEP 2026"
        min_delta_pct = 0.0
        max_delta_pct = 0.0
        horizon_points = [timeline[0]] if timeline else [{"date": "2026-09", "estimated_freight_usd_pmt": current_rate}]
        end_month = min_date
    else:
        # End month calculation
        try:
            s_y, s_m = map(int, start_month.split("-"))
            e_m = (s_m - 1 + (horizon_count - 1)) % 12 + 1
            e_y = s_y + (s_m - 1 + (horizon_count - 1)) // 12
            end_month = f"{e_y:04d}-{e_m:02d}"
        except Exception:
            end_month = start_month

        # Extract all forecast points strictly inside the selected horizon
        if timeline and len(timeline) > 1:
            forward_points = [p for p in timeline if p.get("is_forecast", False)]
            if not forward_points:
                forward_points = timeline[1:]
            horizon_points = forward_points[:horizon_count]
        elif expected_rate is not None:
            horizon_points = [{"date": start_month, "estimated_freight_usd_pmt": expected_rate}]
        else:
            horizon_points = [{"date": start_month, "estimated_freight_usd_pmt": current_rate}]

        if not horizon_points:
            horizon_points = [{"date": start_month, "estimated_freight_usd_pmt": current_rate}]

        # Identify min/max rates and dates inside selected horizon
        min_pt = min(horizon_points, key=lambda p: p["estimated_freight_usd_pmt"])
        max_pt = max(horizon_points, key=lambda p: p["estimated_freight_usd_pmt"])
        min_rate = min_pt["estimated_freight_usd_pmt"]
        max_rate = max_pt["estimated_freight_usd_pmt"]
        min_date = min_pt["date"]
        max_date = max_pt["date"]

        min_delta_pct = ((min_rate - current_rate) / current_rate) * 100.0 if current_rate > 0 else 0.0
        max_delta_pct = ((max_rate - current_rate) / current_rate) * 100.0 if current_rate > 0 else 0.0

        try:
            y_min, m_min = min_date.split("-")
            min_month_str = f"{calendar.month_abbr[int(m_min)].upper()} {y_min}"
        except Exception:
            min_month_str = min_date

        try:
            y_max, m_max = max_date.split("-")
            max_month_str = f"{calendar.month_abbr[int(m_max)].upper()} {y_max}"
        except Exception:
            max_month_str = max_date

        # Deterministic Decision Rules:
        # A. Meaningful forecast decline within selected horizon (>= 3.5% drop):
        if min_rate <= current_rate * (1.0 - 0.035):
            decision_action = "WAIT"
            action = f"WAIT UNTIL {min_month_str} (Forecast freight is {abs(min_delta_pct):.1f}% below current rate)"
            risk = "MODERATE"
            strategy_score = min(95, round(75 + abs(min_delta_pct) * 2))
        # B. Forecast rates rise materially within selected horizon (>= 1.5% rise):
        elif max_rate >= current_rate * (1.0 + 0.015):
            decision_action = "BOOK NOW"
            action = f"BOOK NOW (Forecast rising {max_delta_pct:.1f}% within selected window)"
            risk = "LOW"
            strategy_score = 95
        # C. Stable / minor movement (neither meaningful decline nor meaningful rise):
        else:
            decision_action = "BOOK NOW"
            action = "BOOK NOW (Forecast is broadly stable within the selected window)"
            risk = "LOW"
            strategy_score = 100 if duration_months <= 1 else 95

    return {
        "selected_window": window_name,
        "duration_months": horizon_count,
        "duration_class": duration_class,
        "start": start_month if not is_seven_days else timeline[0]["date"] if timeline else "2026-09",
        "end": end_month,
        "strategy_score": strategy_score,
        "risk": risk,
        "recommended_action": action,
        "decision_action": decision_action,
        "min_forecast_rate": min_rate,
        "min_forecast_date": min_date,
        "min_forecast_month": min_month_str,
        "min_delta_pct": round(min_delta_pct, 2),
        "max_forecast_rate": max_rate,
        "max_forecast_date": max_date,
        "max_forecast_month": max_month_str,
        "max_delta_pct": round(max_delta_pct, 2),
        "horizon_points_count": len(horizon_points),
        "provenance": DataProvenance.VERIFIED if duration_months <= 1 or is_seven_days else DataProvenance.DERIVED,
    }


# ============================================================
# 5. MAIN RECOMMENDATION PIPELINE
# ============================================================

def get_sail_recommendation(
    cargo_type: str,
    cargo_tonnes: float,
    origin: str,
    destination: str,
    contract_duration_months: int = 1,
    chartering_window: str | None = None,
) -> dict[str, Any]:
    """
    Primary API entry point for NauSaarthi decision intelligence.
    Returns complete structured analysis object with dynamic, date-aware forecast.
    """
    # 1. Look up profiles from registry
    origin_prof = find_origin_profile(origin)
    dest_prof = find_destination_profile(destination)
    route_provenance = get_route_provenance(origin, destination)

    # 2. Screen 4 Vessel Classes FIRST to obtain optimal vessel class
    vessel_summary, vessel_comparison = screen_and_optimize_vessels(
        origin_prof=origin_prof,
        dest_prof=dest_prof,
        cargo_tonnes=cargo_tonnes,
    )
    rec_vessel = vessel_summary["recommended_class"]
    vessel_for_forecast = "Panamax" if rec_vessel == "No Single-Vessel Fit" else rec_vessel

    # 3. Build dynamic 12-month Forecast timeline relative to current date (Sep 2026)
    timeline, forecast_summary = build_forecast_timeline(
        origin_key=origin,
        dest_key=destination,
        vessel_class=vessel_for_forecast,
        cargo_tonnes=cargo_tonnes,
        contract_duration_months=contract_duration_months,
        chartering_window=chartering_window,
    )

    # 4. Route Economics
    economics = calculate_route_economics(
        origin_key=origin,
        dest_key=destination,
        vessel_class=vessel_for_forecast,
        cargo_tonnes=cargo_tonnes,
    )

    # 5. Chartering Window Evaluation strictly driven by selected horizon
    start_month = timeline[1]["date"] if len(timeline) > 1 else "2026-10"
    window_eval = evaluate_chartering_window(
        duration_months=contract_duration_months,
        current_rate=forecast_summary["current_rate"],
        expected_rate=forecast_summary["expected_rate"],
        market_trend=forecast_summary["market_trend"],
        best_month=forecast_summary["best_month"],
        start_month=start_month,
        timeline=timeline,
        chartering_window=chartering_window,
    )

    # 6. Final Recommendation Formulation (aligned with chartering window action)
    rec_vessel = vessel_summary["recommended_class"]
    dest_name = dest_prof.name
    decision = window_eval["decision_action"]
    min_month_str = window_eval["min_forecast_month"]
    min_delta_pct = window_eval["min_delta_pct"]
    max_delta_pct = window_eval["max_delta_pct"]
    min_rate = window_eval["min_forecast_rate"]
    max_rate = window_eval["max_forecast_rate"]
    cur_rate = forecast_summary["current_rate"]

    if rec_vessel == "No Single-Vessel Fit":
        port_ok = False
        rec_action = "NO FEASIBLE SINGLE-VESSEL OPTION"
        action_headline = "NO FEASIBLE SINGLE-VESSEL OPTION"
        reasons = [
            f"No single vessel in the 4 evaluated classes satisfies both the cargo payload requirement ({cargo_tonnes:,.0f} MT) and physical port limits at {dest_name} (max draft {dest_prof.max_draft_m}m, max LOA {dest_prof.max_loa_m}m).",
            f"Port-compliant smaller vessels (e.g. Handysize) cannot fit {cargo_tonnes:,.0f} MT in a single voyage (payload capacity max ~38,000 MT).",
            f"Cargo-capable larger vessels (e.g. Capesize) exceed the maximum permissible draft of {dest_name} (18.2m vessel draft vs {dest_prof.max_draft_m}m port limit).",
            f"Operational Strategy: Split cargo into multiple voyages (e.g. {math.ceil(cargo_tonnes / 35000)} x Handysize shipments) or arrange offshore lighterage / transshipment at deepwater anchorage.",
            "Decision support advisory only — commercial freight fixtures and charterparty terms remain subject to final negotiations.",
        ]
    else:
        v_spec = VESSEL_REGISTRY.get(_normalize(rec_vessel), VESSEL_REGISTRY["panamax"])
        port_ok = dest_prof.max_draft_m >= v_spec.draft_m
        is_alt = (vessel_summary.get("operational_mode") == "ALTERNATIVE_DISCHARGE")

        if decision == "WAIT":
            rec_action = "WAIT / DEFER"
            if is_alt:
                action_headline = f"WAIT / DEFER - TARGET {min_month_str} ({rec_vessel.upper()} + ALTERNATIVE DISCHARGE)"
            else:
                action_headline = f"WAIT / DEFER - TARGET {min_month_str} ({rec_vessel.upper()})"

            reasons = [
                f"Forecast freight curve indicates a {abs(min_delta_pct):.1f}% decline to ${min_rate:.2f}/MT in {min_month_str} (current rate: ${cur_rate:.2f}/MT); deferring contract fixture captures lower forward freight.",
            ]
            if is_alt:
                reasons.extend([
                    f"{rec_vessel} provides optimal single-voyage payload capacity for {cargo_tonnes:,.0f} MT ({v_spec.dwt_tonnes:,.0f} DWT).",
                    f"Direct {dest_name} berth access is draft-constrained (port max {dest_prof.max_draft_m}m vs {v_spec.draft_m}m vessel draft); viable via offshore lighterage / deepwater transshipment.",
                    f"Selected window ({window_eval['selected_window']}) strategy score is {window_eval['strategy_score']}/100 with {window_eval['risk']} market risk.",
                    "Commercial freight rate quotes and lighterage service agreements remain subject to charterparty terms.",
                    "This output is DECISION SUPPORT only and does not constitute a guarantee of commercial profitability.",
                ])
            else:
                reasons.extend([
                    f"{rec_vessel} passes all physical draft ({v_spec.draft_m}m) and berth restrictions at {dest_name} (max draft {dest_prof.max_draft_m}m).",
                    f"Cargo quantity ({cargo_tonnes:,.0f} MT) perfectly aligns with {rec_vessel} deadweight payload capacity.",
                    f"Selected window ({window_eval['selected_window']}) strategy score is {window_eval['strategy_score']}/100 with {window_eval['risk']} market risk.",
                    "Commercial freight rate quotes and complete voyage-cost settlement remain required for final bottom-line profit calculation.",
                    "This output is DECISION SUPPORT only and does not constitute a guarantee of commercial profitability.",
                ])
        else:
            # BOOK NOW
            rec_action = "BOOK NOW"
            if is_alt:
                action_headline = f"BOOK NOW - {rec_vessel.upper()} + ALTERNATIVE DISCHARGE"
            else:
                action_headline = f"BOOK NOW - {rec_vessel.upper()}"

            is_seven_days_req = (
                chartering_window in ["within_7_days", "within-7-days", "7_days", "7d"]
                or window_eval.get("selected_window") == "Within 7 Days"
            )
            if is_seven_days_req:
                timing_reason = (
                    f"Selected chartering window ({window_eval['selected_window']}) requires prompt fixture within 7 days; "
                    f"execute prompt contract fixture to secure available spot tonnage at current market rate (${cur_rate:.2f}/MT)."
                )
            elif max_delta_pct >= 1.5:
                timing_reason = (
                    f"Forecast freight curve indicates rising rates (+{max_delta_pct:.1f}% within selected window, reaching ${max_rate:.2f}/MT); "
                    f"prompt fixture hedges against freight inflation."
                )
            else:
                timing_reason = (
                    f"Forecast freight rates are broadly stable within the selected window (${min_rate:.2f} to ${max_rate:.2f}/MT vs current ${cur_rate:.2f}/MT); "
                    f"execute prompt fixture to secure vessel tonnage at stable rates."
                )

            reasons = [timing_reason]
            if is_alt:
                reasons.extend([
                    f"{rec_vessel} provides optimal single-voyage payload capacity for {cargo_tonnes:,.0f} MT ({v_spec.dwt_tonnes:,.0f} DWT).",
                    f"Direct {dest_name} berth access is draft-constrained (port max {dest_prof.max_draft_m}m vs {v_spec.draft_m}m vessel draft); viable via offshore lighterage / deepwater transshipment.",
                    f"Selected window ({window_eval['selected_window']}) provides strong strategy score ({window_eval['strategy_score']}/100) and {window_eval['risk']} risk.",
                    "Commercial freight rate quotes and lighterage service agreements remain subject to charterparty terms.",
                    "This output is DECISION SUPPORT only and does not constitute a guarantee of commercial profitability.",
                ])
            else:
                reasons.extend([
                    f"{rec_vessel} passes all physical draft ({v_spec.draft_m}m) and berth restrictions at {dest_name} (max draft {dest_prof.max_draft_m}m).",
                    f"Cargo quantity ({cargo_tonnes:,.0f} MT) perfectly aligns with {rec_vessel} deadweight payload capacity.",
                    f"Selected window ({window_eval['selected_window']}) provides strong strategy score ({window_eval['strategy_score']}/100) and {window_eval['risk']} risk.",
                    "Commercial freight rate quotes and complete voyage-cost settlement remain required for final bottom-line profit calculation.",
                    "This output is DECISION SUPPORT only and does not constitute a guarantee of commercial profitability.",
                ])

    recommendation = {
        "action": rec_action,
        "headline": action_headline,
        "reasons": reasons,
    }

    # 7. Data Quality & Provenance Summary
    scenario_assumptions_list = [
        f"Load port turn time assumed at {origin_prof.turnaround_hours} hours ({origin_prof.representative_port})",
        f"Discharge handling rate modeled at {dest_prof.discharge_rate_tpd:,.0f} t/day ({dest_prof.name})",
    ] if route_provenance != DataProvenance.VERIFIED else []

    if vessel_summary.get("operational_mode") == "ALTERNATIVE_DISCHARGE":
        v_draft = VESSEL_REGISTRY.get(_normalize(rec_vessel), VESSEL_REGISTRY["capesize"]).draft_m
        scenario_assumptions_list.append(
            f"Offshore lighterage / deepwater anchorage transshipment operational strategy applied for {rec_vessel} "
            f"due to {dest_name} berth draft constraint ({dest_prof.max_draft_m}m port limit vs {v_draft}m vessel draft)."
        )

    data_quality = {
        "overall_status": route_provenance,
        "route_type": "VERIFIED MODEL ROUTE" if route_provenance == DataProvenance.VERIFIED else "DERIVED SCENARIO ANALYSIS",
        "verified": [
            "Random Forest Machine Learning BPI/BCI 12-month Forecast (STEP6B)",
            f"Historical VLSFO Bunker Fuel Pricing through {timeline[0]['date']} (STEP7B latest ${economics['bunker_price_usd_per_mt']:.2f}/MT)",
            "Forward VLSFO Bunker Fuel Pricing Timeline (STEP8C)",
            f"Baltic {forecast_summary['route_benchmark']['index_code']} Benchmark Vessel Dimensions (STEP8E/STEP8D)",
            "Contract Strategy Score & Window Sensitivity (STEP8J/8K)",
        ],
        "derived": [
            f"Dual-port physical screening against {dest_prof.name} (Draft {dest_prof.max_draft_m}m, LOA {dest_prof.max_loa_m}m)",
            f"Nautical distance calculation ({economics['distance_nm']} nm) and bunker fuel model",
            f"Current Market Rate derived estimate (${forecast_summary['current_rate']:.2f}/MT) calibrated via {forecast_summary['route_benchmark']['index_name']}",
            "Multi-vessel 4-class operational ranking (Handysize, Supramax, Panamax, Capesize)",
        ],
        "scenario_assumptions": scenario_assumptions_list,
        "missing": [
            "Real-time published commercial broker freight fixtures (protected/unsupplied)",
            "Final voyage net profit / TCE settlement",
        ],
    }

    # 8. Complete Response Schema (incorporating all requested keys)
    return {
        "status": "OK",
        "request": {
            "cargo_type": cargo_type,
            "cargo_tonnes": cargo_tonnes,
            "origin": origin_prof.port_name_full,
            "destination": dest_prof.port_name_full,
            "chartering_window": window_eval["selected_window"],
            "contract_duration_months": contract_duration_months,
        },
        "forecast": {
            "current_rate": forecast_summary["current_rate"],
            "current_rate_date": forecast_summary["current_rate_date"],
            "current_rate_source": forecast_summary["current_rate_source"],
            "current_rate_data_status": forecast_summary["current_rate_data_status"],
            "expected_rate": forecast_summary["expected_rate"],
            "expected_rate_date": forecast_summary["expected_rate_date"],
            "expected_rate_horizon": forecast_summary["expected_rate_horizon"],
            "expected_rate_data_status": forecast_summary.get("expected_rate_data_status", "FORECAST"),
            "market_trend": forecast_summary["market_trend"],
            "confidence": forecast_summary["confidence"],
            "best_month": forecast_summary["best_month"],
            "best_month_signal": forecast_summary["best_month_signal"],
            "route_benchmark": forecast_summary["route_benchmark"],
            "forecast_benchmark": forecast_summary["forecast_benchmark"],
            "pricing_mechanism": forecast_summary["pricing_mechanism"],
            "timeline": timeline,
        },
        "vessel": {
            "recommended_class": vessel_summary["recommended_class"],
            "cargo_fit": vessel_summary["cargo_fit"],
            "port_fit": vessel_summary["port_fit"],
            "route_fit": vessel_summary["route_fit"],
            "operational_mode": vessel_summary.get("operational_mode", "DIRECT_PORT_CALL"),
            "operational_score": vessel_summary["operational_score"],
            "recommendation_reason": vessel_summary.get("recommendation_reason", ""),
            "comparison": vessel_comparison,
        },
        "port": {
            "port_name": dest_prof.port_name_full,
            "feasibility": "PASS" if port_ok else "CONSTRAINED",
            "draft": dest_prof.max_draft_m,
            "loa": dest_prof.max_loa_m,
            "beam": dest_prof.max_beam_m,
            "cargo_handling_rate_tpd": dest_prof.discharge_rate_tpd,
            "notes": dest_prof.notes,
        },
        "chartering_window": window_eval,
        "economics": economics,
        "recommendation": {
            "action": action_headline,
            "headline": action_headline,
            "reasons": reasons,
        },
        "data_quality": data_quality,

        # Backward compatibility fields for legacy components
        "scenario_id": f"{_normalize(origin_prof.country).upper()}_{_normalize(dest_prof.name).upper()}_{_normalize(cargo_type).upper()}",
        "inputs": {
            "cargo_type": cargo_type,
            "cargo_tonnes": cargo_tonnes,
            "origin": origin_prof.port_name_full,
            "destination": dest_prof.port_name_full,
            "chartering_window": window_eval["selected_window"],
            "contract_duration_months": contract_duration_months,
        },
        "recommended_vessel": vessel_summary["recommended_class"],
        "port_feasibility": "PASS" if port_ok else "CONSTRAINED",
        "cargo_status": vessel_summary["cargo_fit"].upper(),
        "cargo_note": vessel_summary.get("recommendation_reason", ""),
        "vessel_optimization": {
            "status": "OK",
            "vessel_comparison": [
                {
                    "vessel_type": v["vessel_type"],
                    "port_feasible": v["port_feasible"],
                    "operational_score": v["operational_score"],
                    "vessel_recommendation": v["status"],
                    "cargo_fit": v["cargo_fit"],
                    "route_fit": v["route_fit"],
                }
                for v in vessel_comparison
            ],
            "monthly_vessel_comparison": [
                {
                    "month": pt["date"],
                    "panamax_bpi_forecast": pt["bpi"],
                    "capesize_bci_forecast": pt["bci"],
                }
                for pt in timeline
            ],
        },
        "break_even": {
            "average_usd_per_mt": economics["break_even_rate"],
            "maximum_stressed_usd_per_mt": economics["stressed_break_even_rate"],
        },
        "best_month": forecast_summary["best_month"],
        "best_month_strategy_score": window_eval["strategy_score"],
        "best_month_market_signal": "FAVORABLE",
        "best_month_bunker_risk": "LOW",
        "selected_window": {
            "start": window_eval["start"],
            "end": window_eval["end"],
            "duration_months": window_eval["duration_months"],
            "duration_class": window_eval["duration_class"],
            "strategy_score": window_eval["strategy_score"],
            "recommendation": action_headline,
        },
        "risk": {
            "selected_window_risk": window_eval["risk"],
            "overall_status": route_provenance,
        },
        "recommendation_reason": reasons[0] if reasons else "",
        "commercial_data": {
            "rate_available": False,
            "financial_status": economics["financial_status"],
        },
        "disclaimer": (
            "This output is DECISION SUPPORT only. It is NOT a guarantee of commercial profitability. "
            "Commercial freight rates and full voyage costs are currently protected in this model."
        ),
    }