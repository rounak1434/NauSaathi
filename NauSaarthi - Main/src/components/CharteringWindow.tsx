import { Clock, ArrowRight, CheckCircle2 } from 'lucide-react';
import type { CharteringWindowResult } from '../types';

interface Props {
  data: CharteringWindowResult;
}

export default function CharteringWindowCard({ data }: Props) {
  // Timeline markers
  const totalDays = data.timelineDays <= 7 ? Math.max(data.timelineDays, 7) : Math.max(data.timelineDays + 5, 30);
  const todayPct = 0;
  const idealStartPct = ((data.idealWindowStart ?? 0) / totalDays) * 100;
  const idealEndPct = ((data.idealWindowEnd ?? data.timelineDays) / totalDays) * 100;

  const isBookNow =
    data.action === 'BOOK_NOW' ||
    (Boolean(data.displayLabel) && data.displayLabel.toUpperCase().includes('BOOK'));

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 animate-fade-in animate-fade-in-delay-2">
      <h3 className="text-base font-bold text-[#1e3a5f] mb-5">Ideal Chartering Window</h3>

      {/* Hero action */}
      <div
        className={`${
          isBookNow
            ? 'bg-emerald-50 border-emerald-200'
            : 'bg-[#f0f4ff] border-[#d4dff7]'
        } border rounded-lg p-5 mb-6 flex items-center gap-4`}
      >
        <div
          className={`w-12 h-12 rounded-lg ${
            isBookNow ? 'bg-emerald-600' : 'bg-[#1e3a5f]'
          } flex items-center justify-center flex-shrink-0 shadow-sm`}
        >
          {isBookNow ? (
            <CheckCircle2 className="w-6 h-6 text-white" />
          ) : (
            <Clock className="w-6 h-6 text-white" />
          )}
        </div>
        <div>
          <p
            className={`text-xl font-bold ${
              isBookNow ? 'text-emerald-800' : 'text-[#1e3a5f]'
            }`}
          >
            {data.displayLabel}
          </p>
          <p className="text-sm text-gray-500">{data.explanation}</p>
        </div>
      </div>

      {/* Visual Timeline */}
      <div className="mb-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Timeline
        </p>

        <div className="relative">
          {/* Track */}
          <div className="h-2 bg-gray-100 rounded-full relative overflow-visible">
            {/* Ideal window highlight */}
            <div
              className={`absolute top-0 h-full ${
                isBookNow ? 'bg-emerald-500/20' : 'bg-[#1e3a5f]/15'
              } rounded-full`}
              style={{
                left: `${idealStartPct}%`,
                width: `${idealEndPct - idealStartPct}%`,
              }}
            />
            {/* Ideal window strong bar */}
            <div
              className={`absolute top-0 h-full ${
                isBookNow ? 'bg-emerald-600' : 'bg-[#1e3a5f]'
              } rounded-full`}
              style={{
                left: `${idealStartPct}%`,
                width: `${idealEndPct - idealStartPct}%`,
                opacity: 0.6,
              }}
            />
          </div>

          {/* Markers */}
          <div className="flex justify-between mt-3">
            {/* Today */}
            <div className="flex flex-col items-start" style={{ marginLeft: `${todayPct}%` }}>
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  isBookNow ? 'bg-emerald-600' : 'bg-[#1e3a5f]'
                } border-2 border-white shadow-sm -mt-[22px]`}
              />
              <span className="text-[11px] font-medium text-gray-500 mt-1">Today</span>
            </div>

            {/* Ideal Window label */}
            <div
              className="flex flex-col items-center absolute"
              style={{ left: `${(idealStartPct + idealEndPct) / 2}%`, transform: 'translateX(-50%)' }}
            >
              <span
                className={`text-[11px] font-semibold ${
                  isBookNow ? 'text-emerald-700' : 'text-[#1e3a5f]'
                } mt-1`}
              >
                {data.idealWindowStart !== undefined && data.idealWindowEnd !== undefined
                  ? `Day ${data.idealWindowStart}–${data.idealWindowEnd}`
                  : `~${data.timelineDays} days`}
              </span>
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="flex items-center gap-3 mt-6 text-xs text-gray-500">
          <span className="bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 font-medium">
            Today
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-gray-300" />
          <span className="bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 font-medium">
            Forecast Trend
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-gray-300" />
          <span
            className={`${
              isBookNow
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-[#eef2ff] border-[#d4dff7] text-[#1e3a5f]'
            } border rounded-md px-3 py-1.5 font-semibold`}
          >
            Ideal Window
          </span>
        </div>
      </div>
    </div>
  );
}
