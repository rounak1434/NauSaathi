// ─── Cargo & Route Types ───────────────────────────────────────────────

export interface Port {
  name: string;
  country?: string;
}

export interface OriginOption {
  country: string;
  ports: Port[];
}

export interface DestinationPort {
  name: string;
  state?: string;
}

export type CharteringWindowOption =
  | 'within_7_days'
  | 'within_30_days'
  | 'within_60_days'
  | 'within_90_days'
  | 'custom';

export interface CargoRequirement {
  cargoQuantityMT: number;
  origin: string;
  destination: string;
  charteringWindow: CharteringWindowOption;
  cargoType?: string;
}

// ─── Freight Forecast Types ────────────────────────────────────────────

export type MarketTrend = 'RISING' | 'FALLING' | 'STABLE';
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface FreightDataPoint {
  date: string;
  rawDate?: string;
  rate: number;
  type: 'historical' | 'forecast';
}

export interface FreightForecast {
  currentRatePerMT: number;
  expectedRatePerMT: number;
  trend: MarketTrend;
  confidence: ConfidenceLevel;
  chartData: FreightDataPoint[];
  currentRateDate?: string;
  expectedRateDate?: string;
  currentRateDataStatus?: string;
  expectedRateDataStatus?: string;
}

// ─── Vessel Types ──────────────────────────────────────────────────────

export type VesselClass = 'Handysize' | 'Supramax' | 'Panamax' | 'Capesize' | 'No Single-Vessel Fit';
export type SuitabilityStatus = 'Suitable' | 'Not Suitable' | 'Recommended';

export interface VesselSuitability {
  vesselClass: VesselClass;
  cargoFit: SuitabilityStatus;
  portFit: SuitabilityStatus;
  routeFit: SuitabilityStatus;
  isRecommended: boolean;
  dwtRange?: string;
  loaRange?: string;
  beamRange?: string;
  draftRange?: string;
}

export interface VesselRecommendation {
  recommended: VesselClass;
  reason: string;
  vessels: VesselSuitability[];
  operationalMode?: string;
}

// ─── Chartering Window Types ───────────────────────────────────────────

export type TimingAction = 'BOOK_NOW' | 'WAIT' | 'CHARTER_WITHIN_RANGE' | 'INFEASIBLE';

export interface CharteringWindowResult {
  action: TimingAction;
  displayLabel: string;
  explanation: string;
  timelineDays: number;
  idealWindowStart?: number;
  idealWindowEnd?: number;
  strategyScore?: number;
  risk?: string;
}

// ─── Final Recommendation ──────────────────────────────────────────────

export type RecommendationVerdict =
  | 'BOOK_NOW'
  | 'WAIT'
  | 'CONSIDER_ALTERNATIVE_WINDOW'
  | 'NO_FEASIBLE_SINGLE_VESSEL';

export interface Recommendation {
  verdict: RecommendationVerdict;
  displayLabel: string;
  reasons: string[];
}

// ─── Combined Analysis Response ────────────────────────────────────────

export interface AnalysisResponse {
  input: CargoRequirement;
  freightForecast: FreightForecast;
  vesselRecommendation: VesselRecommendation;
  charteringWindow: CharteringWindowResult;
  recommendation: Recommendation;
  economics?: {
    break_even_rate: number;
    stressed_break_even_rate: number;
    distance_nm: number;
    voyage_days: number;
    bunker_cost_usd: number;
    bunker_price_usd_per_mt: number;
    bunker_observation_date?: string;
    profit: number | null;
    tce: number | null;
    financial_status: string;
    provenance: string;
  };
  dataQuality?: {
    overall_status: string;
    route_type?: string;
    verified: string[];
    derived: string[];
    scenario_assumptions: string[];
    missing: string[];
  };
  rawBackend?: Record<string, unknown>;
}
