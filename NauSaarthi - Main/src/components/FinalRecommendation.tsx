import { CheckCircle2, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';
import type { Recommendation, DecisionFactor } from '../types';

interface Props {
  data: Recommendation;
}

export default function FinalRecommendation({ data }: Props) {
  const isInfeasible =
    data.verdict === 'NO_FEASIBLE_SINGLE_VESSEL' ||
    (Boolean(data.displayLabel) &&
      (data.displayLabel.toUpperCase().includes('NO FEASIBLE') ||
        data.displayLabel.toUpperCase().includes('INFEASIBLE')));

  const isBookNow =
    !isInfeasible &&
    (data.verdict === 'BOOK_NOW' ||
      (Boolean(data.displayLabel) && data.displayLabel.toUpperCase().includes('BOOK')));

  const isWait =
    !isInfeasible &&
    (data.verdict === 'WAIT' ||
      (Boolean(data.displayLabel) && data.displayLabel.toUpperCase().includes('WAIT')));

  const selectedConfig = isInfeasible
    ? {
        icon: AlertTriangle,
        accentBg: 'bg-amber-50/70',
        accentBorder: 'border-amber-300',
        accentText: 'text-amber-900',
        iconBg: 'bg-amber-600',
        statusBadge: 'bg-amber-100 text-amber-900 border-amber-200',
        dotColor: 'bg-amber-600',
      }
    : isBookNow
    ? {
        icon: CheckCircle2,
        accentBg: 'bg-emerald-50/70',
        accentBorder: 'border-emerald-300',
        accentText: 'text-emerald-900',
        iconBg: 'bg-emerald-600',
        statusBadge: 'bg-emerald-100 text-emerald-900 border-emerald-200',
        dotColor: 'bg-emerald-600',
      }
    : isWait
    ? {
        icon: Clock,
        accentBg: 'bg-amber-50/50',
        accentBorder: 'border-amber-300',
        accentText: 'text-amber-900',
        iconBg: 'bg-amber-500',
        statusBadge: 'bg-amber-100 text-amber-900 border-amber-200',
        dotColor: 'bg-amber-500',
      }
    : {
        icon: AlertTriangle,
        accentBg: 'bg-[#f0f4ff]',
        accentBorder: 'border-[#d4dff7]',
        accentText: 'text-[#1e3a5f]',
        iconBg: 'bg-[#1e3a5f]',
        statusBadge: 'bg-[#eef2ff] text-[#1e3a5f] border-[#d4dff7]',
        dotColor: 'bg-[#1e3a5f]',
      };

  const Icon = selectedConfig.icon;

  // Extract structured factors from data.decisionFactors if present
  const factorMap: Record<string, DecisionFactor> = {};
  if (data.decisionFactors) {
    for (const df of data.decisionFactors) {
      factorMap[df.factor] = df;
    }
  }

  // Parse title and subtitle
  const labelParts = data.displayLabel.split('-');
  const primaryVerdict = labelParts[0].trim();
  const secondaryDetail = labelParts.length > 1 ? labelParts.slice(1).join('-').trim() : '';

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-6 sm:p-7 animate-fade-in animate-fade-in-delay-3 w-full">
      <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-5">
        <div>
          <h3 className="text-sm font-bold text-[#1e3a5f] uppercase tracking-wider">
            NAUSAARTHI RECOMMENDATION
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Holistic commercial fixture guidance synthesizing market forecasts, port access, and voyage risk.
          </p>
        </div>
        <ShieldCheck className="w-5 h-5 text-[#1e3a5f]/40" />
      </div>

      {/* Hero Recommendation Banner */}
      <div
        className={`${selectedConfig.accentBg} ${selectedConfig.accentBorder} border-2 rounded-xl p-5 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4`}
      >
        <div className="flex items-start sm:items-center gap-4">
          <div
            className={`w-12 h-12 rounded-xl ${selectedConfig.iconBg} flex items-center justify-center flex-shrink-0 shadow-xs mt-1 sm:mt-0`}
          >
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className={`text-xl sm:text-2xl font-extrabold tracking-tight ${selectedConfig.accentText}`}>
                {primaryVerdict}
              </span>
              <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${selectedConfig.statusBadge}`}>
                {isBookNow ? 'EXECUTE SPOT FIXTURE' : isWait ? 'DEFER FOR LOWER FREIGHT' : 'OPERATIONAL CONSTRAINT'}
              </span>
            </div>
            {secondaryDetail && (
              <p className="text-sm font-bold text-gray-700 mt-0.5 tracking-tight">
                {secondaryDetail}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Decision-Factor Pipeline Chain */}
      <div className="mb-6">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
          Decision-Factor Chain
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* 1. Market */}
          <div className="bg-gray-50/80 rounded-lg p-3 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
              1. Market Freight
            </span>
            <span className="text-xs font-bold text-gray-900 block truncate">
              {factorMap['CURRENT_RATE'] ? factorMap['CURRENT_RATE'].value : 'Spot Market'} → {factorMap['FORECAST_RATE'] ? factorMap['FORECAST_RATE'].value : 'Forecast'}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5 truncate">
              {factorMap['FORECAST_TREND'] ? factorMap['FORECAST_TREND'].value : 'Forward Curve'}
            </span>
          </div>

          {/* 2. Vessel */}
          <div className="bg-gray-50/80 rounded-lg p-3 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
              2. Vessel Class
            </span>
            <span className="text-xs font-bold text-gray-900 block truncate">
              {factorMap['VESSEL_FEASIBILITY']?.status === 'PASS' || factorMap['VESSEL_FEASIBILITY']?.value === 'PASS' ? 'Optimal Payload' : 'Capacity Match'}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5 truncate">
              {factorMap['VESSEL_FEASIBILITY'] ? factorMap['VESSEL_FEASIBILITY'].detail : 'Single-voyage fit'}
            </span>
          </div>

          {/* 3. Port */}
          <div className="bg-gray-50/80 rounded-lg p-3 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
              3. Port Access
            </span>
            <span className="text-xs font-bold text-gray-900 block truncate">
              {factorMap['PORT_CONSTRAINTS'] ? factorMap['PORT_CONSTRAINTS'].value : 'Berth Check'}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5 truncate">
              {factorMap['PORT_CONSTRAINTS'] ? factorMap['PORT_CONSTRAINTS'].detail : 'Draft & LOA limits'}
            </span>
          </div>

          {/* 4. Timing */}
          <div className="bg-gray-50/80 rounded-lg p-3 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
              4. Fixture Timing
            </span>
            <span className="text-xs font-bold text-gray-900 block truncate">
              {isWait ? 'Target Forward Trough' : 'Immediate Spot Window'}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5 truncate">
              {factorMap['RISK_LEVEL'] ? factorMap['RISK_LEVEL'].detail : 'Decision window'}
            </span>
          </div>

          {/* 5. Verdict */}
          <div className={`rounded-lg p-3 border ${selectedConfig.accentBg} ${selectedConfig.accentBorder}`}>
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block mb-1">
              5. Final Action
            </span>
            <span className={`text-xs font-extrabold block truncate ${selectedConfig.accentText}`}>
              {primaryVerdict}
            </span>
            <span className="text-[11px] text-gray-600 block mt-0.5 truncate">
              Commercial Fixture Advisory
            </span>
          </div>
        </div>
      </div>

      {/* Why this recommendation? */}
      <div>
        <p className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
          Why this recommendation?
        </p>
        <ul className="space-y-2.5">
          {data.reasons.map((reason, i) => (
            <li key={i} className="flex items-start gap-2.5 text-xs sm:text-sm text-gray-700 leading-relaxed bg-gray-50/50 p-2.5 rounded-lg border border-gray-100">
              <span
                className={`mt-1.5 w-2 h-2 rounded-full ${selectedConfig.dotColor} flex-shrink-0`}
              />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
