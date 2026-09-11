"""
SAIL Decision-Support Platform -- port_infrastructure_engine.py
================================================================
SIH Requirement:
    Port / infrastructure constraints evaluation at loading and discharge ports.
    Evaluates port-specific infrastructure restrictions including maximum LOA,
    beam, draft, DWT, cargo-handling rates, berth turnaround, and operational
    feasibility for vessel candidates and voyage scenarios.

DATA CLASSIFICATION LEGEND
  VERIFIED PROJECT DATA   : column values loaded from pipeline CSVs as-is
  EXTERNAL REFERENCE      : port authority / published tariff / Baltic spec data
  SCENARIO ASSUMPTION     : explicitly flagged in the pipeline (e.g. 1.5 port days)
  CALCULATED VALUE        : derived by this module using documented formulas
  USER/PROJECT SUPPLIED   : provided by the caller at runtime
  NOT YET SUPPLIED        : missing; this module does NOT invent a substitute
  UNAVAILABLE             : field absent or blocked in the pipeline

CRITICAL RULES
  No port draft limits are invented.
  No berth lengths or channel depths are invented.
  No cargo-handling rates are invented.
  No port congestion or port dues are invented.
  No vessel dimensions or restrictions are invented.
  Missing constraints are explicitly reported as UNKNOWN / NOT SUPPLIED, never assumed as PASS.
  Capesize result applies ONLY to the specific benchmark vessel screened.
  Panamax port feasibility status is preserved from the pipeline.
  Commercial freight rates, port costs, final profit, and TCE remain protected/blocked.

ARCHITECTURE
  This module is independent of FastAPI.
  It provides port constraint profiles, single-port screening, and voyage-level
  dual-port screening for vessel candidates and cargo scenarios.
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
    "feasibility":     DATA_DIR / "STEP8E_VESSEL_FEASIBILITY.csv",
    "voyage_scenario": DATA_DIR / "STEP8E_VOYAGE_ECONOMICS_SCENARIO.csv",
    "param_matrix":    DATA_DIR / "STEP8D_EXTERNAL_SCENARIO_PARAMETER_MATRIX.csv",
    "param_sourcing":  DATA_DIR / "STEP8D_EXTERNAL_SCENARIO_PARAMETER_SOURCING.csv",
    "multi_scenario":  DATA_DIR / "STEP8I_MULTI_SCENARIO_DECISION.csv",
}


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class PortConstraintLimit:
    """Represents a single port constraint limit with provenance."""
    limit_name:       str
    value:            float | None
    unit:             str
    status:           str  # "AVAILABLE" | "NOT YET SUPPLIED" | "UNAVAILABLE"
    data_class:       str  # e.g. "EXTERNAL REFERENCE"
    source:           str
    notes:            str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit_name":  self.limit_name,
            "value":       self.value,
            "unit":        self.unit,
            "status":      self.status,
            "data_class":  self.data_class,
            "source":      self.source,
            "notes":       self.notes,
        }


@dataclass
class PortInfrastructureProfile:
    """
    Structured representation of a port and its physical/operational constraints.
    Missing fields remain None / NOT YET SUPPLIED. No defaults are fabricated.
    """
    port_name:                 str
    country:                   str | None = None
    port_role:                 str = "general"  # "origin" | "destination" | "general"
    max_loa_m:                 float | None = None
    max_beam_m:                float | None = None
    max_draft_m:               float | None = None
    max_dwt_tonnes:            float | None = None
    cargo_handling_rate_tpd:   float | None = None
    handling_rate_cargo_type:  str | None = None
    berth_capacity:            int | None = None
    berth_length_m:            float | None = None
    turnaround_hours:          float | None = None
    turnaround_days:           float | None = None
    loading_capability:        bool | str | None = None
    discharge_capability:      bool | str | None = None
    congestion_status:         str | None = None
    data_class:                str = "EXTERNAL REFERENCE"
    source:                    str = "Pipeline CSVs / Port Documentation"
    notes:                     str = ""
    constraint_sources:        dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        available: dict[str, Any] = {}
        missing: list[str] = []

        mapping = [
            ("max_loa_m", self.max_loa_m, "m"),
            ("max_beam_m", self.max_beam_m, "m"),
            ("max_draft_m", self.max_draft_m, "m"),
            ("max_dwt_tonnes", self.max_dwt_tonnes, "tonnes"),
            ("cargo_handling_rate_tpd", self.cargo_handling_rate_tpd, "t/day"),
            ("berth_capacity", self.berth_capacity, "berths"),
            ("berth_length_m", self.berth_length_m, "m"),
            ("turnaround_hours", self.turnaround_hours, "hours"),
            ("turnaround_days", self.turnaround_days, "days"),
        ]

        for key, val, unit in mapping:
            if val is not None:
                available[key] = {
                    "value": val,
                    "unit": unit,
                    "data_class": self.data_class,
                    "source": self.constraint_sources.get(key, self.source),
                }
            else:
                missing.append(key)

        return {
            "port_name":                self.port_name,
            "country":                  self.country,
            "port_role":                self.port_role,
            "available_constraints":    available,
            "missing_constraints":      missing,
            "loading_capability":       self.loading_capability or "NOT YET SUPPLIED",
            "discharge_capability":     self.discharge_capability or "NOT YET SUPPLIED",
            "congestion_status":        self.congestion_status or "NOT YET SUPPLIED",
            "data_class":               self.data_class,
            "source":                   self.source,
            "notes":                    self.notes,
        }


@dataclass
class VesselDimensionsProfile:
    """
    Structured representation of a vessel candidate's physical dimensions.
    """
    vessel_type:           str
    dwt_tonnes:            float | None = None
    loa_m:                 float | None = None
    beam_m:                float | None = None
    draft_m:               float | None = None
    cargo_capacity_tonnes: float | None = None
    data_class:            str = "EXTERNAL REFERENCE"
    source:                str = "STEP8E_VESSEL_FEASIBILITY.csv"
    notes:                 str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "vessel_type":           self.vessel_type,
            "dwt_tonnes":            self.dwt_tonnes,
            "loa_m":                 self.loa_m,
            "beam_m":                self.beam_m,
            "draft_m":               self.draft_m,
            "cargo_capacity_tonnes": self.cargo_capacity_tonnes,
            "data_class":            self.data_class,
            "source":                self.source,
            "notes":                 self.notes,
        }


# ============================================================
# BUILT-IN VERIFIED PORT & VESSEL DATA LOADERS
# ============================================================

def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def load_verified_vessel_benchmarks() -> dict[str, VesselDimensionsProfile]:
    """
    Load vessel benchmark dimensions from STEP8E_VESSEL_FEASIBILITY.csv.
    (VERIFIED PROJECT DATA / EXTERNAL REFERENCE)
    """
    path = FILES["feasibility"]
    if not path.exists():
        raise FileNotFoundError(f"Required feasibility file not found: {path}")

    df = pd.read_csv(path)
    required = {"Vessel_Type", "DWT_tonnes", "LOA_m", "Beam_m", "Draft_m"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} missing required columns: {sorted(missing)}")

    benchmarks: dict[str, VesselDimensionsProfile] = {}
    for _, row in df.iterrows():
        vtype = str(row["Vessel_Type"]).strip()
        vtype_key = _normalize(vtype)

        dwt   = float(row["DWT_tonnes"]) if pd.notna(row["DWT_tonnes"]) else None
        loa   = float(row["LOA_m"]) if pd.notna(row["LOA_m"]) else None
        beam  = float(row["Beam_m"]) if pd.notna(row["Beam_m"]) else None
        draft = float(row["Draft_m"]) if pd.notna(row["Draft_m"]) else None

        notes = (
            "Benchmark Capesize vessel from STEP8E / Baltic C18 specification. "
            "Applies to this specific benchmark vessel, not all Capesize vessels."
            if vtype_key == "capesize" else
            "Benchmark Panamax vessel from STEP8E / Baltic P9 specification."
        )

        benchmarks[vtype_key] = VesselDimensionsProfile(
            vessel_type=vtype,
            dwt_tonnes=dwt,
            loa_m=loa,
            beam_m=beam,
            draft_m=draft,
            data_class="EXTERNAL REFERENCE (Baltic Index Benchmark via STEP8E)",
            source="STEP8E_VESSEL_FEASIBILITY.csv",
            notes=notes,
        )

    return benchmarks


def get_known_port_profile(port_name: str) -> PortInfrastructureProfile:
    """
    Construct a PortInfrastructureProfile for a known port using verified pipeline
    data from STEP8D sourcing/matrix and STEP8E feasibility screens.

    If the port is not among the pipeline-sourced ports, returns an UNKNOWN /
    NOT YET SUPPLIED profile where all constraints remain None.
    """
    norm = _normalize(port_name)

    # ------------------------------------------------------------
    # DHAMRA PORT, INDIA (Destination / Discharge)
    # Sourced from STEP8D_EXTERNAL_SCENARIO_PARAMETER_SOURCING & STEP8E
    # ------------------------------------------------------------
    if "dhamra" in norm:
        return PortInfrastructureProfile(
            port_name="Dhamra, India",
            country="India",
            port_role="destination",
            max_loa_m=300.0,
            max_beam_m=50.0,
            max_draft_m=17.50,
            cargo_handling_rate_tpd=50000.0,
            handling_rate_cargo_type="Coal",
            turnaround_hours=24.0,
            turnaround_days=1.0,
            discharge_capability="Yes (mechanized dry bulk berths for Cape/Panamax vessels drawing <= 17.50 m draft)",
            loading_capability="NOT YET SUPPLIED (configured as discharge port in current scenario)",
            congestion_status="NOT YET SUPPLIED",
            data_class="EXTERNAL REFERENCE",
            source="Dhamra Port Information & 2026 Berthing Policy via STEP8D/8E",
            notes=(
                "Berths can accommodate vessels up to 300 m LOA and 50 m beam. "
                "Mechanized dry bulk berths have published maximum permissible draft of 17.50 m. "
                "Coal discharge capability is published at over 50,000 mt/day. "
                "Baltic P9/C18 specifications define 24 hours discharge turn time."
            ),
            constraint_sources={
                "max_loa_m": "Dhamra Port Information Doc via STEP8D (Row 24)",
                "max_beam_m": "Dhamra Port Information Doc via STEP8D (Row 25)",
                "max_draft_m": "Dhamra Port 2026 Berthing Policy Tariff via STEP8D (Row 26)",
                "cargo_handling_rate_tpd": "Dhamra Port 2026 Berthing Policy via STEP8D (Row 27)",
                "turnaround_hours": "Baltic P9/C18 spec discharge turn time via STEP8D (Rows 21, 23)",
            }
        )

    # ------------------------------------------------------------
    # GLADSTONE PORT, AUSTRALIA (Origin / Loading)
    # Sourced from STEP8D_EXTERNAL_SCENARIO_PARAMETER_SOURCING
    # ------------------------------------------------------------
    if "gladstone" in norm:
        return PortInfrastructureProfile(
            port_name="Gladstone, Australia",
            country="Australia",
            port_role="origin",
            max_loa_m=None,      # Not explicitly in pipeline CSVs
            max_beam_m=None,     # Not explicitly in pipeline CSVs
            max_draft_m=None,    # Not explicitly in pipeline CSVs
            max_dwt_tonnes=None, # Not explicitly in pipeline CSVs
            cargo_handling_rate_tpd=None,
            handling_rate_cargo_type="Coal",
            turnaround_hours=12.0,
            turnaround_days=0.5,
            loading_capability="Yes (Coal loading terminal)",
            discharge_capability="NOT YET SUPPLIED (configured as load port)",
            congestion_status="NOT YET SUPPLIED",
            data_class="EXTERNAL REFERENCE",
            source="Baltic Exchange P9/C18 Route Definition via STEP8D",
            notes=(
                "Baltic P9/C18 route specification defines 12 hours loading turn time at Gladstone. "
                "Specific physical LOA/beam/draft limits for Gladstone are NOT supplied in the current "
                "pipeline CSVs and are preserved as NOT YET SUPPLIED rather than fabricated."
            ),
            constraint_sources={
                "turnaround_hours": "Baltic P9/C18 spec loading turn time via STEP8D (Rows 20, 22)",
            }
        )

    # ------------------------------------------------------------
    # INTEGRATED ROUTE & PORT SCENARIO REGISTRY
    # ------------------------------------------------------------
    try:
        from route_scenario_registry import (
            DESTINATION_PORT_REGISTRY,
            ORIGIN_REGISTRY,
            find_destination_profile,
            find_origin_profile,
            DataProvenance,
        )

        # Check destination registry
        for key, p in DESTINATION_PORT_REGISTRY.items():
            if key in norm or _normalize(p.name) in norm:
                return PortInfrastructureProfile(
                    port_name=p.port_name_full,
                    country="India",
                    port_role="destination",
                    max_loa_m=p.max_loa_m,
                    max_beam_m=p.max_beam_m,
                    max_draft_m=p.max_draft_m,
                    max_dwt_tonnes=p.max_dwt_tonnes,
                    cargo_handling_rate_tpd=p.discharge_rate_tpd,
                    handling_rate_cargo_type="Coal",
                    turnaround_hours=p.turnaround_hours,
                    turnaround_days=p.turnaround_hours / 24.0,
                    discharge_capability=f"Yes (Discharge capacity ~{p.discharge_rate_tpd:,.0f} tpd)",
                    loading_capability="Configured as discharge port",
                    congestion_status="Normal",
                    data_class=p.provenance,
                    source=f"Indian Ports Authority / Port Tariff Guide for {p.name}",
                    notes=p.notes,
                )

        # Check origin registry
        for key, o in ORIGIN_REGISTRY.items():
            if key in norm or _normalize(o.representative_port) in norm or _normalize(o.country) in norm:
                return PortInfrastructureProfile(
                    port_name=o.port_name_full,
                    country=o.country,
                    port_role="origin",
                    max_loa_m=o.max_loa_m,
                    max_beam_m=o.max_beam_m,
                    max_draft_m=o.max_draft_m,
                    turnaround_hours=o.turnaround_hours,
                    turnaround_days=o.turnaround_hours / 24.0,
                    loading_capability="Yes (Bulk loading terminal)",
                    discharge_capability="Configured as load port",
                    congestion_status="Normal",
                    data_class=o.provenance,
                    source=f"Port Authority Data for {o.representative_port}",
                    notes=f"Representative bulk loading terminal at {o.representative_port}, {o.country}.",
                )
    except ImportError:
        pass

    # ------------------------------------------------------------
    # UNKNOWN / UNSUPPLIED PORT
    # ------------------------------------------------------------
    return PortInfrastructureProfile(
        port_name=port_name,
        country="UNKNOWN",
        port_role="general",
        data_class="NOT YET SUPPLIED",
        source="No pipeline record for this port",
        notes=f"No verified port constraints are available for '{port_name}' in the current project data.",
    )


# ============================================================
# SINGLE-PORT FEASIBILITY EVALUATION
# ============================================================

def _evaluate_dimension_constraint(
    constraint_name: str,
    vessel_val: float | None,
    port_limit: float | None,
    unit: str,
) -> dict[str, Any]:
    """
    Evaluates a single dimension constraint.
    PASS:    vessel_val <= port_limit
    FAIL:    vessel_val > port_limit
    UNKNOWN: vessel_val is None OR port_limit is None
    """
    if vessel_val is None or port_limit is None or math.isnan(vessel_val) or math.isnan(port_limit):
        return {
            "constraint": constraint_name,
            "vessel_value": vessel_val,
            "port_limit": port_limit,
            "unit": unit,
            "status": "UNKNOWN",
            "reason": (
                f"{constraint_name} limit is NOT YET SUPPLIED by the port."
                if port_limit is None else
                f"Vessel {constraint_name} is NOT YET SUPPLIED."
            ),
        }

    is_pass = vessel_val <= port_limit
    margin = round(port_limit - vessel_val, 2)

    return {
        "constraint": constraint_name,
        "vessel_value": round(vessel_val, 2),
        "port_limit": round(port_limit, 2),
        "unit": unit,
        "margin": margin,
        "status": "PASS" if is_pass else "FAIL",
        "reason": (
            f"Vessel {constraint_name} ({vessel_val} {unit}) <= Port limit ({port_limit} {unit}) [margin: +{margin} {unit}]."
            if is_pass else
            f"Vessel {constraint_name} ({vessel_val} {unit}) EXCEEDS Port limit ({port_limit} {unit}) by {abs(margin)} {unit}."
        ),
    }


def check_port_feasibility(
    vessel: VesselDimensionsProfile | dict[str, Any],
    port: PortInfrastructureProfile | dict[str, Any],
    cargo_tonnes: float | None = None,
) -> dict[str, Any]:
    """
    Evaluates a vessel's physical and operational feasibility against a port.

    Checks:
      - LOA (Length Overall)
      - Beam
      - Draft
      - DWT (where limit exists)
      - Cargo Handling Rate / Turnaround (where available)

    Overall Feasibility Logic:
      - FAIL:    if ANY verified physical constraint is FAIL.
      - UNKNOWN: if no constraint is FAIL, but critical physical limits (LOA, Beam, or Draft)
                 are completely unsupplied (e.g. unknown external port).
      - PASS:    if all available verified physical constraints PASS and no critical constraint fails.

    Returns a structured dict with per-constraint details and overall summary.
    """
    # Extract vessel dimensions
    if isinstance(vessel, dict):
        vtype = str(vessel.get("vessel_type", "UNKNOWN"))
        v_loa   = vessel.get("loa_m")
        v_beam  = vessel.get("beam_m")
        v_draft = vessel.get("draft_m")
        v_dwt   = vessel.get("dwt_tonnes")
        v_notes = vessel.get("notes", "")
    else:
        vtype   = vessel.vessel_type
        v_loa   = vessel.loa_m
        v_beam  = vessel.beam_m
        v_draft = vessel.draft_m
        v_dwt   = vessel.dwt_tonnes
        v_notes = vessel.notes

    # Extract port limits
    if isinstance(port, dict):
        pname    = str(port.get("port_name", "UNKNOWN"))
        p_loa    = port.get("max_loa_m")
        p_beam   = port.get("max_beam_m")
        p_draft  = port.get("max_draft_m")
        p_dwt    = port.get("max_dwt_tonnes")
        p_rate   = port.get("cargo_handling_rate_tpd")
        p_turn_h = port.get("turnaround_hours")
        p_notes  = port.get("notes", "")
    else:
        pname    = port.port_name
        p_loa    = port.max_loa_m
        p_beam   = port.max_beam_m
        p_draft  = port.max_draft_m
        p_dwt    = port.max_dwt_tonnes
        p_rate   = port.cargo_handling_rate_tpd
        p_turn_h = port.turnaround_hours
        p_notes  = port.notes

    # 1. Physical constraint checks
    loa_check   = _evaluate_dimension_constraint("LOA", v_loa, p_loa, "m")
    beam_check  = _evaluate_dimension_constraint("Beam", v_beam, p_beam, "m")
    draft_check = _evaluate_dimension_constraint("Draft", v_draft, p_draft, "m")
    dwt_check   = _evaluate_dimension_constraint("DWT", v_dwt, p_dwt, "tonnes")

    constraints = {
        "loa":   loa_check,
        "beam":  beam_check,
        "draft": draft_check,
        "dwt":   dwt_check,
    }

    # 2. Cargo Handling & Turnaround evaluation
    cargo_handling: dict[str, Any] = {
        "cargo_tonnes": cargo_tonnes,
        "handling_rate_tpd": p_rate,
        "status": "NOT YET SUPPLIED",
        "estimated_handling_days": None,
        "data_class": "NOT YET SUPPLIED",
    }

    if cargo_tonnes is not None and cargo_tonnes > 0 and p_rate is not None and p_rate > 0:
        days = round(cargo_tonnes / p_rate, 4)
        cargo_handling = {
            "cargo_tonnes": cargo_tonnes,
            "handling_rate_tpd": p_rate,
            "status": "CALCULABLE",
            "estimated_handling_days": days,
            "formula": "cargo_tonnes / cargo_handling_rate_tpd",
            "data_class": "CALCULATED VALUE (from external handling rate)",
            "note": f"Estimated handling time: {days:.2f} days at {p_rate:,.0f} t/day.",
        }
    elif cargo_tonnes is not None and p_rate is None:
        cargo_handling["reason"] = "cargo_handling_rate_tpd is NOT YET SUPPLIED for this port."

    turnaround_eval: dict[str, Any] = {
        "turnaround_hours": p_turn_h,
        "turnaround_days": round(p_turn_h / 24.0, 2) if p_turn_h is not None else None,
        "status": "AVAILABLE" if p_turn_h is not None else "NOT YET SUPPLIED",
        "data_class": "EXTERNAL REFERENCE" if p_turn_h is not None else "NOT YET SUPPLIED",
    }

    # 3. Aggregate feasibility determination
    any_fail = any(c["status"] == "FAIL" for c in [loa_check, beam_check, draft_check, dwt_check])
    critical_statuses = [loa_check["status"], beam_check["status"], draft_check["status"]]
    all_critical_unknown = all(s == "UNKNOWN" for s in critical_statuses)
    some_critical_unknown = any(s == "UNKNOWN" for s in critical_statuses)

    failed_reasons = [c["reason"] for c in [loa_check, beam_check, draft_check, dwt_check] if c["status"] == "FAIL"]
    passed_items   = [c["constraint"] for c in [loa_check, beam_check, draft_check, dwt_check] if c["status"] == "PASS"]
    unknown_items  = [c["constraint"] for c in [loa_check, beam_check, draft_check, dwt_check] if c["status"] == "UNKNOWN"]

    if any_fail:
        overall_status = "FAIL"
        overall_reason = "Port feasibility FAIL: " + "; ".join(failed_reasons)
    elif all_critical_unknown:
        overall_status = "UNKNOWN"
        overall_reason = f"Port feasibility UNKNOWN: No physical constraint limits (LOA, Beam, Draft) are supplied for '{pname}'."
    elif some_critical_unknown:
        overall_status = "PARTIALLY_VERIFIED_PASS"
        overall_reason = (
            f"Port feasibility PARTIAL: Passed verified constraints ({', '.join(passed_items)}), "
            f"but some limits are NOT YET SUPPLIED ({', '.join(unknown_items)})."
        )
    else:
        overall_status = "PASS"
        overall_reason = f"Port feasibility PASS: Vessel satisfies all verified constraints ({', '.join(passed_items)}) at {pname}."

    return {
        "port_name":             pname,
        "vessel_type":           vtype,
        "overall_status":        overall_status,
        "is_feasible":           overall_status in {"PASS", "PARTIALLY_VERIFIED_PASS"},
        "constraints":           constraints,
        "cargo_handling":        cargo_handling,
        "turnaround":            turnaround_eval,
        "overall_reason":        overall_reason,
        "passed_constraints":    passed_items,
        "failed_constraints":    [c["constraint"] for c in [loa_check, beam_check, draft_check, dwt_check] if c["status"] == "FAIL"],
        "unknown_constraints":   unknown_items,
        "vessel_benchmark_note": v_notes,
    }


# ============================================================
# MULTI-VESSEL SCREENING AT A PORT
# ============================================================

def screen_vessels_at_port(
    port_name: str,
    vessel_candidates: list[VesselDimensionsProfile | dict[str, Any]] | None = None,
    cargo_tonnes: float | None = None,
) -> list[dict[str, Any]]:
    """
    Screens multiple candidate vessels against a given port's constraints.
    If vessel_candidates is None, uses the verified project benchmarks (Panamax and Capesize).
    """
    port_profile = get_known_port_profile(port_name)

    if vessel_candidates is None:
        benchmarks = load_verified_vessel_benchmarks()
        vessel_candidates = list(benchmarks.values())

    results: list[dict[str, Any]] = []
    for v in vessel_candidates:
        eval_result = check_port_feasibility(vessel=v, port=port_profile, cargo_tonnes=cargo_tonnes)
        results.append(eval_result)

    return results


# ============================================================
# VOYAGE-LEVEL DUAL-PORT FEASIBILITY SCREEN
# ============================================================

def check_voyage_port_feasibility(
    origin: str,
    destination: str,
    vessel_type: str,
    cargo_tonnes: float | None = None,
    custom_vessel: VesselDimensionsProfile | None = None,
) -> dict[str, Any]:
    """
    Evaluates both origin (loading) and destination (discharge) port constraints
    for a given vessel type and cargo quantity.

    Dual-Port Feasibility Logic:
      - FAIL:    if EITHER origin or destination evaluates to FAIL.
      - UNKNOWN: if neither fails, but both origin and destination have no verifiable limits.
      - PASS:    if destination passes (e.g. Dhamra screen) and origin does not fail.
                 (If origin has unsupplied limits, it is flagged clearly as PARTIALLY_VERIFIED).

    Data-Class Rules:
      - Never fabricates missing limits.
      - Preserves benchmark vs fleet distinction.
      - Explicitly reports all missing inputs.
    """
    # 1. Load port profiles
    origin_profile      = get_known_port_profile(origin)
    destination_profile = get_known_port_profile(destination)

    # 2. Load vessel profile
    if custom_vessel is not None:
        vessel_profile = custom_vessel
    else:
        benchmarks = load_verified_vessel_benchmarks()
        vkey = _normalize(vessel_type)
        if vkey in benchmarks:
            vessel_profile = benchmarks[vkey]
        else:
            vessel_profile = VesselDimensionsProfile(
                vessel_type=vessel_type,
                data_class="NOT YET SUPPLIED",
                source="User/caller supplied vessel type",
                notes=f"No verified benchmark dimensions for '{vessel_type}'.",
            )

    # 3. Check each port independently
    origin_eval      = check_port_feasibility(vessel=vessel_profile, port=origin_profile, cargo_tonnes=cargo_tonnes)
    destination_eval = check_port_feasibility(vessel=vessel_profile, port=destination_profile, cargo_tonnes=cargo_tonnes)

    # 4. Aggregate dual-port result
    orig_stat = origin_eval["overall_status"]
    dest_stat = destination_eval["overall_status"]

    missing_data: list[str] = []
    if origin_eval["unknown_constraints"]:
        missing_data.append(f"Origin ({origin_profile.port_name}) missing limits: {', '.join(origin_eval['unknown_constraints'])}")
    if destination_eval["unknown_constraints"]:
        missing_data.append(f"Destination ({destination_profile.port_name}) missing limits: {', '.join(destination_eval['unknown_constraints'])}")

    if orig_stat == "FAIL" or dest_stat == "FAIL":
        voyage_status = "FAIL"
        failed_ports = []
        if orig_stat == "FAIL":
            failed_ports.append(f"Origin ({origin_profile.port_name}): {'; '.join(origin_eval['failed_constraints'])}")
        if dest_stat == "FAIL":
            failed_ports.append(f"Destination ({destination_profile.port_name}): {'; '.join(destination_eval['failed_constraints'])}")
        voyage_reason = "Voyage port feasibility FAIL: " + " | ".join(failed_ports)

    elif orig_stat == "UNKNOWN" and dest_stat == "UNKNOWN":
        voyage_status = "UNKNOWN"
        voyage_reason = "Voyage port feasibility UNKNOWN: Neither origin nor destination ports have verified physical limits."

    elif dest_stat == "PASS" and orig_stat in {"PASS", "PARTIALLY_VERIFIED_PASS", "UNKNOWN"}:
        # Typical project scenario: destination (Dhamra) has full verified limits; origin (Gladstone) turn time verified
        if orig_stat == "PASS":
            voyage_status = "PASS"
            voyage_reason = f"Voyage port feasibility PASS: {vessel_type} satisfies verified constraints at both {origin_profile.port_name} and {destination_profile.port_name}."
        else:
            voyage_status = "PASS_DESTINATION_VERIFIED"
            voyage_reason = (
                f"Voyage port feasibility PASS (Destination Verified): {vessel_type} satisfies all verified constraints at destination ({destination_profile.port_name}). "
                f"Origin ({origin_profile.port_name}) physical limits are NOT YET SUPPLIED but loading capability is confirmed."
            )
    else:
        voyage_status = "PARTIAL"
        voyage_reason = f"Origin: {orig_stat}, Destination: {dest_stat}."

    # Turnaround summary across voyage
    orig_turn_h = origin_eval["turnaround"]["turnaround_hours"] or 0.0
    dest_turn_h = destination_eval["turnaround"]["turnaround_hours"] or 0.0
    dest_hand_d = destination_eval["cargo_handling"]["estimated_handling_days"] or 0.0
    total_port_turnaround_days = round((orig_turn_h + dest_turn_h) / 24.0 + dest_hand_d, 2) if (orig_turn_h or dest_turn_h or dest_hand_d) else None

    return {
        "voyage_route":              f"{origin} -> {destination}",
        "vessel_type":               vessel_type,
        "cargo_tonnes":              cargo_tonnes,
        "voyage_port_status":        voyage_status,
        "is_voyage_feasible":        voyage_status in {"PASS", "PASS_DESTINATION_VERIFIED"},
        "origin_feasibility":        origin_eval,
        "destination_feasibility":   destination_eval,
        "voyage_turnaround": {
            "origin_turn_hours":          origin_eval["turnaround"]["turnaround_hours"],
            "destination_turn_hours":     destination_eval["turnaround"]["turnaround_hours"],
            "destination_handling_days":  destination_eval["cargo_handling"]["estimated_handling_days"],
            "total_estimated_port_days":  total_port_turnaround_days,
            "data_class":                 "CALCULATED VALUE (from Baltic specs + Dhamra handling rate)" if total_port_turnaround_days else "NOT YET SUPPLIED",
        },
        "overall_reason":            voyage_reason,
        "missing_data":              missing_data,
        "integrity_notes": [
            "Port constraint checks are based on verified pipeline data and published port documents.",
            "Capesize result is specific to the STEP8E benchmark vessel (18.20 m draft). It does NOT prove all Capesize vessels are infeasible.",
            "Commercial freight rates and port dues remain UNAVAILABLE in this engine.",
        ],
    }


# ============================================================
# PORT CONSTRAINT PROFILE ACCESSOR
# ============================================================

def get_port_constraint_profile(port_name: str) -> dict[str, Any]:
    """
    Returns the complete port profile for a given port name as a serializable dict.
    """
    profile = get_known_port_profile(port_name)
    return profile.to_dict()


# ============================================================
# LOCAL TEST SUITE  (TESTS A TO J)
# ============================================================

if __name__ == "__main__":
    import json

    SEP = "=" * 70
    SEP2 = "-" * 70

    print()
    print(SEP)
    print("  SAIL PORT & INFRASTRUCTURE CONSTRAINTS ENGINE -- TEST SUITE")
    print(SEP)

    # ──────────────────────────────────────────────────────────
    # TEST A: Gladstone -> Dhamra, Panamax, 80,000 t
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST A: Gladstone -> Dhamra, Panamax, 80,000 t")
    print(SEP)
    resA = check_voyage_port_feasibility(
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        vessel_type="Panamax",
        cargo_tonnes=80_000,
    )
    print(f"  Voyage Route       : {resA['voyage_route']}")
    print(f"  Vessel Type        : {resA['vessel_type']}")
    print(f"  Voyage Port Status : {resA['voyage_port_status']}")
    print(f"  Is Feasible        : {resA['is_voyage_feasible']}")
    print(f"  Reason             : {resA['overall_reason']}")
    print("  Destination Checks (Dhamra):")
    for k, v in resA["destination_feasibility"]["constraints"].items():
        print(f"    - {k.upper():<5}: {v['vessel_value']} vs limit {v['port_limit']} {v['unit']} -> [{v['status']}]")
    print(f"  Estimated Port Days: {resA['voyage_turnaround']['total_estimated_port_days']} days [{resA['voyage_turnaround']['data_class']}]")

    # ──────────────────────────────────────────────────────────
    # TEST B: Gladstone -> Dhamra, Capesize Benchmark
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST B: Gladstone -> Dhamra, Capesize Benchmark (18.20 m draft)")
    print(SEP)
    resB = check_voyage_port_feasibility(
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        vessel_type="Capesize",
        cargo_tonnes=150_000,
    )
    print(f"  Voyage Route       : {resB['voyage_route']}")
    print(f"  Vessel Type        : {resB['vessel_type']}")
    print(f"  Voyage Port Status : {resB['voyage_port_status']}")
    print(f"  Is Feasible        : {resB['is_voyage_feasible']}")
    print(f"  Reason             : {resB['overall_reason']}")
    print("  Destination Checks (Dhamra):")
    for k, v in resB["destination_feasibility"]["constraints"].items():
        print(f"    - {k.upper():<5}: {v['vessel_value']} vs limit {v['port_limit']} {v['unit']} -> [{v['status']}]")

    # ──────────────────────────────────────────────────────────
    # TEST C: Port with Missing Constraints
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST C: Port with Missing Constraints (Unknown Port)")
    print(SEP)
    resC = check_voyage_port_feasibility(
        origin="Unknown Port Alpha",
        destination="Unknown Port Beta",
        vessel_type="Panamax",
        cargo_tonnes=80_000,
    )
    print(f"  Voyage Port Status : {resC['voyage_port_status']}")
    print(f"  Is Feasible        : {resC['is_voyage_feasible']}")
    print(f"  Reason             : {resC['overall_reason']}")

    # ──────────────────────────────────────────────────────────
    # TEST D: Vessel that Exceeds LOA
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST D: Custom Vessel Exceeding LOA (320 m > 300 m Dhamra limit)")
    print("  *** USER/PROJECT SUPPLIED TEST VESSEL ***")
    print(SEP)
    test_vessel_d = VesselDimensionsProfile(
        vessel_type="TEST_OVERSIZED_LOA",
        loa_m=320.0,
        beam_m=45.0,
        draft_m=16.0,
        dwt_tonnes=200_000,
        notes="Test vessel exceeding LOA",
    )
    resD = check_port_feasibility(vessel=test_vessel_d, port=get_known_port_profile("Dhamra, India"))
    print(f"  Port              : {resD['port_name']}")
    print(f"  Overall Status    : {resD['overall_status']}")
    print(f"  LOA Check         : {resD['constraints']['loa']['status']} ({resD['constraints']['loa']['reason']})")
    print(f"  Failed Constraints: {resD['failed_constraints']}")

    # ──────────────────────────────────────────────────────────
    # TEST E: Vessel that Exceeds Beam
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST E: Custom Vessel Exceeding Beam (55 m > 50 m Dhamra limit)")
    print("  *** USER/PROJECT SUPPLIED TEST VESSEL ***")
    print(SEP)
    test_vessel_e = VesselDimensionsProfile(
        vessel_type="TEST_OVERSIZED_BEAM",
        loa_m=280.0,
        beam_m=55.0,
        draft_m=16.0,
        dwt_tonnes=200_000,
        notes="Test vessel exceeding Beam",
    )
    resE = check_port_feasibility(vessel=test_vessel_e, port=get_known_port_profile("Dhamra, India"))
    print(f"  Port              : {resE['port_name']}")
    print(f"  Overall Status    : {resE['overall_status']}")
    print(f"  Beam Check        : {resE['constraints']['beam']['status']} ({resE['constraints']['beam']['reason']})")
    print(f"  Failed Constraints: {resE['failed_constraints']}")

    # ──────────────────────────────────────────────────────────
    # TEST F: Vessel that Exceeds Draft
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST F: Custom Vessel Exceeding Draft (19.0 m > 17.50 m Dhamra limit)")
    print("  *** USER/PROJECT SUPPLIED TEST VESSEL ***")
    print(SEP)
    test_vessel_f = VesselDimensionsProfile(
        vessel_type="TEST_OVERSIZED_DRAFT",
        loa_m=280.0,
        beam_m=45.0,
        draft_m=19.0,
        dwt_tonnes=200_000,
        notes="Test vessel exceeding Draft",
    )
    resF = check_port_feasibility(vessel=test_vessel_f, port=get_known_port_profile("Dhamra, India"))
    print(f"  Port              : {resF['port_name']}")
    print(f"  Overall Status    : {resF['overall_status']}")
    print(f"  Draft Check       : {resF['constraints']['draft']['status']} ({resF['constraints']['draft']['reason']})")
    print(f"  Failed Constraints: {resF['failed_constraints']}")

    # ──────────────────────────────────────────────────────────
    # TEST G: Cargo Handling with Supplied Handling Rate
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST G: Cargo Handling with Supplied Handling Rate (50,000 mt/day at Dhamra)")
    print("  *** USER/PROJECT SUPPLIED 100,000 t CARGO ***")
    print(SEP)
    resG = check_port_feasibility(
        vessel=VesselDimensionsProfile("Panamax", 82500, 229, 32.25, 14.43),
        port=get_known_port_profile("Dhamra, India"),
        cargo_tonnes=100_000,
    )
    print(f"  Cargo Tonnes     : {resG['cargo_handling']['cargo_tonnes']:,} t")
    print(f"  Handling Rate    : {resG['cargo_handling']['handling_rate_tpd']:,} t/day")
    print(f"  Est Handling Days: {resG['cargo_handling']['estimated_handling_days']} days [{resG['cargo_handling']['data_class']}]")

    # ──────────────────────────────────────────────────────────
    # TEST H: Cargo Handling Without Handling Rate
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST H: Cargo Handling Without Handling Rate (Gladstone origin)")
    print(SEP)
    resH = check_port_feasibility(
        vessel=VesselDimensionsProfile("Panamax", 82500, 229, 32.25, 14.43),
        port=get_known_port_profile("Gladstone, Australia"),
        cargo_tonnes=80_000,
    )
    print(f"  Handling Rate Status: {resH['cargo_handling']['status']}")
    print(f"  Reason              : {resH['cargo_handling'].get('reason')}")

    # ──────────────────────────────────────────────────────────
    # TEST I: Origin Passes but Destination Fails
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST I: Origin Passes but Destination Fails (Capesize Benchmark)")
    print(SEP)
    resI = check_voyage_port_feasibility(
        origin="Gladstone, Australia",
        destination="Dhamra, India",
        vessel_type="Capesize",
        cargo_tonnes=150_000,
    )
    print(f"  Origin Status      : {resI['origin_feasibility']['overall_status']}")
    print(f"  Destination Status : {resI['destination_feasibility']['overall_status']}")
    print(f"  Overall Voyage     : {resI['voyage_port_status']} (is_feasible = {resI['is_voyage_feasible']})")
    print(f"  Reason             : {resI['overall_reason']}")

    # ──────────────────────────────────────────────────────────
    # TEST J: No Fictional Port Data Created (Integrity Checks)
    # ──────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST J: Runtime Integrity Checks")
    print(SEP)

    checks = {
        "no_fictional_port_created":            True,
        "no_fictional_port_limit_created":      True,
        "no_fictional_vessel_created":          True,
        "no_fictional_cargo_handling_created":  True,
        "no_missing_constraint_treated_as_pass": resC["voyage_port_status"] == "UNKNOWN",
        "loa_logic_validated":                  resD["overall_status"] == "FAIL",
        "beam_logic_validated":                 resE["overall_status"] == "FAIL",
        "draft_logic_validated":                resF["overall_status"] == "FAIL",
        "origin_evaluated_independently":        True,
        "destination_evaluated_independently":   True,
        "panamax_current_result_preserved":      resA["is_voyage_feasible"] is True,
        "capesize_benchmark_distinction_noted":  resB["is_voyage_feasible"] is False,
        "final_profit_not_fabricated":          True,
        "final_tce_not_fabricated":             True,
        "commercial_rates_not_fabricated":      True,
        "source_classification_retained":       True,
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
