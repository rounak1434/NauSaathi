"""
SAIL / NauSaathi Decision-Support Platform
=========================================
route_scenario_registry.py

Provides a centralized, maintainable registry of:
- Origin countries & representative load ports
- Destination ports (Indian East Coast bulk ports) with physical limits (Draft, LOA, Beam)
- Vessel classes (Handysize, Supramax, Panamax, Capesize)
- Voyage distance matrix
- Data provenance classification (VERIFIED, DERIVED, SCENARIO)

CRITICAL RULES:
- Gladstone, Australia -> Dhamra, India is classified as VERIFIED (anchored in STEP8 pipeline data).
- Other routes are classified as DERIVED (physical engineering checks against published port constraints)
  or SCENARIO (simulated parameters for demonstration).
- Transparent provenance is attached to every profile and calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ============================================================
# DATA PROVENANCE ENUMS
# ============================================================

class DataProvenance:
    VERIFIED = "VERIFIED"    # Ground truth from project pipeline CSVs
    DERIVED = "DERIVED"      # Evaluated via physical engineering / constraint models
    SCENARIO = "SCENARIO"    # Model simulation / baseline assumption


# ============================================================
# VESSEL SPECIFICATIONS (4 Dry Bulk Classes)
# ============================================================

@dataclass(frozen=True)
class VesselSpecification:
    vessel_class: str
    dwt_tonnes: float
    min_cargo_tonnes: float
    max_cargo_tonnes: float
    loa_m: float
    beam_m: float
    draft_m: float
    laden_speed_knots: float
    ballast_speed_knots: float
    laden_fuel_tpd: float
    ballast_fuel_tpd: float
    description: str
    provenance: str = DataProvenance.VERIFIED


VESSEL_REGISTRY: dict[str, VesselSpecification] = {
    "handysize": VesselSpecification(
        vessel_class="Handysize",
        dwt_tonnes=35_000,
        min_cargo_tonnes=20_000,
        max_cargo_tonnes=38_000,
        loa_m=180.0,
        beam_m=28.0,
        draft_m=10.0,
        laden_speed_knots=13.0,
        ballast_speed_knots=13.5,
        laden_fuel_tpd=20.0,
        ballast_fuel_tpd=18.0,
        description="Geared small bulk carrier suitable for shallow draft and regional riverine ports (e.g., Haldia).",
        provenance=DataProvenance.DERIVED,
    ),
    "supramax": VesselSpecification(
        vessel_class="Supramax",
        dwt_tonnes=58_000,
        min_cargo_tonnes=40_000,
        max_cargo_tonnes=62_000,
        loa_m=190.0,
        beam_m=32.26,
        draft_m=12.8,
        laden_speed_knots=13.5,
        ballast_speed_knots=14.0,
        laden_fuel_tpd=28.0,
        ballast_fuel_tpd=25.0,
        description="Versatile dry bulk vessel with self-unloading gear; suitable for intermediate draft ports (Gopalpur, Paradip).",
        provenance=DataProvenance.DERIVED,
    ),
    "panamax": VesselSpecification(
        vessel_class="Panamax",
        dwt_tonnes=82_500,
        min_cargo_tonnes=65_000,
        max_cargo_tonnes=85_000,
        loa_m=229.0,
        beam_m=32.25,
        draft_m=14.43,
        laden_speed_knots=13.5,
        ballast_speed_knots=14.0,
        laden_fuel_tpd=33.0,
        ballast_fuel_tpd=31.0,
        description="Standard gearless coal carrier based on Baltic P9 index specification; optimal fit for 70k-85k MT parcels.",
        provenance=DataProvenance.VERIFIED,
    ),
    "capesize": VesselSpecification(
        vessel_class="Capesize",
        dwt_tonnes=182_000,
        min_cargo_tonnes=120_000,
        max_cargo_tonnes=190_000,
        loa_m=292.0,
        beam_m=45.0,
        draft_m=18.2,
        laden_speed_knots=14.0,
        ballast_speed_knots=15.0,
        laden_fuel_tpd=52.0,
        ballast_fuel_tpd=44.0,
        description="Large gearless heavy bulk carrier based on Baltic C18 specification; requires deepwater draft (Dhamra, Gangavaram).",
        provenance=DataProvenance.VERIFIED,
    ),
}


# ============================================================
# ORIGIN COUNTRIES & REPRESENTATIVE LOAD PORTS
# ============================================================

@dataclass(frozen=True)
class OriginProfile:
    country: str
    representative_port: str
    port_name_full: str
    max_loa_m: float | None
    max_beam_m: float | None
    max_draft_m: float | None
    turnaround_hours: float
    provenance: str = DataProvenance.SCENARIO


ORIGIN_REGISTRY: dict[str, OriginProfile] = {
    "australia": OriginProfile(
        country="Australia",
        representative_port="Gladstone",
        port_name_full="Gladstone, Australia",
        max_loa_m=300.0,
        max_beam_m=50.0,
        max_draft_m=18.5,
        turnaround_hours=12.0,
        provenance=DataProvenance.VERIFIED,
    ),
    "united states": OriginProfile(
        country="United States",
        representative_port="Hampton Roads",
        port_name_full="Hampton Roads, United States",
        max_loa_m=300.0,
        max_beam_m=45.0,
        max_draft_m=15.5,
        turnaround_hours=24.0,
        provenance=DataProvenance.SCENARIO,
    ),
    "mozambique": OriginProfile(
        country="Mozambique",
        representative_port="Maputo",
        port_name_full="Maputo, Mozambique",
        max_loa_m=260.0,
        max_beam_m=42.0,
        max_draft_m=14.2,
        turnaround_hours=24.0,
        provenance=DataProvenance.SCENARIO,
    ),
    "indonesia": OriginProfile(
        country="Indonesia",
        representative_port="Balikpapan",
        port_name_full="Balikpapan, Indonesia",
        max_loa_m=280.0,
        max_beam_m=45.0,
        max_draft_m=15.0,
        turnaround_hours=18.0,
        provenance=DataProvenance.SCENARIO,
    ),
    "russia": OriginProfile(
        country="Russia",
        representative_port="Vostochny",
        port_name_full="Vostochny, Russia",
        max_loa_m=300.0,
        max_beam_m=48.0,
        max_draft_m=17.0,
        turnaround_hours=20.0,
        provenance=DataProvenance.SCENARIO,
    ),
}


# ============================================================
# DISCHARGE / DESTINATION PORTS (Indian East Coast)
# ============================================================

@dataclass(frozen=True)
class DestinationPortProfile:
    name: str
    state: str
    port_name_full: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    max_dwt_tonnes: float
    discharge_rate_tpd: float
    turnaround_hours: float
    mechanized: bool
    notes: str
    lighterage_support: bool = True
    provenance: str = DataProvenance.DERIVED


DESTINATION_PORT_REGISTRY: dict[str, DestinationPortProfile] = {
    "dhamra": DestinationPortProfile(
        name="Dhamra",
        state="Odisha",
        port_name_full="Dhamra, India",
        max_loa_m=300.0,
        max_beam_m=50.0,
        max_draft_m=17.50,
        max_dwt_tonnes=180_000,
        discharge_rate_tpd=50_000,
        turnaround_hours=24.0,
        mechanized=True,
        notes="Deep draft all-weather port capable of handling Capesize and Panamax bulk vessels up to 17.5m draft.",
        provenance=DataProvenance.VERIFIED,
    ),
    "gangavaram": DestinationPortProfile(
        name="Gangavaram",
        state="Andhra Pradesh",
        port_name_full="Gangavaram, India",
        max_loa_m=300.0,
        max_beam_m=50.0,
        max_draft_m=18.50,
        max_dwt_tonnes=200_000,
        discharge_rate_tpd=45_000,
        turnaround_hours=24.0,
        mechanized=True,
        notes="Deepest all-weather port in India; can comfortably accommodate fully laden Capesize and Super-Capesize vessels.",
        provenance=DataProvenance.DERIVED,
    ),
    "visakhapatnam": DestinationPortProfile(
        name="Visakhapatnam",
        state="Andhra Pradesh",
        port_name_full="Visakhapatnam, India",
        max_loa_m=280.0,
        max_beam_m=45.0,
        max_draft_m=16.50,
        max_dwt_tonnes=150_000,
        discharge_rate_tpd=35_000,
        turnaround_hours=24.0,
        mechanized=True,
        notes="Major multi-cargo port. Outer harbor takes Capesize/Panamax up to 16.5m draft; inner harbor restricted to Panamax/Supramax.",
        provenance=DataProvenance.DERIVED,
    ),
    "paradip": DestinationPortProfile(
        name="Paradip",
        state="Odisha",
        port_name_full="Paradip, India",
        max_loa_m=260.0,
        max_beam_m=42.0,
        max_draft_m=14.50,
        max_dwt_tonnes=95_000,
        discharge_rate_tpd=30_000,
        turnaround_hours=24.0,
        mechanized=True,
        notes="High volume bulk port. Ideal for Panamax and Supramax vessels. Capesize requires offshore lighterage or partial deballasting.",
        provenance=DataProvenance.DERIVED,
    ),
    "gopalpur": DestinationPortProfile(
        name="Gopalpur",
        state="Odisha",
        port_name_full="Gopalpur, India",
        max_loa_m=225.0,
        max_beam_m=32.5,
        max_draft_m=12.50,
        max_dwt_tonnes=65_000,
        discharge_rate_tpd=20_000,
        turnaround_hours=36.0,
        mechanized=False,
        notes="Intermediate all-weather port. Optimal for Supramax and Handysize vessels; draft restricts fully laden Panamax/Capesize.",
        provenance=DataProvenance.DERIVED,
    ),
    "sagar-sandheads": DestinationPortProfile(
        name="Sagar-Sandheads",
        state="West Bengal",
        port_name_full="Sagar-Sandheads, India",
        max_loa_m=200.0,
        max_beam_m=32.2,
        max_draft_m=11.00,
        max_dwt_tonnes=50_000,
        discharge_rate_tpd=15_000,
        turnaround_hours=48.0,
        mechanized=False,
        notes="Anchorage and transshipment lighterage zone for Kolkata/Haldia river approach.",
        provenance=DataProvenance.DERIVED,
    ),
    "haldia": DestinationPortProfile(
        name="Haldia",
        state="West Bengal",
        port_name_full="Haldia, India",
        max_loa_m=190.0,
        max_beam_m=28.0,
        max_draft_m=8.00,
        max_dwt_tonnes=35_000,
        discharge_rate_tpd=12_000,
        turnaround_hours=36.0,
        mechanized=False,
        notes="Riverine dock system restricted by Hooghly river bar draft. Strictly restricted to Handysize and parcel lighterage.",
        provenance=DataProvenance.DERIVED,
    ),
}


# ============================================================
# NAUTICAL DISTANCES (nm) MATRIX
# ============================================================

# Base distances from load ports to Indian East Coast average
# Regional variations for specific ports are adjusted within +/- 150 nm
BASE_DISTANCES: dict[str, float] = {
    "australia": 5827.27,      # Gladstone -> East Coast India (STEP8D ground truth)
    "indonesia": 2350.00,      # Balikpapan -> East Coast India
    "mozambique": 4420.00,     # Maputo -> East Coast India
    "russia": 5350.00,         # Vostochny -> East Coast India
    "united states": 9250.00,  # Hampton Roads -> East Coast India via Cape of Good Hope
}

# Discharge port differential relative to central East Coast (nm)
PORT_DISTANCE_OFFSET: dict[str, float] = {
    "dhamra": 0.0,
    "paradip": -45.0,
    "visakhapatnam": -180.0,
    "gangavaram": -190.0,
    "gopalpur": -90.0,
    "sagar-sandheads": 60.0,
    "haldia": 110.0,
}


def get_route_distance_nm(origin_key: str, destination_key: str) -> tuple[float, str]:
    """
    Returns (distance_nm, provenance).
    Gladstone -> Dhamra returns exact 5827.27 nm with VERIFIED status.
    Raises ValueError("UNSUPPORTED_ROUTE: ...") if origin or destination is unknown.
    """
    o_norm = _normalize(origin_key)
    d_norm = _normalize(destination_key)

    if ("australia" in o_norm or "gladstone" in o_norm) and "dhamra" in d_norm:
        return 5827.27, DataProvenance.VERIFIED

    # Match registered origin country or port substring
    base = None
    for k, v in BASE_DISTANCES.items():
        if k in o_norm:
            base = v
            break

    if base is None:
        raise ValueError(
            f"UNSUPPORTED_ROUTE: Unknown origin '{origin_key}'. "
            f"Supported origins: {sorted([p.country for p in ORIGIN_REGISTRY.values()])}."
        )

    # Match registered destination port substring
    offset = None
    for k, v in PORT_DISTANCE_OFFSET.items():
        if k in d_norm:
            offset = v
            break

    if offset is None:
        raise ValueError(
            f"UNSUPPORTED_ROUTE: Unknown destination '{destination_key}'. "
            f"Supported destinations: {sorted([p.name for p in DESTINATION_PORT_REGISTRY.values()])}."
        )

    dist = round(base + offset, 2)
    return dist, DataProvenance.DERIVED


# ============================================================
# REGISTRY LOOKUP UTILITIES
# ============================================================

def _normalize(val: Any) -> str:
    return str(val or "").strip().lower()


def find_origin_profile(origin_name: str) -> OriginProfile:
    """
    Looks up the origin profile from the validated registry.
    Raises ValueError("UNSUPPORTED_ROUTE: ...") if no registered origin matches.
    """
    norm = _normalize(origin_name)
    for key, prof in ORIGIN_REGISTRY.items():
        if key in norm or _normalize(prof.representative_port) in norm or _normalize(prof.country) in norm:
            return prof
    raise ValueError(
        f"UNSUPPORTED_ROUTE: Origin '{origin_name}' is not in the validated origin registry. "
        f"Supported origins: {sorted([p.country for p in ORIGIN_REGISTRY.values()])}."
    )


def find_destination_profile(dest_name: str) -> DestinationPortProfile:
    """
    Looks up the destination port profile from the validated registry.
    Raises ValueError("UNSUPPORTED_ROUTE: ...") if no registered destination matches.
    """
    norm = _normalize(dest_name)
    for key, prof in DESTINATION_PORT_REGISTRY.items():
        if key in norm or _normalize(prof.name) in norm:
            return prof
    raise ValueError(
        f"UNSUPPORTED_ROUTE: Destination '{dest_name}' is not in the validated destination port registry. "
        f"Supported destinations: {sorted([p.name for p in DESTINATION_PORT_REGISTRY.values()])}."
    )


def get_route_provenance(origin_name: str, dest_name: str) -> str:
    """
    Returns VERIFIED if exact Gladstone -> Dhamra coal route,
    DERIVED if destination is a configured Indian port with verified hydrographic constraints,
    SCENARIO otherwise.
    """
    o_norm = _normalize(origin_name)
    d_norm = _normalize(dest_name)

    if ("gladstone" in o_norm or "australia" in o_norm) and "dhamra" in d_norm:
        return DataProvenance.VERIFIED

    if any(k in d_norm for k in DESTINATION_PORT_REGISTRY):
        return DataProvenance.DERIVED

    return DataProvenance.SCENARIO
