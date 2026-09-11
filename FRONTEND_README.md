# NauSaarthi — Maritime Decision-Support Platform Documentation

> **Product Name:** NauSaarthi — Smart Maritime Decision Support  
> **Subtitle / Tagline:** Intelligent Decision Support for Bulk Cargo Procurement & Vessel Chartering  
> **Frontend Architecture:** React + Vite + Tailwind CSS + Lucide Icons + Recharts  
> **Backend Service:** Existing FastAPI REST decision-support backend (App/api.py)  
> **Hackathon Prototype:** Smart India Hackathon (SIH 2026)

---

## 1. Quick Start

### Prerequisites
- Node.js (v18+)
- Python (v3.10+) with FastAPI, Uvicorn, Pandas, and Scikit-Learn

### Step 1: Start the Backend Service
From the root directory:
```bash
cd "App"
python -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```
Verify the backend is live at `http://127.0.0.1:8000/docs` (OpenAPI Swagger) and `http://127.0.0.1:8000/health`.

### Step 2: Start the NauSaarthi Frontend
In a separate terminal, from the root directory:
```bash
cd "frontend"
npm install
npm run dev
```
Open `http://127.0.0.1:5173/` in your browser.

---

## 2. Environment Configuration

The NauSaarthi frontend reads the API base URL from `.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```
When deploying in production or Docker, set `VITE_API_BASE_URL` to your backend's domain.

---

## 3. Component Architecture

```text
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Header.jsx             # NauSaarthi branding, live API status pill, active route indicator
│   │   ├── Sidebar.jsx            # Smooth section navigation
│   │   └── Footer.jsx             # Data-integrity notice & disclaimer
│   ├── scenario/
│   │   └── ScenarioForm.jsx       # Dynamic cargo & voyage parameter configurator
│   ├── dashboard/
│   │   ├── ExecutiveSummary.jsx   # Hero banner, recommendation, strategy score, KPI tiles
│   │   ├── MarketIntelligence.jsx # 12-month forward predictive forecast chart & timeline table
│   │   ├── VesselAnalysis.jsx     # Panamax vs Capesize physical screening & ranking
│   │   ├── PortFeasibility.jsx    # Gladstone & Dhamra berth clearances (LOA/Beam/Draft)
│   │   ├── ContractStrategy.jsx   # Selected charter window & duration comparison (1M, 3M, 6M)
│   │   ├── RiskAnalysis.jsx       # Sensitivity stress-testing matrix (+10%/+20% perturbations)
│   │   ├── IdleDeadhead.jsx       # Repositioning recommendation & idle risk signals
│   │   ├── CommercialEconomics.jsx# Financial guardrail banner, partial break-even, locked profit
│   │   └── DataQualityAudit.jsx   # 7-class data governance & transparency framework
│   └── common/
│       ├── StatusBadge.jsx        # Standardized badge (PASS, FAIL, LOCKED, etc.)
│       ├── MetricCard.jsx         # KPI tile with tooltip and data classification
│       ├── LoadingSkeleton.jsx    # Pulse skeleton loaders
│       ├── ErrorBanner.jsx        # Structured error notifications (400, 422, 500, network)
│       └── Tooltip.jsx            # Explanatory tooltips for maritime terminology
├── services/
│   └── api.js                     # Centralized API service connecting to existing FastAPI backend
├── utils/
│   ├── formatters.js              # Currency, tonnes, days, and distance formatters
│   └── constants.js               # Tooltips, data classification colors, default scenario
├── App.jsx                        # Main application container
├── index.css                      # Maritime dark theme styles & glassmorphism
└── main.jsx                       # React root entry point
```

---

## 4. Key UI & Decision Support Features

1. **NauSaarthi Executive Summary Banner:** Prominently presents the top recommendation (`CONSIDER PANAMAX CONTRACTING`), Strategy Score (`100/100`), Best Month (`2025-12`), and Port Clearance (`PASS`).
2. **Interactive Forecast Chart:** Switch between **Break-Even Freight ($/mt)**, **VLSFO Fuel Price ($/t)**, and **Total Bunker Cost ($)** over the 12-month forward horizon.
3. **Physical Port Clearance Gauges:** Visual margin clearance for Length Overall (+71.0m), Beam (+17.75m), and Draft (+3.07m) at Dhamra, India.
4. **Data Integrity Guardrails:** When commercial freight rates are unavailable in the pipeline, **Net Profit** and **TCE** are strictly **LOCKED** with an explanatory badge (never default to misleading $0).
5. **One-Click Demo Mode:** Quick-fill button loads the validated `Coal 80,000 MT (Gladstone -> Dhamra, 1 Month)` scenario.
6. **Graceful Error Handling:** Unsupported routes (e.g. `Singapore -> Rotterdam`) display clear `UNSUPPORTED_ROUTE` guidance without crashing.

---

## 5. Troubleshooting

- **"API DISCONNECTED" in Header / Network Failure:** Ensure the FastAPI server is running on `http://127.0.0.1:8000`.
- **CORS Errors in Console:** Backend `App/api.py` includes `http://localhost:5173` and `http://127.0.0.1:5173` in `CORS_ORIGINS`. Ensure you access the frontend using one of these hosts.
- **Port Conflict:** If port `5173` is busy, Vite will pick `5174`. Add `http://127.0.0.1:5174` to `CORS_ORIGINS` in `App/api.py` if needed.
