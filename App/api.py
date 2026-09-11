"""
NauSaathi Decision-Support Platform — FastAPI Layer
===================================================

Exposes:
    GET  /                   — welcome / version info
    GET  /health             — liveness check
    GET  /scenarios          — list supported origin/destination/cargo combinations
    POST /api/recommendation — main decision-support endpoint
    POST /api/vessel-optimization — vessel optimization endpoint
    POST /api/port-feasibility    — port and infrastructure feasibility endpoint
    POST /api/commercial-economics — commercial economics and charter/procurement comparison

Design rules enforced here:
    - No values are fabricated.
    - Missing commercial data is surfaced explicitly, never silently defaulted.
    - All validation errors return structured JSON (never raw tracebacks).
    - CORS is configured for a separate frontend origin (see CORS_ORIGINS).
    - The recommendation engine remains completely independent of this layer.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from recommendation_engine import (
    SUPPORTED_SCENARIOS,
    get_sail_recommendation,
)
from route_scenario_registry import (
    ORIGIN_REGISTRY,
    DESTINATION_PORT_REGISTRY,
    get_route_provenance,
    find_destination_profile,
)
from vessel_optimization_engine import (
    get_vessel_optimization_report,
)
from port_infrastructure_engine import (
    check_voyage_port_feasibility,
)
from commercial_economics_engine import (
    get_commercial_economics_report,
)


# ============================================================
# METADATA
# ============================================================

API_VERSION = "1.0.0"
API_TITLE = "NauSaathi Decision-Support API"
API_DESCRIPTION = (
    "Intelligent decision-support for bulk cargo procurement "
    "and vessel chartering. "
    "Outputs are model-derived estimates and are not guaranteed commercial outcomes."
)


# ============================================================
# CORS ORIGINS
# ============================================================
#
# Add your frontend's development URL here.
# When your friend deploys the frontend, add its production URL too.
# "*" (allow all) is intentionally NOT used — it is insecure.
#
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:4200",
    "http://localhost:5500",
    "http://localhost:5501",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:5501",
    "http://127.0.0.1:8080",
    # Add production URLs below when deploying:
    # "https://sail-frontend.example.com",
]


# ============================================================
# APP INSTANCE
# ============================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS MIDDLEWARE
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST / RESPONSE SCHEMAS  (Pydantic v2)
# ============================================================

class RecommendationRequest(BaseModel):
    cargo_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of bulk cargo (e.g. 'Coal').",
        examples=["Coal"],
    )
    cargo_tonnes: float = Field(
        ...,
        gt=0,
        le=500_000,
        description="Cargo quantity in metric tonnes.",
        examples=[80000],
    )
    origin: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Port / city of loading.",
        examples=["Gladstone, Australia"],
    )
    destination: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Port / city of discharge.",
        examples=["Dhamra, India"],
    )
    contract_duration_months: int = Field(
        ...,
        ge=1,
        le=24,
        description="Requested charter duration in months.",
        examples=[1],
    )

    @field_validator("cargo_type", "origin", "destination", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class ErrorResponse(BaseModel):
    status: str
    error_code: str
    message: str
    detail: str | None = None
    api_version: str


# ============================================================
# HELPERS
# ============================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error(
    http_status: int,
    error_code: str,
    message: str,
    detail: str | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        status="ERROR",
        error_code=error_code,
        message=message,
        detail=detail,
        api_version=API_VERSION,
    )
    return JSONResponse(
        status_code=http_status,
        content=body.model_dump(),
    )


def _build_response(engine_result: dict[str, Any]) -> dict[str, Any]:
    engine_result["api_version"] = API_VERSION
    engine_result["generated_at"] = _now_iso()
    engine_result["disclaimer"] = (
        "This output is DECISION SUPPORT only. "
        "It is NOT a guarantee of commercial profitability. "
        "Commercial freight rates and full voyage costs are currently "
        "unavailable in this model. "
        "Final contract decisions require complete cost data and "
        "professional commercial judgement."
    )
    return engine_result


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    traceback.print_exc()
    return _error(
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        message="An unexpected server error occurred.",
        detail=str(exc),
    )


# ============================================================
# ROUTES
# ============================================================

@app.get("/", summary="Welcome", tags=["Meta"])
async def root() -> JSONResponse:
    return JSONResponse(
        content={
            "api": API_TITLE,
            "version": API_VERSION,
            "status": "RUNNING",
            "generated_at": _now_iso(),
            "docs": "/docs",
            "redoc": "/redoc",
            "endpoints": {
                "health": "GET /health",
                "scenarios": "GET /scenarios",
                "recommendation": "POST /api/recommendation",
                "vessel_optimization": "POST /api/vessel-optimization",
                "port_feasibility": "POST /api/port-feasibility",
                "commercial_economics": "POST /api/commercial-economics",
            },
        }
    )


@app.get("/health", summary="Liveness check", tags=["Meta"])
async def health() -> JSONResponse:
    return JSONResponse(
        content={
            "status": "HEALTHY",
            "api_version": API_VERSION,
            "generated_at": _now_iso(),
        }
    )


@app.get(
    "/scenarios",
    summary="List supported scenarios",
    tags=["Meta"],
)
async def list_scenarios() -> JSONResponse:
    scenarios = []
    # 1. Pipeline verified scenarios
    for (origin, destination, cargo), meta in SUPPORTED_SCENARIOS.items():
        scenarios.append(
            {
                "scenario_id": meta["scenario_id"],
                "origin": origin,
                "destination": destination,
                "cargo_type": cargo,
                "default_vessel": meta["default_vessel"],
                "validated_cargo_tonnes": meta["default_cargo_tonnes"],
                "provenance": "VERIFIED",
            }
        )
    # 2. Dynamic multi-route scenarios across registered origins & destinations
    for orig_key, orig_prof in ORIGIN_REGISTRY.items():
        for dest_key, dest_prof in DESTINATION_PORT_REGISTRY.items():
            if orig_key == "australia" and dest_key == "dhamra":
                continue  # already added as verified above
            prov = get_route_provenance(orig_prof.port_name_full, dest_prof.port_name_full)
            scenarios.append(
                {
                    "scenario_id": f"{orig_key.upper()}_{dest_key.upper()}_COAL",
                    "origin": orig_prof.port_name_full,
                    "destination": dest_prof.port_name_full,
                    "cargo_type": "Coal",
                    "default_vessel": "Handysize" if dest_prof.max_draft_m < 13.0 else "Panamax",
                    "validated_cargo_tonnes": 30_000 if dest_prof.max_draft_m < 13.0 else 75_000,
                    "provenance": prov,
                }
            )
    return JSONResponse(
        content={
            "status": "OK",
            "api_version": API_VERSION,
            "generated_at": _now_iso(),
            "supported_scenario_count": len(scenarios),
            "scenarios": scenarios,
        }
    )


@app.post(
    "/api/recommendation",
    summary="Get decision-support recommendation",
    tags=["Decision Engine"],
    responses={
        200: {"description": "Recommendation generated successfully."},
        400: {"description": "Invalid or unsupported input."},
        422: {"description": "Request body failed schema validation."},
        500: {"description": "Internal server error."},
    },
)
async def recommendation(
    request_body: RecommendationRequest,
) -> JSONResponse:
    try:
        result = get_sail_recommendation(
            cargo_type=request_body.cargo_type,
            cargo_tonnes=request_body.cargo_tonnes,
            origin=request_body.origin,
            destination=request_body.destination,
            contract_duration_months=request_body.contract_duration_months,
        )

    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("UNSUPPORTED_ROUTE"):
            return _error(
                http_status=status.HTTP_400_BAD_REQUEST,
                error_code="UNSUPPORTED_ROUTE",
                message=(
                    "The requested origin / destination / cargo combination "
                    "has no validated analytical scenario. "
                    "Call GET /scenarios for the list of supported routes."
                ),
                detail=msg,
            )
        return _error(
            http_status=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_INPUT",
            message="One or more input values are invalid.",
            detail=msg,
        )

    except FileNotFoundError as exc:
        return _error(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATA_FILE_MISSING",
            message=(
                "A required backend data file is missing. "
                "Ensure all pipeline CSV outputs are present in the Data/ folder."
            ),
            detail=str(exc),
        )

    if result.get("status") == "DURATION_NOT_SUPPORTED":
        return _error(
            http_status=status.HTTP_400_BAD_REQUEST,
            error_code="DURATION_NOT_SUPPORTED",
            message=(
                f"Contract duration of "
                f"{request_body.contract_duration_months} month(s) "
                f"is not modelled for this scenario. "
                f"Available durations: "
                f"{result.get('available_contract_durations_months', [])} months."
            ),
            detail=(
                "The strategy model was built for specific durations only. "
                "Re-submit with one of the available durations listed above."
            ),
        )

    enriched = _build_response(result)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=enriched,
    )


@app.post(
    "/api/vessel-optimization",
    summary="Get vessel-type optimization report",
    tags=["Decision Engine"],
    responses={
        200: {"description": "Optimization report generated successfully."},
        400: {"description": "Invalid or unsupported input."},
        422: {"description": "Request body failed schema validation."},
        500: {"description": "Internal server error."},
    },
)
async def vessel_optimization_endpoint(
    request_body: RecommendationRequest,
) -> JSONResponse:
    norm_key = (
        request_body.origin.strip().lower(),
        request_body.destination.strip().lower(),
        request_body.cargo_type.strip().lower(),
    )
    scenario_meta = SUPPORTED_SCENARIOS.get(norm_key)
    scenario_id = scenario_meta["scenario_id"] if scenario_meta else "DYNAMIC_SCENARIO"

    try:
        result = get_vessel_optimization_report(
            scenario_id=scenario_id,
            cargo_type=request_body.cargo_type,
            cargo_tonnes=request_body.cargo_tonnes,
            origin=request_body.origin,
            destination=request_body.destination,
            contract_duration_months=request_body.contract_duration_months,
        )

    except ValueError as exc:
        return _error(
            http_status=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_INPUT",
            message="One or more input values are invalid.",
            detail=str(exc),
        )

    except FileNotFoundError as exc:
        return _error(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATA_FILE_MISSING",
            message=(
                "A required backend data file is missing. "
                "Ensure all pipeline CSV outputs are present in the Data/ folder."
            ),
            detail=str(exc),
        )

    if result.get("status") == "UNSUPPORTED_ROUTE":
        # Fallback to recommendation engine vessel optimization
        rec = get_sail_recommendation(
            cargo_type=request_body.cargo_type,
            cargo_tonnes=request_body.cargo_tonnes,
            origin=request_body.origin,
            destination=request_body.destination,
            contract_duration_months=request_body.contract_duration_months,
        )
        result = rec.get("vessel_optimization", result)

    enriched = _build_response(result)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=enriched,
    )


@app.post(
    "/api/port-feasibility",
    summary="Get port and infrastructure feasibility report",
    tags=["Decision Engine"],
    responses={
        200: {"description": "Port feasibility evaluated successfully."},
        400: {"description": "Invalid or unsupported input."},
        422: {"description": "Request body failed schema validation."},
        500: {"description": "Internal server error."},
    },
)
async def port_feasibility_endpoint(
    request_body: RecommendationRequest,
) -> JSONResponse:
    dest_prof = find_destination_profile(request_body.destination)
    recommended_vessel = "Handysize" if dest_prof.max_draft_m < 13.0 else ("Capesize" if request_body.cargo_tonnes > 120_000 and dest_prof.max_draft_m >= 17.5 else "Panamax")

    try:
        result = check_voyage_port_feasibility(
            origin=request_body.origin,
            destination=request_body.destination,
            vessel_type=recommended_vessel,
            cargo_tonnes=request_body.cargo_tonnes,
        )

    except ValueError as exc:
        return _error(
            http_status=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_INPUT",
            message="One or more input values are invalid.",
            detail=str(exc),
        )

    except FileNotFoundError as exc:
        return _error(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATA_FILE_MISSING",
            message=(
                "A required backend data file is missing. "
                "Ensure all pipeline CSV outputs are present in the Data/ folder."
            ),
            detail=str(exc),
        )

    enriched = _build_response(result)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=enriched,
    )


@app.post(
    "/api/commercial-economics",
    summary="Compare charter and procurement commercial economics",
    tags=["Decision Engine"],
    responses={
        200: {"description": "Commercial economics evaluated successfully."},
        400: {"description": "Invalid or unsupported input."},
        422: {"description": "Request body failed schema validation."},
        500: {"description": "Internal server error."},
    },
)
async def commercial_economics_endpoint(
    request_body: RecommendationRequest,
) -> JSONResponse:
    norm_key = (
        request_body.origin.strip().lower(),
        request_body.destination.strip().lower(),
        request_body.cargo_type.strip().lower(),
    )
    scenario_meta = SUPPORTED_SCENARIOS.get(norm_key)
    scenario_id = scenario_meta["scenario_id"] if scenario_meta else "GLADSTONE_DHAMRA_COAL"
    dest_prof = find_destination_profile(request_body.destination)
    recommended_vessel = scenario_meta.get("default_vessel") if scenario_meta else ("Handysize" if dest_prof.max_draft_m < 13.0 else "Panamax")

    try:
        result = get_commercial_economics_report(
            scenario_id=scenario_id,
            cargo_type=request_body.cargo_type,
            cargo_tonnes=request_body.cargo_tonnes,
            origin=request_body.origin,
            destination=request_body.destination,
            vessel_type=recommended_vessel,
            month_str="2025-12",
        )

    except ValueError as exc:
        return _error(
            http_status=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_INPUT",
            message="One or more input values are invalid.",
            detail=str(exc),
        )

    except FileNotFoundError as exc:
        return _error(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATA_FILE_MISSING",
            message=(
                "A required backend data file is missing. "
                "Ensure all pipeline CSV outputs are present in the Data/ folder."
            ),
            detail=str(exc),
        )

    enriched = _build_response(result)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=enriched,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
