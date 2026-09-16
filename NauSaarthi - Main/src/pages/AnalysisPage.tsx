import { ArrowLeft, RotateCcw, MapPin, Package, Calendar, Ship, TrendingUp } from 'lucide-react';
import FreightForecastCard from '../components/FreightForecast';
import VesselRecommendationCard from '../components/VesselRecommendation';
import CharteringWindowCard from '../components/CharteringWindow';
import FinalRecommendation from '../components/FinalRecommendation';
import type { AnalysisResponse } from '../types';
import { CHARTERING_WINDOW_LABELS } from '../data/locations';

interface Props {
  analysis: AnalysisResponse;
  onModifyInputs: () => void;
  onNewAnalysis: () => void;
}

export default function AnalysisPage({ analysis, onModifyInputs, onNewAnalysis }: Props) {
  const { input, freightForecast, vesselRecommendation, charteringWindow, recommendation } =
    analysis;

  const windowLabel =
    CHARTERING_WINDOW_LABELS[input.charteringWindow] ?? input.charteringWindow;

  // Status flags
  const isInfeasible =
    recommendation.verdict === 'NO_FEASIBLE_SINGLE_VESSEL' ||
    recommendation.displayLabel.toUpperCase().includes('NO FEASIBLE') ||
    recommendation.displayLabel.toUpperCase().includes('INFEASIBLE');

  const isBookNow =
    !isInfeasible &&
    (recommendation.verdict === 'BOOK_NOW' ||
      recommendation.displayLabel.toUpperCase().includes('BOOK'));

  const isWait =
    !isInfeasible &&
    (recommendation.verdict === 'WAIT' ||
      recommendation.displayLabel.toUpperCase().includes('WAIT'));

  // Top bar styling & text extraction
  const recActionClean = isInfeasible
    ? 'NO FEASIBLE VESSEL'
    : isBookNow
      ? 'BOOK NOW'
      : isWait
        ? 'WAIT / DEFER'
        : recommendation.displayLabel;

  const recSubtext = isInfeasible
    ? 'Single-vessel constraint'
    : recommendation.displayLabel.includes('-')
      ? recommendation.displayLabel.split('-')[1].trim()
      : charteringWindow.action === 'WAIT' && charteringWindow.forecastHorizon
        ? `Target ${charteringWindow.forecastHorizon}`
        : 'Execute prompt fixture';

  const recDotColor = isInfeasible
    ? 'bg-amber-600'
    : isBookNow
      ? 'bg-emerald-600'
      : 'bg-amber-500';

  const recTextColor = isInfeasible
    ? 'text-amber-900'
    : isBookNow
      ? 'text-emerald-700'
      : 'text-amber-800';

  const vesselModeLabel = vesselRecommendation.operationalMode === 'ALTERNATIVE_DISCHARGE'
    ? 'Offshore Lighterage'
    : vesselRecommendation.operationalMode === 'DIRECT_PORT_CALL'
      ? 'Direct Port Call'
      : vesselRecommendation.operationalMode === 'INFEASIBLE'
        ? 'Berth Infeasible'
        : vesselRecommendation.operationalMode || 'Standard Voyage';

  const rateDeltaPct = freightForecast.rateDeltaPct;
  const deltaColorClass = rateDeltaPct < -1
    ? 'text-emerald-600'
    : rateDeltaPct > 1
      ? 'text-amber-600'
      : 'text-gray-500';

  const rateDeltaText = rateDeltaPct < -0.1
    ? `↓ ${Math.abs(rateDeltaPct).toFixed(1)}% below current`
    : rateDeltaPct > 0.1
      ? `↑ ${rateDeltaPct.toFixed(1)}% above current`
      : 'Broadly stable';

  const riskBadgeStyle = charteringWindow.risk === 'LOW'
    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
    : charteringWindow.risk === 'HIGH' || isInfeasible
      ? 'bg-red-50 text-red-700 border border-red-200'
      : 'bg-amber-50 text-amber-700 border border-amber-200';

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-5">
      {/* Top Header & Context Bar */}
      <div className="mb-5 animate-fade-in">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pb-3 border-b border-gray-200/80">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#1e3a5f] tracking-tight">
              Chartering Analysis &amp; Decision Support
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Automated freight curve trajectory, hydrographic port constraints, and fixture timing intelligence.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={onModifyInputs}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs sm:text-sm font-semibold text-[#1e3a5f] bg-[#eef2ff] hover:bg-[#e0e8ff] rounded-lg transition-colors cursor-pointer border border-[#d4dff7]"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Modify Inputs
            </button>
            <button
              onClick={onNewAnalysis}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs sm:text-sm font-medium text-gray-600 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              New Analysis
            </button>
          </div>
        </div>

        {/* Scenario metadata chips */}
        <div className="flex flex-wrap items-center gap-2.5 pt-3">
          <div className="flex items-center gap-1.5 bg-white border border-gray-200/90 rounded-md px-3 py-1 text-xs text-gray-700 font-medium shadow-2xs">
            <Package className="w-3.5 h-3.5 text-[#1e3a5f]" />
            <span><strong className="font-bold">{input.cargoQuantityMT.toLocaleString()} MT</strong> Coal</span>
          </div>
          <div className="flex items-center gap-1.5 bg-white border border-gray-200/90 rounded-md px-3 py-1 text-xs text-gray-700 font-medium shadow-2xs">
            <MapPin className="w-3.5 h-3.5 text-[#1e3a5f]" />
            <span>{input.origin} <span className="text-gray-400 mx-1">→</span> {input.destination}</span>
          </div>
          <div className="flex items-center gap-1.5 bg-white border border-gray-200/90 rounded-md px-3 py-1 text-xs text-gray-700 font-medium shadow-2xs">
            <Calendar className="w-3.5 h-3.5 text-[#1e3a5f]" />
            <span>Planning Horizon: <strong className="font-semibold text-gray-900">{windowLabel}</strong></span>
          </div>
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="space-y-5">
        {/* 1. TOP RECOMMENDATION BAR (Compact Decision Cockpit) */}
        <div className="w-full bg-white rounded-xl border border-gray-200/90 shadow-xs p-4 sm:p-5 animate-fade-in">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 divide-y sm:divide-y-0 sm:divide-x divide-gray-100">
            {/* Recommendation */}
            <div className="flex flex-col pr-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
                Recommendation
              </span>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${recDotColor} flex-shrink-0`} />
                <span className={`text-base sm:text-lg font-bold tracking-tight ${recTextColor}`}>
                  {recActionClean}
                </span>
              </div>
              <span className="text-xs text-gray-500 mt-0.5 font-medium truncate">
                {recSubtext}
              </span>
            </div>

            {/* Recommended Vessel */}
            <div className="flex flex-col sm:px-4 pt-3 sm:pt-0">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
                Recommended Vessel
              </span>
              <div className="flex items-center gap-1.5">
                <Ship className="w-4 h-4 text-[#1e3a5f] flex-shrink-0" />
                <span className="text-base sm:text-lg font-bold text-gray-900 tracking-tight">
                  {vesselRecommendation.recommended}
                </span>
              </div>
              <span className="text-xs text-gray-500 mt-0.5">
                {vesselModeLabel}
              </span>
            </div>

            {/* Freight Trajectory */}
            <div className="flex flex-col sm:px-4 pt-3 sm:pt-0">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
                Freight Trajectory
              </span>
              <div className="flex items-center gap-1.5 flex-wrap">
                <TrendingUp className="w-4 h-4 text-[#1e3a5f] flex-shrink-0" />
                <span className="text-base sm:text-lg font-bold text-gray-900 tracking-tight">
                  ${freightForecast.currentRatePerMT.toFixed(2)} → ${freightForecast.expectedRatePerMT.toFixed(2)}
                </span>
                <span className="text-xs text-gray-400">/MT</span>
              </div>
              <span className={`text-xs font-semibold mt-0.5 ${deltaColorClass}`}>
                {rateDeltaText}
              </span>
            </div>

            {/* Risk & Timing Signal */}
            <div className="flex flex-col sm:pl-4 pt-3 sm:pt-0">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
                Risk &amp; Timing Signal
              </span>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-2 py-0.5 text-xs font-bold rounded ${riskBadgeStyle}`}>
                  {charteringWindow.risk || 'MODERATE'} RISK
                </span>
                {charteringWindow.strategyScore !== undefined && (
                  <span className="text-xs font-bold text-gray-700">
                    Index: {charteringWindow.strategyScore}/100
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-400 mt-0.5 font-medium">
                Rule-Based Timing Index
              </span>
            </div>
          </div>
        </div>

        {/* 2. FREIGHT PRICE FORECAST (Full-Width Card) */}
        <div className="w-full">
          <FreightForecastCard data={freightForecast} />
        </div>

        {/* 3. LOWER GRID: Vessel Recommendation & Chartering Window (Side-by-Side on Desktop) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
          <VesselRecommendationCard data={vesselRecommendation} />
          <CharteringWindowCard data={charteringWindow} />
        </div>

        {/* 4. FINAL HERO RECOMMENDATION (Full-Width Card) */}
        <div className="w-full">
          <FinalRecommendation data={recommendation} />
        </div>
      </div>

      {/* Footer padding */}
      <div className="h-10" />
    </div>
  );
}
