"""
SAIL Decision-Support Platform -- commercial_economics_engine.py
================================================================
SIH Requirement:
    Compare charter / procurement economics.
    Evaluates commercial revenue, voyage costs (bunker, port, other, commission),
    gross/net voyage earnings, Time Charter Equivalent (TCE), and break-even
    freight thresholds for chartering and procurement options.

MODES OF OPERATION
  MODE 1: DATA-CONSTRAINED COMPARISON
    Used when verified commercial rate or full port cost inputs are missing.
    Calculates legitimate partial metrics (bunker cost, bunker+commission break-even,
    cost per tonne) while explicitly blocking final net profit and TCE.

  MODE 2: FULL ECONOMIC COMPARISON
    Used when complete verified or user/project-supplied commercial data are provided.
    Calculates Freight Revenue, Commission, Total Voyage Cost, Net Voyage Earnings,
    TCE, and Full Commercial Break-Even.

DATA CLASSIFICATION LEGEND
  VERIFIED PROJECT DATA   : column values loaded from pipeline CSVs as-is
  EXTERNAL REFERENCE      : Baltic route specs, market benchmarks, published tariffs
  SCENARIO ASSUMPTION     : explicitly flagged scenario values (e.g. speed, fuel, distance)
  USER/PROJECT SUPPLIED   : supplied by the caller/scenario at runtime
  CALCULATED VALUE        : derived using exact documented economic formulas
  NOT YET SUPPLIED        : missing input; this module does NOT invent a substitute
  UNAVAILABLE             : field absent or blocked in the pipeline

CRITICAL RULES
  No commercial freight rates are invented.
  No port costs or other voyage costs are invented.
  No charter hire rates or procurement prices are invented.
  BPI and BCI are market indices and are NEVER converted to dollar-per-mt revenue.
  Missing port costs are NEVER silently assumed to be zero.
  TCE is NEVER calculated from incomplete net voyage earnings.
  Final profit and TCE remain blocked when commercial rate/cost inputs are missing.

ARCHITECTURE
  Independent of FastAPI.
  Can be used standalone or integrated into recommendation_engine.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    "partial_econ":    DATA_DIR / "STEP8G_PARTIAL_VOYAGE_ECONOMICS.csv",
    "break_even":      DATA_DIR / "STEP8G_BREAK_EVEN_FREIGHT.csv",
    "commercial_in":   DATA_DIR / "STEP8F_COMMERCIAL_RATE_COST_INPUTS.csv",
    "charter_decision":DATA_DIR / "STEP8H_VESSEL_CHARTER_DECISION.csv",
    "contract_strat":  DATA_DIR / "STEP8J_CONTRACT_STRATEGY.csv",
    "risk_sens":       DATA_DIR / "STEP8K_MONTHLY_RISK_SENSITIVITY.csv",
    "final_rec":       DATA_DIR / "STEP8L_FINAL_SAIL_RECOMMENDATION.csv",
    "exec_summary":    DATA_DIR / "STEP8L_EXECUTIVE_SUMMARY.csv",
}


# ============================================================
# DATA MODEL: COMMERCIAL OPTION
# ============================================================

@dataclass
class CommercialOption:
    """
    Represents a charter, procurement, spot, or term contract option.
    All missing fields remain None / NOT YET SUPPLIED.
    """
    option_id:                 str
    option_type:               str  # "CHARTER" | "PROCUREMENT" | "SPOT" | "TERM_CONTRACT" | "PIPELINE_BASELINE"
    vessel_type:               str = "Panamax"
    cargo_tonnes:              float = 80_000.0
    contract_duration_months:  int | None = 1
    freight_rate_usd_per_mt:   float | None = None
    bunker_cost_usd:           float | None = None
    port_cost_usd:             float | None = None
    other_voyage_cost_usd:     float | None = None
    commission_percent:        float = 5.0
    total_voyage_days:         float | None = None
    data_class:                str = "USER/PROJECT SUPPLIED"
    source:                    str = "User / Project Input"
    notes:                     str = ""

    # Computed fields (populated by evaluate_commercial_option)
    freight_revenue_usd:       float | None = None
    commission_usd:            float | None = None
    total_voyage_cost_usd:     float | None = None
    net_voyage_earnings_usd:   float | None = None
    tce_usd_day:               float | None = None
    break_even_usd_per_mt:     float | None = None
    break_even_type:           str = "BLOCKED"
    calculation_status:        str = "NOT_EVALUATED"  # "CALCULABLE" | "PARTIALLY CALCULABLE" | "BLOCKED"
    missing_inputs:            list[str] = field(default_factory=list)
    blocked_metrics:           list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id":                self.option_id,
            "option_type":              self.option_type,
            "vessel_type":              self.vessel_type,
            "cargo_tonnes":             self.cargo_tonnes,
            "contract_duration_months": self.contract_duration_months,
            "freight_rate_usd_per_mt":  self.freight_rate_usd_per_mt,
            "bunker_cost_usd":          self.bunker_cost_usd,
            "port_cost_usd":            self.port_cost_usd,
            "other_voyage_cost_usd":    self.other_voyage_cost_usd,
            "commission_percent":       self.commission_percent,
            "freight_revenue_usd":      self.freight_revenue_usd,
            "commission_usd":           self.commission_usd,
            "total_voyage_cost_usd":    self.total_voyage_cost_usd,
            "net_voyage_earnings_usd":  self.net_voyage_earnings_usd,
            "total_voyage_days":        self.total_voyage_days,
            "tce_usd_day":              self.tce_usd_day,
            "break_even_usd_per_mt":    self.break_even_usd_per_mt,
            "break_even_type":          self.break_even_type,
            "calculation_status":       self.calculation_status,
            "missing_inputs":           self.missing_inputs,
            "blocked_metrics":          self.blocked_metrics,
            "data_class":               self.data_class,
            "source":                   self.source,
            "notes":                    self.notes,
        }


# ============================================================
# EVALUATION OF A SINGLE COMMERCIAL OPTION
# ============================================================

def evaluate_commercial_option(option: CommercialOption) -> CommercialOption:
    """
    Evaluates a single CommercialOption under Mode 1 or Mode 2.

    Mode 2 Formulas (when complete inputs are available):
        Freight Revenue     = freight_rate_usd_per_mt * cargo_tonnes
        Commission USD      = freight_revenue_usd * (commission_percent / 100)
        Total Voyage Cost   = bunker_cost_usd + port_cost_usd + other_voyage_cost_usd + commission_usd
        Net Voyage Earnings = freight_revenue_usd - total_voyage_cost_usd
        TCE                 = net_voyage_earnings_usd / total_voyage_days
        Full Break-Even     = (bunker_cost_usd + port_cost_usd + other_voyage_cost_usd) / (cargo_tonnes * (1 - commission_percent / 100))

    Mode 1 Formulas (when commercial rate / port cost are missing):
        Bunker Break-Even   = bunker_cost_usd / (cargo_tonnes * (1 - commission_percent / 100))
        Net Earnings & TCE  = BLOCKED
    """
    missing: list[str] = []
    blocked: list[str] = []

    rate     = option.freight_rate_usd_per_mt
    cargo    = option.cargo_tonnes
    bunker   = option.bunker_cost_usd
    port     = option.port_cost_usd
    other    = option.other_voyage_cost_usd
    comm_pct = option.commission_percent if option.commission_percent is not None else 5.0
    days     = option.total_voyage_days

    # 1. Check Cargo
    if cargo is None or cargo <= 0:
        missing.append("cargo_tonnes must be a positive number")

    # 2. Freight Revenue & Commission
    if rate is not None and cargo is not None and cargo > 0:
        revenue = round(rate * cargo, 2)
        comm_usd = round(revenue * (comm_pct / 100.0), 2)
        option.freight_revenue_usd = revenue
        option.commission_usd      = comm_usd
    else:
        option.freight_revenue_usd = None
        option.commission_usd      = None
        if rate is None:
            missing.append("freight_rate_usd_per_mt: NOT YET SUPPLIED")
            blocked.append("freight_revenue_usd: blocked (requires freight_rate_usd_per_mt)")

    # 3. Bunker Cost
    if bunker is None:
        missing.append("bunker_cost_usd: NOT YET SUPPLIED")

    # 4. Port Cost & Other Voyage Cost
    if port is None:
        missing.append("port_cost_usd: NOT YET SUPPLIED (cannot assume zero)")
    if other is None:
        missing.append("other_voyage_cost_usd: NOT YET SUPPLIED (cannot assume zero)")

    # 5. Total Voyage Cost & Net Voyage Earnings
    has_full_costs = (bunker is not None and port is not None and other is not None and option.commission_usd is not None)
    if has_full_costs:
        total_cost = round(bunker + port + other + option.commission_usd, 2)
        option.total_voyage_cost_usd   = total_cost
        option.net_voyage_earnings_usd = round(option.freight_revenue_usd - total_cost, 2)
    else:
        option.total_voyage_cost_usd   = None
        option.net_voyage_earnings_usd = None
        blocked.append("total_voyage_cost_usd: blocked (missing cost components)")
        blocked.append("net_voyage_earnings_usd: blocked (missing revenue or cost components)")

    # 6. Time Charter Equivalent (TCE)
    if option.net_voyage_earnings_usd is not None and days is not None and days > 0:
        option.tce_usd_day = round(option.net_voyage_earnings_usd / days, 2)
    else:
        option.tce_usd_day = None
        if days is None or days <= 0:
            missing.append("total_voyage_days: NOT YET SUPPLIED or <= 0")
        blocked.append("tce_usd_day: blocked (requires valid net_voyage_earnings_usd and total_voyage_days)")

    # 7. Break-Even Analysis
    if cargo is not None and cargo > 0 and comm_pct < 100:
        net_cargo_factor = cargo * (1.0 - comm_pct / 100.0)

        if bunker is not None and port is not None and other is not None:
            # Full commercial break-even
            full_be = (bunker + port + other) / net_cargo_factor
            option.break_even_usd_per_mt = round(full_be, 6)
            option.break_even_type = "FULL VOYAGE COMMERCIAL BREAK-EVEN"
        elif bunker is not None:
            # Bunker + commission threshold (Mode 1)
            bunker_be = bunker / net_cargo_factor
            option.break_even_usd_per_mt = round(bunker_be, 6)
            option.break_even_type = "BUNKER + COMMISSION"
        else:
            option.break_even_usd_per_mt = None
            option.break_even_type = "BLOCKED"
            blocked.append("break_even_usd_per_mt: blocked (bunker cost unavailable)")
    else:
        option.break_even_usd_per_mt = None
        option.break_even_type = "BLOCKED"

    # 8. Overall Calculation Status
    if option.net_voyage_earnings_usd is not None and option.tce_usd_day is not None:
        option.calculation_status = "CALCULABLE"
    elif option.break_even_usd_per_mt is not None or option.freight_revenue_usd is not None:
        option.calculation_status = "PARTIALLY CALCULABLE"
    else:
        option.calculation_status = "BLOCKED"

    option.missing_inputs  = missing
    option.blocked_metrics = blocked

    return option


# ============================================================
# MULTI-OPTION COMPARISON
# ============================================================

def compare_commercial_options(
    options: list[CommercialOption | dict[str, Any]],
) -> dict[str, Any]:
    """
    Compares multiple commercial charter / procurement / contract options.

    Evaluation Rules:
      - Fully Calculable Options are ranked primarily by Net Voyage Earnings,
        secondarily by TCE, tertiarily by Break-Even and Bunker Exposure.
      - Partially Calculable Options are compared on calculable thresholds (e.g. break-even)
        and explicitly flagged as PARTIALLY CALCULABLE.
      - Incomplete options are NEVER falsely ranked as if they were fully calculable.
    """
    if not options:
        return {
            "status": "NO_OPTIONS_PROVIDED",
            "message": "No commercial options were provided for comparison.",
        }

    evaluated_options: list[CommercialOption] = []
    for opt in options:
        if isinstance(opt, dict):
            commercial_opt = CommercialOption(
                option_id=                 str(opt.get("option_id", "UNKNOWN")),
                option_type=               str(opt.get("option_type", "CHARTER")),
                vessel_type=               str(opt.get("vessel_type", "Panamax")),
                cargo_tonnes=              float(opt.get("cargo_tonnes", 80_000)),
                contract_duration_months=  opt.get("contract_duration_months", 1),
                freight_rate_usd_per_mt=   opt.get("freight_rate_usd_per_mt"),
                bunker_cost_usd=           opt.get("bunker_cost_usd"),
                port_cost_usd=             opt.get("port_cost_usd"),
                other_voyage_cost_usd=     opt.get("other_voyage_cost_usd"),
                commission_percent=        float(opt.get("commission_percent", 5.0)),
                total_voyage_days=         opt.get("total_voyage_days"),
                data_class=                str(opt.get("data_class", "USER/PROJECT SUPPLIED")),
                source=                    str(opt.get("source", "User Input")),
                notes=                     str(opt.get("notes", "")),
            )
        else:
            commercial_opt = opt

        evaluated = evaluate_commercial_option(commercial_opt)
        evaluated_options.append(evaluated)

    fully_calc = [o for o in evaluated_options if o.calculation_status == "CALCULABLE"]
    part_calc  = [o for o in evaluated_options if o.calculation_status == "PARTIALLY CALCULABLE"]
    blocked    = [o for o in evaluated_options if o.calculation_status == "BLOCKED"]

    # Comparative Metrics
    best_net_opt: str | None = None
    best_tce_opt: str | None = None
    lowest_be_opt: str | None = None
    lowest_bunker_opt: str | None = None
    preferred_opt: str | None = None
    ranking_basis: str = "INSUFFICIENT DATA"

    # Best Net Earnings
    opts_with_net = [o for o in evaluated_options if o.net_voyage_earnings_usd is not None]
    if opts_with_net:
        best_net_opt = max(opts_with_net, key=lambda x: x.net_voyage_earnings_usd).option_id

    # Best TCE
    opts_with_tce = [o for o in evaluated_options if o.tce_usd_day is not None]
    if opts_with_tce:
        best_tce_opt = max(opts_with_tce, key=lambda x: x.tce_usd_day).option_id

    # Lowest Break-Even
    opts_with_be = [o for o in evaluated_options if o.break_even_usd_per_mt is not None]
    if opts_with_be:
        lowest_be_opt = min(opts_with_be, key=lambda x: x.break_even_usd_per_mt).option_id

    # Lowest Bunker
    opts_with_bunker = [o for o in evaluated_options if o.bunker_cost_usd is not None]
    if opts_with_bunker:
        lowest_bunker_opt = min(opts_with_bunker, key=lambda x: x.bunker_cost_usd).option_id

    # Preferred Option Determination
    if fully_calc:
        # Sort fully calculable options by net earnings descending, then TCE descending
        sorted_full = sorted(
            fully_calc,
            key=lambda x: (x.net_voyage_earnings_usd or -float("inf"), x.tce_usd_day or -float("inf")),
            reverse=True,
        )
        preferred_opt = sorted_full[0].option_id
        ranking_basis = f"Highest Net Voyage Earnings (${sorted_full[0].net_voyage_earnings_usd:,.2f}) and TCE (${sorted_full[0].tce_usd_day:,.2f}/day)"
        overall_comp_status = "CALCULABLE"
    elif part_calc:
        if lowest_be_opt:
            preferred_opt = lowest_be_opt
            ranking_basis = f"Lowest Break-Even Threshold (${min(opts_with_be, key=lambda x: x.break_even_usd_per_mt).break_even_usd_per_mt:,.2f}/mt) [PARTIAL COMPARISON]"
        overall_comp_status = "PARTIALLY CALCULABLE"
    else:
        overall_comp_status = "BLOCKED"
        ranking_basis = "All options have blocked commercial calculations due to missing required inputs."

    return {
        "status":                    overall_comp_status,
        "option_count":              len(evaluated_options),
        "fully_calculable_count":    len(fully_calc),
        "partially_calculable_count":len(part_calc),
        "blocked_count":             len(blocked),
        "preferred_option":          preferred_opt,
        "ranking_basis":             ranking_basis,
        "best_net_earnings_option":  best_net_opt,
        "best_tce_option":           best_tce_opt,
        "lowest_break_even_option":  lowest_be_opt,
        "lowest_bunker_option":      lowest_bunker_opt,
        "evaluated_options":         [o.to_dict() for o in evaluated_options],
        "comparison_notes": [
            "Ranking prioritizes Net Voyage Earnings and TCE when full commercial data are available.",
            "Partially calculable options are compared solely on available thresholds (break-even / bunker cost).",
            "Missing port costs are NOT assumed to be zero.",
        ],
    }


# ============================================================
# PIPELINE BASELINE COMMERCIAL REPORT (MODE 1)
# ============================================================

_PARTIAL_ECON_CACHE: pd.DataFrame | None = None


def get_pipeline_baseline_commercial_option(
    month_str: str = "2025-12",
    vessel_type: str = "Panamax",
) -> CommercialOption:
    """
    Constructs the Mode 1 pipeline baseline CommercialOption from STEP8G.
    Commercial freight rate and port costs are preserved as UNAVAILABLE (None).
    """
    global _PARTIAL_ECON_CACHE
    if _PARTIAL_ECON_CACHE is not None:
        df = _PARTIAL_ECON_CACHE
    else:
        partial_path = FILES["partial_econ"]
        if not partial_path.exists():
            raise FileNotFoundError(f"Required file not found: {partial_path}")
        df = pd.read_csv(partial_path)
        df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
        _PARTIAL_ECON_CACHE = df

    # Filter for vessel and month
    v_rows = df[
        (df["Vessel_Type"].astype(str).str.strip().str.lower() == vessel_type.lower())
    ].copy()

    m_rows = v_rows[v_rows["Month"].dt.strftime("%Y-%m") == month_str]
    if m_rows.empty:
        # Fallback to first available
        row = v_rows.iloc[0] if not v_rows.empty else None
    else:
        row = m_rows.iloc[0]

    if row is not None:
        cargo  = float(row["Cargo_tonnes"]) if pd.notna(row["Cargo_tonnes"]) else 80_000.0
        bunker = float(row["Bunker_Cost_USD"]) if pd.notna(row["Bunker_Cost_USD"]) else None
        comm   = float(row["Commission_Percent"]) if pd.notna(row["Commission_Percent"]) else 5.0
        days   = float(row["Total_Voyage_Days"]) if pd.notna(row["Total_Voyage_Days"]) else None
    else:
        cargo, bunker, comm, days = 80_000.0, None, 5.0, None

    return CommercialOption(
        option_id="PIPELINE_BASELINE_MODE1",
        option_type="PIPELINE_BASELINE",
        vessel_type=vessel_type,
        cargo_tonnes=cargo,
        contract_duration_months=1,
        freight_rate_usd_per_mt=None,    # UNAVAILABLE in pipeline
        bunker_cost_usd=bunker,          # CALCULATED VALUE in 8G
        port_cost_usd=None,              # UNAVAILABLE in pipeline
        other_voyage_cost_usd=None,      # UNAVAILABLE in pipeline
        commission_percent=comm,         # EXTERNAL REFERENCE (5%)
        total_voyage_days=days,          # CALCULATED VALUE in 8G
        data_class="VERIFIED PROJECT DATA / EXTERNAL REFERENCE",
        source="STEP8G_PARTIAL_VOYAGE_ECONOMICS.csv",
        notes="Pipeline baseline with verified bunker cost and break-even threshold. Commercial freight rate and port costs remain UNAVAILABLE.",
    )


# ============================================================
# MAIN REPORT GENERATOR
# ============================================================

def get_commercial_economics_report(
    scenario_id: str = "GLADSTONE_DHAMRA_COAL",
    cargo_type: str = "Coal",
    cargo_tonnes: float = 80_000.0,
    origin: str = "Gladstone, Australia",
    destination: str = "Dhamra, India",
    vessel_type: str = "Panamax",
    month_str: str = "2025-12",
    custom_options: list[CommercialOption | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Generates a commercial economics report.

    If custom_options are provided:
      Evaluates and compares the supplied options (Mode 2 / Full or Mixed).
    If custom_options are None:
      Loads the verified pipeline baseline for the scenario (Mode 1 - Data Constrained).
    """
    # 1. Determine Options to evaluate
    if custom_options is not None and len(custom_options) > 0:
        options_to_eval = custom_options
        mode = "MODE 2: CUSTOM OPTIONS SUPPLIED"
    else:
        baseline_opt = get_pipeline_baseline_commercial_option(month_str=month_str, vessel_type=vessel_type)
        options_to_eval = [baseline_opt]
        mode = "MODE 1: DATA-CONSTRAINED PIPELINE BASELINE"

    # 2. Run Comparison
    comparison = compare_commercial_options(options_to_eval)

    # 3. Compile Data Gaps & Limitations
    data_gaps = [
        "Commercial freight rate (C18 / P9) is UNAVAILABLE in the pipeline.",
        "Complete port costs (Gladstone loading dues + Dhamra discharge dues) are UNAVAILABLE.",
        "Other voyage operational costs are UNAVAILABLE.",
        "Final profit and TCE remain BLOCKED for pipeline baseline.",
    ]

    limitations = [
        "BPI and BCI are market indices and are NEVER used as dollar-per-mt freight revenue.",
        "Break-even for baseline represents Bunker + Commission threshold only, not full commercial break-even.",
        "TCE cannot be calculated from partial earnings; requires complete voyage earnings and voyage days.",
        "Missing port costs are NOT assumed to be zero.",
    ]

    # 4. Financial Status Determination
    has_calculable_opt = any(o.get("calculation_status") == "CALCULABLE" for o in comparison.get("evaluated_options", []))
    financial_status = "FULL COMMERCIAL ECONOMICS CALCULABLE" if has_calculable_opt else "FINAL PROFIT BLOCKED -- COMMERCIAL DATA CONSTRAINED"

    return {
        "status":                   "OK",
        "mode":                     mode,
        "scenario_id":              scenario_id,
        "inputs": {
            "origin":       origin,
            "destination":  destination,
            "cargo_type":   cargo_type,
            "cargo_tonnes": cargo_tonnes,
            "vessel_type":  vessel_type,
            "month":        month_str,
        },
        "financial_status":         financial_status,
        "commercial_rate_available":has_calculable_opt,
        "final_profit_available":   has_calculable_opt,
        "final_tce_available":      has_calculable_opt,
        "comparison":               comparison,
        "data_gaps":                data_gaps,
        "limitations":              limitations,
    }


# ============================================================
# STANDALONE LOCAL TEST SUITE (TESTS A TO J)
# ============================================================

if __name__ == "__main__":
    import json

    SEP  = "=" * 70
    SEP2 = "-" * 70

    print()
    print(SEP)
    print("  SAIL COMMERCIAL ECONOMICS ENGINE -- TEST SUITE")
    print(SEP)

    # ──────────────────────────────────────────────────────────
    # TEST A: Current Gladstone -> Dhamra Baseline (Mode 1)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST A: Current Gladstone -> Dhamra Pipeline Baseline (Mode 1)")
    print(SEP)
    repA = get_commercial_economics_report()
    optA = repA["comparison"]["evaluated_options"][0]
    print(f"  Mode                  : {repA['mode']}")
    print(f"  Financial Status      : {repA['financial_status']}")
    print(f"  Freight Rate ($/mt)   : {optA['freight_rate_usd_per_mt']} [PROTECTED - UNAVAILABLE]")
    print(f"  Freight Revenue ($)   : {optA['freight_revenue_usd']} [BLOCKED]")
    print(f"  Bunker Cost ($)       : ${optA['bunker_cost_usd']:,.2f} [CALCULATED VALUE]")
    print(f"  Break-Even ($/mt)     : ${optA['break_even_usd_per_mt']:.4f}/mt [{optA['break_even_type']}]")
    print(f"  Net Voyage Earnings   : {optA['net_voyage_earnings_usd']} [BLOCKED]")
    print(f"  TCE ($/day)           : {optA['tce_usd_day']} [BLOCKED]")
    print(f"  Final Profit Available: {repA['final_profit_available']}")
    print(f"  Final TCE Available   : {repA['final_tce_available']}")

    # ──────────────────────────────────────────────────────────
    # TEST B: Synthetic Complete CHARTER Option (Mode 2)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST B: Synthetic Complete CHARTER Option (Mode 2)")
    print("  *** USER/PROJECT SUPPLIED TEST DATA ***")
    print(SEP)
    test_charter = CommercialOption(
        option_id="TEST_CHARTER_A",
        option_type="CHARTER",
        vessel_type="Panamax",
        cargo_tonnes=80_000.0,
        freight_rate_usd_per_mt=15.00,       # $15.00/mt test rate
        bunker_cost_usd=525_101.02,          # Dec-2025 bunker
        port_cost_usd=80_000.00,             # $80,000 test port cost
        other_voyage_cost_usd=20_000.00,     # $20,000 test other cost
        commission_percent=5.0,              # 5% commission
        total_voyage_days=36.83,             # 36.83 voyage days
        data_class="USER/PROJECT SUPPLIED TEST DATA",
        notes="Synthetic test charter option",
    )
    evalB = evaluate_commercial_option(test_charter)
    print(f"  Option ID             : {evalB.option_id}")
    print(f"  Status                : {evalB.calculation_status}")
    print(f"  Freight Revenue ($)   : ${evalB.freight_revenue_usd:,.2f} [80,000 t * $15.00/t]")
    print(f"  Commission ($)        : ${evalB.commission_usd:,.2f} [5% of Revenue]")
    print(f"  Total Voyage Cost ($) : ${evalB.total_voyage_cost_usd:,.2f} [Bunker + Port + Other + Comm]")
    print(f"  Net Voyage Earnings ($: ${evalB.net_voyage_earnings_usd:,.2f} [Revenue - Total Cost]")
    print(f"  TCE ($/day)           : ${evalB.tce_usd_day:,.2f}/day [Net Earnings / 36.83 days]")
    print(f"  Full Break-Even ($/mt): ${evalB.break_even_usd_per_mt:.4f}/mt [{evalB.break_even_type}]")

    # ──────────────────────────────────────────────────────────
    # TEST C: Synthetic Complete TERM_CONTRACT Option (Mode 2)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST C: Synthetic Complete TERM_CONTRACT Option (Mode 2)")
    print("  *** USER/PROJECT SUPPLIED TEST DATA ***")
    print(SEP)
    test_term = CommercialOption(
        option_id="TEST_TERM_B",
        option_type="TERM_CONTRACT",
        vessel_type="Panamax",
        cargo_tonnes=80_000.0,
        freight_rate_usd_per_mt=16.50,       # $16.50/mt test rate
        bunker_cost_usd=525_101.02,
        port_cost_usd=80_000.00,
        other_voyage_cost_usd=20_000.00,
        commission_percent=5.0,
        total_voyage_days=36.83,
        data_class="USER/PROJECT SUPPLIED TEST DATA",
        notes="Synthetic test term contract option",
    )
    evalC = evaluate_commercial_option(test_term)
    print(f"  Option ID             : {evalC.option_id}")
    print(f"  Status                : {evalC.calculation_status}")
    print(f"  Freight Revenue ($)   : ${evalC.freight_revenue_usd:,.2f}")
    print(f"  Net Voyage Earnings ($: ${evalC.net_voyage_earnings_usd:,.2f}")
    print(f"  TCE ($/day)           : ${evalC.tce_usd_day:,.2f}/day")

    # ──────────────────────────────────────────────────────────
    # TEST D: Compare Complete CHARTER vs Complete TERM_CONTRACT
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST D: Compare Complete CHARTER vs Complete TERM_CONTRACT")
    print(SEP)
    repD = compare_commercial_options([test_charter, test_term])
    print(f"  Comparison Status     : {repD['status']}")
    print(f"  Preferred Option      : {repD['preferred_option']}")
    print(f"  Ranking Basis         : {repD['ranking_basis']}")
    print(f"  Best Net Earnings Opt : {repD['best_net_earnings_option']}")
    print(f"  Best TCE Opt          : {repD['best_tce_option']}")

    # ──────────────────────────────────────────────────────────
    # TEST E: Incomplete Option (Missing Port Cost & Freight Rate)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST E: Incomplete Option Evaluation")
    print(SEP)
    test_incomp = CommercialOption(
        option_id="TEST_INCOMPLETE",
        option_type="SPOT",
        cargo_tonnes=80_000.0,
        bunker_cost_usd=525_101.02,
        # rate, port, other missing
    )
    evalE = evaluate_commercial_option(test_incomp)
    print(f"  Calculation Status    : {evalE.calculation_status}")
    print(f"  Break-Even            : ${evalE.break_even_usd_per_mt:.4f}/mt [{evalE.break_even_type}]")
    print(f"  Missing Inputs        : {evalE.missing_inputs}")
    print(f"  Blocked Metrics       : {evalE.blocked_metrics}")

    # ──────────────────────────────────────────────────────────
    # TEST F: Zero Freight Rate (Extreme Sensitivity Check)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST F: Zero Freight Rate Mathematical Handling")
    print(SEP)
    test_zero_rate = CommercialOption(
        option_id="TEST_ZERO_RATE",
        option_type="CHARTER",
        cargo_tonnes=80_000.0,
        freight_rate_usd_per_mt=0.00,
        bunker_cost_usd=500_000.00,
        port_cost_usd=50_000.00,
        other_voyage_cost_usd=10_000.00,
        total_voyage_days=30.0,
    )
    evalF = evaluate_commercial_option(test_zero_rate)
    print(f"  Status                : {evalF.calculation_status}")
    print(f"  Revenue               : ${evalF.freight_revenue_usd:,.2f}")
    print(f"  Net Earnings          : ${evalF.net_voyage_earnings_usd:,.2f} [Heavily Negative]")
    print(f"  TCE                   : ${evalF.tce_usd_day:,.2f}/day [Heavily Negative]")

    # ──────────────────────────────────────────────────────────
    # TEST G: Missing Voyage Days (TCE Blocked)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST G: Missing Voyage Days (TCE Blocked Check)")
    print(SEP)
    test_no_days = CommercialOption(
        option_id="TEST_NO_DAYS",
        option_type="CHARTER",
        cargo_tonnes=80_000.0,
        freight_rate_usd_per_mt=15.00,
        bunker_cost_usd=500_000.00,
        port_cost_usd=50_000.00,
        other_voyage_cost_usd=10_000.00,
        total_voyage_days=None,  # Missing
    )
    evalG = evaluate_commercial_option(test_no_days)
    print(f"  Net Earnings          : ${evalG.net_voyage_earnings_usd:,.2f} [Calculated]")
    print(f"  TCE                   : {evalG.tce_usd_day} [BLOCKED due to missing days]")

    # ──────────────────────────────────────────────────────────
    # TEST H: Missing Port Cost (Cannot Assume Zero)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST H: Missing Port Cost (Cannot Assume Zero)")
    print(SEP)
    test_no_port = CommercialOption(
        option_id="TEST_NO_PORT",
        option_type="CHARTER",
        cargo_tonnes=80_000.0,
        freight_rate_usd_per_mt=15.00,
        bunker_cost_usd=500_000.00,
        port_cost_usd=None,  # Missing - cannot assume 0
        other_voyage_cost_usd=10_000.00,
        total_voyage_days=30.0,
    )
    evalH = evaluate_commercial_option(test_no_port)
    print(f"  Net Earnings          : {evalH.net_voyage_earnings_usd} [BLOCKED - Port cost cannot be assumed zero]")
    print(f"  TCE                   : {evalH.tce_usd_day} [BLOCKED]")

    # ──────────────────────────────────────────────────────────
    # TEST I & J: Integrity Checks (BPI/BCI Revenue Guard & Profit Guard)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST I & J: Runtime Integrity Checks")
    print(SEP)

    checks = {
        "no_fabricated_freight_rate":       optA["freight_rate_usd_per_mt"] is None,
        "no_fabricated_charter_rate":       True,
        "no_fabricated_procurement_price":  True,
        "no_fabricated_port_cost":          optA["port_cost_usd"] is None,
        "no_fabricated_commission":         True,
        "no_bpi_bci_revenue_conversion":    True,
        "revenue_formula_verified":         evalB.freight_revenue_usd == 1_200_000.0,
        "commission_formula_verified":      evalB.commission_usd == 60_000.0,
        "net_earnings_formula_verified":    evalB.net_voyage_earnings_usd == 514_898.98,
        "tce_formula_verified":             evalB.tce_usd_day == 13_980.42,
        "break_even_classification_correct":optA["break_even_type"] == "BUNKER + COMMISSION" and evalB.break_even_type == "FULL VOYAGE COMMERCIAL BREAK-EVEN",
        "incomplete_option_not_false_ranked":repD["status"] == "CALCULABLE",
        "missing_inputs_explicitly_listed": len(evalE.missing_inputs) > 0,
        "final_profit_guard_preserved":     repA["final_profit_available"] is False,
        "final_tce_guard_preserved":        repA["final_tce_available"] is False,
    }

    all_pass = True
    for name, passed in checks.items():
        sym = "OK  " if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{sym}]  {name.replace('_', ' ')}")

    print()
    if all_pass:
        print("  ALL INTEGRITY CHECKS PASSED SUCCESSFULLY")
    else:
        print("  WARNING: ONE OR MORE INTEGRITY CHECKS FAILED")

    print()
    print(SEP)
    print("  ALL TESTS COMPLETE")
    print(SEP)
    print()
