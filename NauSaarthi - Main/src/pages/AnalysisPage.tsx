import { ArrowLeft, RotateCcw, MapPin, Package, Calendar } from 'lucide-react';
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

  return (
    <div className="w-full px-6 sm:px-10 lg:px-16 py-8">
      {/* Page header */}
      <div className="mb-8 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <div>
            <h1 className="text-xl font-bold text-[#1e3a5f]">Chartering Analysis</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Analysis based on your cargo, route and selected chartering window.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onModifyInputs}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-[#1e3a5f] bg-[#eef2ff] hover:bg-[#e0e8ff] rounded-lg transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Modify Inputs
            </button>
            <button
              onClick={onNewAnalysis}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-500 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              New Analysis
            </button>
          </div>
        </div>

        {/* Input summary */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-600">
            <Package className="w-3.5 h-3.5 text-gray-400" />
            <span className="font-semibold">{input.cargoQuantityMT.toLocaleString()} MT</span>
          </div>
          <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-600">
            <MapPin className="w-3.5 h-3.5 text-gray-400" />
            <span>
              {input.origin} <span className="text-gray-400 mx-0.5">→</span> {input.destination}
            </span>
          </div>
          <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-600">
            <Calendar className="w-3.5 h-3.5 text-gray-400" />
            <span>{windowLabel}</span>
          </div>
        </div>
      </div>

      {/* Analysis sections */}
      <div className="space-y-6">
        {/* Section 1: Freight Forecast */}
        <FreightForecastCard data={freightForecast} />

        {/* Section 2 + 3: Vessel and Timing side by side on desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <VesselRecommendationCard data={vesselRecommendation} />
          <CharteringWindowCard data={charteringWindow} />
        </div>

        {/* Section 4: Final Recommendation */}
        <FinalRecommendation data={recommendation} />
      </div>

      {/* Footer spacer */}
      <div className="h-12" />
    </div>
  );
}
