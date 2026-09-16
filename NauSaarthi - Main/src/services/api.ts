import type {
  CargoRequirement,
  AnalysisResponse,
  CharteringWindowOption,
  FreightDataPoint,
  FreightForecast,
  MarketTrend,
  ForecastSignalLevel,
  ForecastSignal,
  VesselClass,
  SuitabilityStatus,
  VesselSuitability,
  VesselRecommendation,
  TimingAction,
  CharteringWindowResult,
  RecommendationVerdict,
  Recommendation,
  DecisionFactor,
} from '../types';

// ─── Configuration ─────────────────────────────────────────────────────

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') ||
  'http://127.0.0.1:8000';

let warmedUp = false;

/**
 * Asynchronously pre-warms the backend on initial application mount.
 * Triggers Render / backend container wake-up without blocking homepage render.
 */
export function prewarmBackend(): void {
  if (warmedUp) return;
  warmedUp = true;
  fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  }).catch(() => {
    // Non-blocking, silent catch: warm-up failure must never disrupt the user experience
  });
}

// ─── Helper Mappings ───────────────────────────────────────────────────

/**
 * Maps frontend chartering window selection to backend contract_duration_months:
 * - Within 7 Days  -> 1 month (prompt spot)
 * - Within 30 Days -> 1 month
 * - Within 60 Days -> 2 months
 * - Within 90 Days -> 3 months
 */
const CONTRACT_DURATION_MONTHS: Record<CharteringWindowOption, number> = {
  within_7_days: 1,
  within_30_days: 1,
  within_60_days: 2,
  within_90_days: 3,
  custom: 1,
};

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/**
 * Deterministically formats YYYY-MM into a display label (e.g. "Sep 26")
 * without being susceptible to browser UTC timezone offset shifts.
 */
function formatMonthLabel(dateStr: string): string {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length >= 2) {
    const year = parts[0].slice(-2);
    const monthNum = parseInt(parts[1], 10);
    if (monthNum >= 1 && monthNum <= 12) {
      return `${MONTH_NAMES[monthNum - 1]} ${year}`;
    }
  }
  return dateStr;
}

// ─── Analysis Service ──────────────────────────────────────────────────

/**
 * Analyses chartering requirements by invoking the live FastAPI recommendation backend.
 * Endpoint: POST /api/recommendation
 */
export async function analyzeCharteringRequirement(
  input: CargoRequirement
): Promise<AnalysisResponse> {
  const durationMonths =
    CONTRACT_DURATION_MONTHS[input.charteringWindow] ?? 1;
  const isSevenDays = input.charteringWindow === 'within_7_days';

  const payload = {
    cargo_type: input.cargoType || 'Coal',
    cargo_tonnes: Number(input.cargoQuantityMT),
    origin: input.origin,
    destination: input.destination,
    contract_duration_months: durationMonths,
    chartering_window: input.charteringWindow,
  };

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/recommendation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (netErr: unknown) {
    const msg = netErr instanceof Error ? netErr.message : String(netErr);
    throw new Error(
      `Unable to connect to NauSaarthi backend at ${API_BASE_URL} (${msg}). Please verify FastAPI is running on http://127.0.0.1:8000.`
    );
  }

  if (!response.ok) {
    let errorDetail = `Backend HTTP error ${response.status} (${response.statusText})`;
    try {
      const errJson = await response.json();
      if (errJson.message) {
        errorDetail = errJson.message;
      } else if (errJson.detail) {
        errorDetail =
          typeof errJson.detail === 'string'
            ? errJson.detail
            : JSON.stringify(errJson.detail);
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  const backend = await response.json();

  if (!backend || typeof backend !== 'object') {
    throw new Error('Malformed backend response: root payload is invalid.');
  }

  // 1. Freight Forecast validation & mapping
  if (
    !backend.forecast ||
    !Array.isArray(backend.forecast.timeline) ||
    backend.forecast.timeline.length === 0
  ) {
    throw new Error('Backend response is missing required freight forecast timeline data.');
  }

  const fc = backend.forecast;
  if (typeof fc.current_rate !== 'number' || isNaN(fc.current_rate)) {
    throw new Error('Backend response is missing a valid current_rate in forecast.');
  }
  if (typeof fc.expected_rate !== 'number' || isNaN(fc.expected_rate)) {
    throw new Error('Backend response is missing a valid expected_rate in forecast.');
  }

  const timeline = fc.timeline;
  // Chart data mapping: 100% data-driven binding from backend forecast timeline.
  // Each point corresponds directly to the backend's Baltic benchmark (BCI/BPI)
  // and bunker calibrated freight rate without any synthetic scaling or interpolation.
  const chartData: FreightDataPoint[] = timeline.map(
    (pt: {
      date: string;
      estimated_freight_usd_pmt: number;
      is_forecast?: boolean;
    }) => ({
      date: formatMonthLabel(pt.date),
      rawDate: pt.date,
      rate: Number(pt.estimated_freight_usd_pmt),
      type: pt.is_forecast ? ('forecast' as const) : ('historical' as const),
    })
  );

  const trendRaw = String(fc.market_trend || '').toUpperCase();
  let trend: MarketTrend = 'STABLE';
  if (
    trendRaw.includes('DECLINING') ||
    trendRaw.includes('FALLING') ||
    trendRaw.includes('FAVORABLE') ||
    trendRaw.includes('LOW')
  ) {
    trend = 'FALLING';
  } else if (
    trendRaw.includes('RISING') ||
    trendRaw.includes('HIGH') ||
    trendRaw.includes('UP')
  ) {
    trend = 'RISING';
  }

  // Map forecast signal from backend (replaces old HIGH/MEDIUM/LOW confidence)
  let forecastSignal: ForecastSignal | null = null;
  let forecastSignalLabel: ForecastSignalLevel = 'Moderate';
  if (fc.forecast_signal && typeof fc.forecast_signal === 'object') {
    forecastSignal = fc.forecast_signal as ForecastSignal;
    forecastSignalLabel = forecastSignal.signal || 'Moderate';
  } else {
    // Backward compat: map old string-based confidence
    const confRaw = String(fc.confidence || '').toLowerCase();
    if (confRaw.includes('strong') || confRaw.includes('high')) {
      forecastSignalLabel = 'Strong';
    } else if (confRaw.includes('weak') || confRaw.includes('low')) {
      forecastSignalLabel = 'Weak';
    }
  }

  // Compute rate delta percentage
  const rateDeltaPct = fc.current_rate > 0
    ? ((fc.expected_rate - fc.current_rate) / fc.current_rate) * 100
    : 0;

  const freightForecast: FreightForecast = {
    currentRatePerMT: Number(fc.current_rate),
    expectedRatePerMT: Number(fc.expected_rate),
    trend,
    forecastSignal,
    forecastSignalLabel,
    chartData,
    currentRateDate: fc.current_rate_date,
    expectedRateDate: fc.expected_rate_date,
    currentRateDataStatus: fc.current_rate_data_status,
    expectedRateDataStatus: fc.expected_rate_data_status,
    rateDeltaPct: Math.round(rateDeltaPct * 10) / 10,
    expectedRateHorizon: fc.expected_rate_horizon,
  };

  // 2. Vessel Recommendation validation & mapping
  if (!backend.vessel || !backend.vessel.recommended_class) {
    throw new Error('Backend response is missing required vessel recommendation data (recommended_class).');
  }

  const vesselData = backend.vessel;
  const recommendedClass = vesselData.recommended_class as VesselClass;
  const operationalMode = vesselData.operational_mode;
  const isSingleVesselInfeasible =
    recommendedClass === 'No Single-Vessel Fit' ||
    operationalMode === 'INFEASIBLE' ||
    String(backend.recommendation?.action || '').toUpperCase().includes('NO FEASIBLE') ||
    String(backend.recommendation?.headline || '').toUpperCase().includes('NO FEASIBLE') ||
    String(backend.chartering_window?.decision_action || '').toUpperCase() === 'INFEASIBLE' ||
    String(backend.chartering_window?.recommended_action || '').toUpperCase().includes('NO FEASIBLE') ||
    String(backend.chartering_window?.recommended_action || '').toUpperCase().includes('INFEASIBLE');

  const comparisons = Array.isArray(vesselData.comparison) ? vesselData.comparison : [];

  const vessels: VesselSuitability[] = comparisons.map(
    (v: {
      vessel_type: string;
      dwt_tonnes?: number;
      loa_m?: number;
      beam_m?: number;
      draft_m?: number;
      cargo_fit?: string;
      port_fit?: string;
      route_fit?: string;
      port_feasible?: boolean;
      operational_mode?: string;
      port_reason?: string;
      status?: string;
    }) => {
      const isRec =
        !isSingleVesselInfeasible &&
        v.vessel_type?.toLowerCase() === recommendedClass.toLowerCase();

      let cargoFit: SuitabilityStatus = 'Not Suitable';
      if (isRec) {
        cargoFit = 'Recommended';
      } else if (
        v.cargo_fit?.toLowerCase() === 'optimal' ||
        v.cargo_fit?.toLowerCase() === 'suitable'
      ) {
        cargoFit = 'Suitable';
      }

      let portFit: SuitabilityStatus = 'Not Suitable';
      if (isRec) {
        portFit = 'Recommended';
      } else if (
        v.port_feasible ||
        v.port_fit?.toLowerCase() === 'pass' ||
        v.operational_mode?.toLowerCase().includes('alternative') ||
        v.operational_mode?.toLowerCase().includes('transshipment') ||
        v.operational_mode?.toLowerCase().includes('lighterage')
      ) {
        portFit = 'Suitable';
      }

      let routeFit: SuitabilityStatus = 'Not Suitable';
      if (isRec) {
        routeFit = 'Recommended';
      } else if (v.route_fit) {
        routeFit = 'Suitable';
      }

      return {
        vesselClass: v.vessel_type as VesselClass,
        cargoFit,
        portFit,
        routeFit,
        isRecommended: isRec,
        dwtRange: v.dwt_tonnes ? `${v.dwt_tonnes.toLocaleString()} DWT` : undefined,
        loaRange: v.loa_m ? `${v.loa_m} m` : undefined,
        beamRange: v.beam_m ? `${v.beam_m} m` : undefined,
        draftRange: v.draft_m ? `${v.draft_m} m` : undefined,
        portReason: v.port_reason || undefined,
        operationalMode: v.operational_mode || undefined,
      };
    }
  );

  const vesselReason =
    vesselData.recommendation_reason ||
    (operationalMode && operationalMode !== 'DIRECT_PORT_CALL'
      ? `${recommendedClass} (${operationalMode})`
      : `${recommendedClass}`);

  const vesselRecommendation: VesselRecommendation = {
    recommended: recommendedClass,
    reason: vesselReason,
    vessels,
    operationalMode,
  };

  // 3. Chartering Window validation & mapping
  if (!backend.chartering_window) {
    throw new Error('Backend response is missing required chartering_window evaluation.');
  }

  const cw = backend.chartering_window;
  const cwActionRaw = String(cw.recommended_action || '').toUpperCase();
  let cwAction: TimingAction = 'CHARTER_WITHIN_RANGE';
  if (isSingleVesselInfeasible || cw.decision_action === 'INFEASIBLE') {
    cwAction = 'INFEASIBLE';
  } else if (cw.decision_action === 'WAIT' || cwActionRaw.includes('WAIT')) {
    cwAction = 'WAIT';
  } else if (cw.decision_action === 'BOOK NOW' || cwActionRaw.includes('BOOK')) {
    cwAction = 'BOOK_NOW';
  }

  const totalDays = isSevenDays ? 7 : (cw.duration_months || durationMonths) * 30;
  let idealStart: number | undefined = 0;
  let idealEnd: number | undefined = totalDays;
  if (isSingleVesselInfeasible) {
    idealStart = undefined;
    idealEnd = undefined;
  } else if (isSevenDays) {
    idealStart = 0;
    idealEnd = 7;
  } else if (cwAction === 'WAIT') {
    idealStart = Math.round(totalDays * 0.4);
    idealEnd = totalDays;
  } else if (cwAction === 'BOOK_NOW') {
    idealStart = 0;
    idealEnd = Math.min(14, totalDays);
  }

  const actionHeadline = isSingleVesselInfeasible
    ? 'NO FEASIBLE CHARTERING WINDOW'
    : cw.recommended_action
      ? cw.recommended_action.split('(')[0].trim()
      : (cw.selected_window || 'Charter Window');

  const cwExplanation = isSingleVesselInfeasible
    ? (cw.explanation ||
       'Single-vessel chartering is infeasible for the selected cargo and port constraints.')
    : (cw.explanation ||
       `Timing Signal: ${cw.strategy_score}/100 (Rule-Based Index) | Risk: ${cw.risk} | Window: ${cw.selected_window} (${cw.start} to ${cw.end}).`);

  // Build suggested reason from chartering window data
  let suggestedReason = '';
  if (cwAction === 'WAIT' && cw.min_forecast_month) {
    suggestedReason = `Forecast indicates lower rates in ${cw.min_forecast_month} (${Math.abs(cw.min_delta_pct || 0).toFixed(1)}% below current)`;
  } else if (cwAction === 'BOOK_NOW' && cw.max_delta_pct >= 1.5) {
    suggestedReason = `Forecast indicates rising rates (+${(cw.max_delta_pct || 0).toFixed(1)}% within window)`;
  } else if (cwAction === 'BOOK_NOW') {
    suggestedReason = 'Rates broadly stable within window — no timing advantage from deferral';
  }

  const charteringWindow: CharteringWindowResult = {
    action: cwAction,
    displayLabel: actionHeadline,
    explanation: cwExplanation,
    timelineDays: totalDays,
    idealWindowStart: idealStart,
    idealWindowEnd: idealEnd,
    strategyScore: isSingleVesselInfeasible ? undefined : cw.strategy_score,
    risk: isSingleVesselInfeasible ? 'HIGH' : cw.risk,
    scoreBreakdown: cw.score_breakdown || undefined,
    userWindow: cw.selected_window,
    forecastHorizon: cw.end ? formatMonthLabel(cw.end) : undefined,
    suggestedReason,
  };

  // 4. Recommendation validation & mapping
  if (!backend.recommendation) {
    throw new Error('Backend response is missing required recommendation payload.');
  }

  const rec = backend.recommendation;
  const recActionRaw = String(rec.action || '').toUpperCase();
  let verdict: RecommendationVerdict = 'CONSIDER_ALTERNATIVE_WINDOW';
  if (isSingleVesselInfeasible) {
    verdict = 'NO_FEASIBLE_SINGLE_VESSEL';
  } else if (cwAction === 'WAIT' || recActionRaw.includes('WAIT')) {
    verdict = 'WAIT';
  } else if (cwAction === 'BOOK_NOW' || recActionRaw.includes('BOOK')) {
    verdict = 'BOOK_NOW';
  }

  // Map decision factors from backend
  const decisionFactors: DecisionFactor[] = Array.isArray(backend.decision_factors)
    ? backend.decision_factors.map((df: { factor: string; value: string; status: string; detail: string }) => ({
        factor: df.factor,
        value: df.value,
        status: df.status,
        detail: df.detail,
      }))
    : [];

  const recommendation: Recommendation = {
    verdict,
    displayLabel: rec.headline || rec.action || 'Decision Support Recommendation',
    reasons: Array.isArray(rec.reasons) ? rec.reasons : [],
    decisionFactors,
    decisionChain: backend.decision_chain || '',
  };

  return {
    input,
    freightForecast,
    vesselRecommendation,
    charteringWindow,
    recommendation,
    economics: backend.economics,
    modelValidation: backend.model_validation,
    dataQuality: backend.data_quality,
    rawBackend: backend,
  };
}
