import type {
  CargoRequirement,
  AnalysisResponse,
  CharteringWindowOption,
  FreightDataPoint,
  FreightForecast,
  MarketTrend,
  ConfidenceLevel,
  VesselClass,
  SuitabilityStatus,
  VesselSuitability,
  VesselRecommendation,
  TimingAction,
  CharteringWindowResult,
  RecommendationVerdict,
  Recommendation,
} from '../types';

// ─── Configuration ─────────────────────────────────────────────────────

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') ||
  'http://127.0.0.1:8000';

// ─── Helper Mappings ───────────────────────────────────────────────────

/**
 * Maps frontend chartering window selection to backend contract_duration_months:
 * - Within 7 Days  -> 1 month (prompt spot)
 * - Within 30 Days -> 1 month
 * - Within 60 Days -> 2 months
 * - Within 90 Days -> 3 months
 */
function mapWindowToDuration(window: CharteringWindowOption): number {
  switch (window) {
    case 'within_7_days':
      return 1;
    case 'within_30_days':
      return 1;
    case 'within_60_days':
      return 2;
    case 'within_90_days':
      return 3;
    case 'custom':
    default:
      return 1;
  }
}

// ─── Analysis Service ──────────────────────────────────────────────────

/**
 * Analyses chartering requirements by invoking the live FastAPI recommendation backend.
 * Endpoint: POST /api/recommendation
 */
export async function analyzeCharteringRequirement(
  input: CargoRequirement
): Promise<AnalysisResponse> {
  const isSevenDays = input.charteringWindow === 'within_7_days';
  const durationMonths = isSevenDays ? 0 : mapWindowToDuration(input.charteringWindow);

  const payload = {
    cargo_type: 'Coal',
    cargo_tonnes: input.cargoQuantityMT,
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
      `Unable to connect to SAIL backend at ${API_BASE_URL} (${msg}). Please verify FastAPI is running on http://127.0.0.1:8000.`
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

  // 1. Freight Forecast
  const fc = backend.forecast ?? {};
  const timeline = Array.isArray(fc.timeline) ? fc.timeline : [];

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

  const confRaw = String(fc.confidence || '').toUpperCase();
  let confidence: ConfidenceLevel = 'MEDIUM';
  if (confRaw.includes('HIGH')) {
    confidence = 'HIGH';
  } else if (confRaw.includes('LOW')) {
    confidence = 'LOW';
  }

  const chartData: FreightDataPoint[] = timeline.map(
    (pt: {
      date: string;
      estimated_freight_usd_pmt: number;
      is_forecast?: boolean;
    }) => {
      const d = new Date(pt.date + '-01');
      const label = isNaN(d.getTime())
        ? pt.date
        : d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      return {
        date: label,
        rate: Number(pt.estimated_freight_usd_pmt ?? 0),
        type: pt.is_forecast ? ('forecast' as const) : ('historical' as const),
      };
    }
  );

  const freightForecast: FreightForecast = {
    currentRatePerMT: Number(fc.current_rate ?? 0),
    expectedRatePerMT: Number(fc.expected_rate ?? 0),
    trend,
    confidence,
    chartData,
    currentRateDate: fc.current_rate_date,
    expectedRateDate: fc.expected_rate_date,
    currentRateDataStatus: fc.current_rate_data_status,
    expectedRateDataStatus: fc.expected_rate_data_status,
  };

  // 2. Vessel Recommendation
  const vesselData = backend.vessel ?? {};
  const recommendedClass = (vesselData.recommended_class || 'Panamax') as VesselClass;
  const operationalMode = vesselData.operational_mode;
  const comparisons = Array.isArray(vesselData.comparison)
    ? vesselData.comparison
    : [];

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
      status?: string;
    }) => {
      const isRec =
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
        v.operational_mode?.includes('Transshipment') ||
        v.operational_mode?.includes('Lighterage')
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
      };
    }
  );

  const vesselReason =
    operationalMode && operationalMode !== 'Direct Port Call'
      ? `${recommendedClass} (${operationalMode}): ${
          vesselData.recommendation_reason ||
          `Optimal fit for ${input.cargoQuantityMT.toLocaleString()} MT on the ${input.origin} → ${input.destination} route`
        }`
      : vesselData.recommendation_reason ||
        `Best fit for ${input.cargoQuantityMT.toLocaleString()} MT on the ${input.origin} → ${input.destination} route`;

  const vesselRecommendation: VesselRecommendation = {
    recommended: recommendedClass,
    reason: vesselReason,
    vessels,
    operationalMode,
  };

  // 3. Chartering Window
  const cw = backend.chartering_window ?? {};
  const cwActionRaw = String(cw.recommended_action || '').toUpperCase();
  let cwAction: TimingAction = 'CHARTER_WITHIN_RANGE';
  if (cwActionRaw.includes('WAIT')) {
    cwAction = 'WAIT';
  } else if (cwActionRaw.includes('BOOK')) {
    cwAction = 'BOOK_NOW';
  }

  const totalDays = isSevenDays ? 7 : (cw.duration_months || durationMonths) * 30;
  let idealStart = 0;
  let idealEnd = totalDays;
  if (isSevenDays) {
    idealStart = 0;
    idealEnd = 7;
  } else if (cwAction === 'WAIT') {
    idealStart = Math.round(totalDays * 0.4);
    idealEnd = totalDays;
  } else if (cwAction === 'BOOK_NOW') {
    idealStart = 0;
    idealEnd = Math.min(14, totalDays);
  }

  const actionHeadline = cw.recommended_action
    ? cw.recommended_action.split('(')[0].trim()
    : (cw.selected_window || 'Charter Window');

  const cwExplanation = `Strategy Score: ${cw.strategy_score ?? 100}/100 | Risk: ${
    cw.risk ?? 'LOW'
  } | Window: ${cw.selected_window ?? ''} (${cw.start ?? ''} to ${cw.end ?? ''}).`;

  const charteringWindow: CharteringWindowResult = {
    action: cwAction,
    displayLabel: actionHeadline,
    explanation: cwExplanation,
    timelineDays: totalDays,
    idealWindowStart: idealStart,
    idealWindowEnd: idealEnd,
    strategyScore: cw.strategy_score,
    risk: cw.risk,
  };

  // 4. Recommendation
  const rec = backend.recommendation ?? {};
  const recActionRaw = String(rec.action || '').toUpperCase();
  let verdict: RecommendationVerdict = 'CONSIDER_ALTERNATIVE_WINDOW';
  if (recActionRaw.includes('WAIT')) {
    verdict = 'WAIT';
  } else if (recActionRaw.includes('BOOK')) {
    verdict = 'BOOK_NOW';
  }

  const recommendation: Recommendation = {
    verdict,
    displayLabel: rec.headline || rec.action || 'Decision Support Recommendation',
    reasons: Array.isArray(rec.reasons) ? rec.reasons : [],
  };

  return {
    input,
    freightForecast,
    vesselRecommendation,
    charteringWindow,
    recommendation,
    economics: backend.economics,
    dataQuality: backend.data_quality,
    rawBackend: backend,
  };
}
