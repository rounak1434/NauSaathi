# NauSaarthi Frontend — Backend Integration Specification

> **Architecture Overview:** End-to-End data flow from the existing FastAPI backend engines to the NauSaarthi React decision-support dashboard.

---

## 1. End-to-End Architecture

```text
+-------------------------------------------------------------------------------+
|                        NauSaarthi Frontend (React Dashboard)                  |
|   - ScenarioForm.jsx (User Inputs: Cargo, Tonnes, Origin, Dest, Duration)     |
|   - ExecutiveSummary.jsx / MarketIntelligence.jsx / PortFeasibility.jsx       |
+-------------------------------------------------------------------------------+
                                       |
                                       | HTTP POST /api/recommendation
                                       v
+-------------------------------------------------------------------------------+
|                             FastAPI (App/api.py)                              |
|   - CORS Middleware (ports 5173, 3000, 8080)                                  |
|   - Pydantic v2 Request Validation (RecommendationRequest)                    |
|   - Standardized Error Envelope Dispatcher                                   |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                    Recommendation Engine (recommendation_engine.py)            |
|   - Route & Scenario Matcher (SUPPORTED_SCENARIOS)                            |
|   - Strategy Window Selector (STEP8J_CONTRACT_STRATEGY.csv)                   |
|   - Best Month Optimizer (Highest Strategy Score + Lowest Break-Even)         |
+-------------------------------------------------------------------------------+
            |                    |                     |                   |
            v                    v                     v                   v
+------------------+   +------------------+   +------------------+  +--------------------+
| Idle/Deadhead    |   | Vessel           |   | Port             |  | Commercial         |
| Engine           |   | Optimization     |   | Infrastructure   |  | Economics Engine   |
| (App/idle_       |   | Engine           |   | Engine           |  | (App/commercial_   |
| deadhead_engine) |   | (App/vessel_     |   | (App/port_infra) |  | economics_engine)  |
|                  |   | optimization)    |   |                  |  |                    |
+------------------+   +------------------+   +------------------+  +--------------------+
            |                    |                     |                   |
            +--------------------+---------------------+-------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                            Enriched JSON Response                             |
|   - Recommended Vessel: "Panamax" (Score: 100/100)                            |
|   - Optimal Month: "2025-12" (Signal: FAVORABLE ENTRY SIGNAL, Risk: LOW)      |
|   - Port Feasibility: PASS (LOA: +71m, Beam: +17.75m, Draft: +3.07m)         |
|   - Break-Even: $6.91/mt (Max Stressed: $9.47/mt)                             |
|   - Financial Status: "FINAL PROFIT BLOCKED" (Guardrails Active)              |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                      NauSaarthi Analytics Dashboard UI                        |
|   - Live KPIs, Recharts Timeline, Clearance Gauges, Locked Profit Badges      |
+-------------------------------------------------------------------------------+
```

---

## 2. Verified API Endpoints

| Method | Route | Description | Request Body | Response Codes |
|---|---|---|---|---|
| `GET` | `/` | API welcome, version info, endpoint directory | None | `200` |
| `GET` | `/health` | Live health monitoring | None | `200` |
| `GET` | `/scenarios` | Lists supported validated routes | None | `200` |
| `POST` | `/api/recommendation` | Primary integrated decision-support payload | `RecommendationRequest` | `200`, `400`, `422`, `500` |
| `POST` | `/api/vessel-optimization` | Vessel screening & ranking report | `RecommendationRequest` | `200`, `400`, `422`, `500` |
| `POST` | `/api/port-feasibility` | Port & berth constraint report | `RecommendationRequest` | `200`, `400`, `422`, `500` |
| `POST` | `/api/commercial-economics` | Commercial economics report | `RecommendationRequest` | `200`, `400`, `422`, `500` |

---

## 3. Request & Response Payload Contract

### Request Schema (`POST /api/recommendation`):
```json
{
  "cargo_type": "Coal",
  "cargo_tonnes": 80000,
  "origin": "Gladstone, Australia",
  "destination": "Dhamra, India",
  "contract_duration_months": 1
}
```

### Response Schema:
```json
{
  "status": "OK",
  "scenario_id": "GLADSTONE_DHAMRA_COAL",
  "inputs": {
    "cargo_type": "coal",
    "cargo_tonnes": 80000.0,
    "origin": "gladstone, australia",
    "destination": "dhamra, india",
    "contract_duration_months": 1
  },
  "recommended_vessel": "Panamax",
  "port_feasibility": "PASS",
  "best_month": "2025-12",
  "best_month_strategy_score": 100.0,
  "best_month_market_signal": "FAVORABLE ENTRY SIGNAL",
  "best_month_bunker_risk": "LOW",
  "selected_window": {
    "start": "2025-12",
    "end": "2025-12",
    "duration_months": 1,
    "duration_class": "SHORT-TERM",
    "strategy_score": 100.0
  },
  "break_even": {
    "average_usd_per_mt": 6.909223952606835,
    "maximum_stressed_usd_per_mt": 6.909223952606835
  },
  "risk": {
    "selected_window_risk": "LOW"
  },
  "commercial_data": {
    "rate_available": false,
    "final_profit_available": false,
    "final_tce_available": false,
    "financial_status": "FINAL PROFIT BLOCKED"
  },
  "recommendation": "CONSIDER PANAMAX CONTRACTING",
  "recommendation_reason": "Panamax passes the configured port screen and the selected contract window has a strong strategy score...",
  "data_quality": "DECISION SUPPORT",
  "cargo_status": "MATCHED",
  "cargo_note": "Cargo quantity matches the current validated scenario.",
  "idle_deadhead": { ... },
  "vessel_optimization": { ... },
  "port_infrastructure": { ... },
  "commercial_economics": { ... },
  "api_version": "1.0.0",
  "generated_at": "2026-09-01T15:04:59.418146+00:00",
  "disclaimer": "This output is DECISION SUPPORT only. It is NOT a guarantee of commercial profitability..."
}
```

---

## 4. Frontend Data Rules Summary

1. **Zero Fabrication:** Never invent port dues, freight rates, or idle days.
2. **Financial Guardrails:** When `financial_status` is `FINAL PROFIT BLOCKED`, render a locked padlock icon and explain data constraints.
3. **Draft Screening Scope:** Infeasible vessel status (e.g. Capesize benchmark 18.2m draft) applies strictly to the benchmark evaluated in Step 8E, not all vessels in the class.
4. **Preserved Backend Terminology:** All signals (`LOWER IDLE RISK`, `FAVORABLE ENTRY SIGNAL`, `SHORT-TERM`, `PASS`) are preserved verbatim.
