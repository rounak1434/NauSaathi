import { Clock, CheckCircle2, AlertTriangle, Calendar, Info } from 'lucide-react';
import type { CharteringWindowResult } from '../types';

interface Props {
  data: CharteringWindowResult;
}

export default function CharteringWindowCard({ data }: Props) {
  // Timeline markers
  const totalDays = data.timelineDays <= 7 ? Math.max(data.timelineDays, 7) : Math.max(data.timelineDays + 5, 30);
  const idealStartPct = ((data.idealWindowStart ?? 0) / totalDays) * 100;
  const idealEndPct = ((data.idealWindowEnd ?? data.timelineDays) / totalDays) * 100;

  const isInfeasible =
    data.action === 'INFEASIBLE' ||
    (Boolean(data.displayLabel) &&
      (data.displayLabel.toUpperCase().includes('NO FEASIBLE') ||
        data.displayLabel.toUpperCase().includes('INFEASIBLE')));

  const isBookNow =
    !isInfeasible &&
    (data.action === 'BOOK_NOW' ||
      (Boolean(data.displayLabel) && data.displayLabel.toUpperCase().includes('BOOK')));

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-5 sm:p-6 flex flex-col justify-between animate-fade-in animate-fade-in-delay-2 h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-[#1e3a5f] tracking-tight">
              CHARTERING WINDOW
            </h3>
            <p className="text-xs text-gray-400">
              Optimal market-entry window based on forward freight inflection.
            </p>
          </div>
          <Calendar className="w-5 h-5 text-gray-300" />
        </div>

        {/* Dominant Action Block */}
        <div
          className={`${
            isInfeasible
              ? 'bg-amber-50 border-amber-300'
              : isBookNow
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-[#f0f4ff]/90 border-[#d4dff7]'
          } border rounded-lg p-4 mb-4 flex items-center gap-3.5`}
        >
          <div
            className={`w-11 h-11 rounded-lg ${
              isInfeasible
                ? 'bg-amber-600'
                : isBookNow
                  ? 'bg-emerald-600'
                  : 'bg-[#1e3a5f]'
            } flex items-center justify-center flex-shrink-0 shadow-xs`}
          >
            {isInfeasible ? (
              <AlertTriangle className="w-5 h-5 text-white" />
            ) : isBookNow ? (
              <CheckCircle2 className="w-5 h-5 text-white" />
            ) : (
              <Clock className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <span
              className={`text-lg sm:text-xl font-extrabold tracking-tight ${
                isInfeasible
                  ? 'text-amber-900'
                  : isBookNow
                    ? 'text-emerald-800'
                    : 'text-[#1e3a5f]'
              }`}
            >
              {data.displayLabel}
            </span>
            {data.suggestedReason && (
              <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">
                {data.suggestedReason}
              </p>
            )}
          </div>
        </div>

        {/* 4-Item Analytical Parameters Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          {/* User Window */}
          <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
              User Window
            </span>
            <span className="text-xs font-bold text-gray-800 block truncate">
              {data.userWindow || 'Standard'}
            </span>
          </div>

          {/* Forecast Horizon */}
          <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
              Forecast Horizon
            </span>
            <span className="text-xs font-bold text-gray-800 block truncate">
              {data.forecastHorizon || 'Target Month'}
            </span>
          </div>

          {/* Timing Signal */}
          <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5 flex items-center justify-between">
              Timing Signal
              {data.scoreBreakdown && <Info className="w-2.5 h-2.5 opacity-40" />}
            </span>
            <span className="text-xs font-bold text-gray-800 block">
              {data.strategyScore !== undefined ? `${data.strategyScore} / 100` : 'N/A'}
            </span>
            <span className="text-[9px] text-gray-400 block mt-0.5 leading-none font-medium">
              Rule-Based Index
            </span>
          </div>

          {/* Risk Level */}
          <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
              Risk Level
            </span>
            <span className={`text-xs font-bold block ${
              data.risk === 'LOW' ? 'text-emerald-600' :
              data.risk === 'MODERATE' ? 'text-amber-700' :
              data.risk === 'HIGH' ? 'text-red-500' : 'text-gray-700'
            }`}>
              {data.risk || 'MODERATE'}
            </span>
          </div>
        </div>

        {/* Timing Formula Explanation */}
        {data.scoreBreakdown && (
          <div className="mb-4 bg-gray-50/80 rounded-lg p-2.5 border border-gray-100">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-0.5">
              <span>Decision Timing Formula</span>
              <span className="font-mono text-gray-400">{data.scoreBreakdown.methodology}</span>
            </div>
            <p className="text-[11px] text-gray-600 font-mono">
              {data.scoreBreakdown.formula}
            </p>
          </div>
        )}

        {/* Visual Timeline Bar */}
        <div>
          <div className="flex items-center justify-between text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
            <span>Execution Timeline</span>
            <span className="text-gray-500 font-normal">0 to {totalDays} days</span>
          </div>

          <div className="relative pt-1 pb-2">
            {/* Track */}
            <div className="h-2 bg-gray-100 rounded-full relative overflow-visible">
              {/* Recommended window highlight */}
              {!isInfeasible && (
                <div
                  className={`absolute top-0 h-full ${
                    isBookNow ? 'bg-emerald-500' : 'bg-[#1e3a5f]'
                  } rounded-full`}
                  style={{
                    left: `${idealStartPct}%`,
                    width: `${Math.max(idealEndPct - idealStartPct, 15)}%`,
                  }}
                />
              )}
            </div>

            {/* Labels */}
            <div className="flex justify-between text-[10px] text-gray-400 mt-1 font-medium">
              <span>Prompt (Day 0)</span>
              <span>Horizon ({totalDays}d)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
