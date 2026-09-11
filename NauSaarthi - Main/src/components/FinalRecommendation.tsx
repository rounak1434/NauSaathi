import { CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import type { Recommendation } from '../types';

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
        accentBg: 'bg-amber-50',
        accentBorder: 'border-amber-300',
        accentText: 'text-amber-900',
        iconBg: 'bg-amber-600',
      }
    : isBookNow
    ? {
        icon: CheckCircle2,
        accentBg: 'bg-emerald-50',
        accentBorder: 'border-emerald-200',
        accentText: 'text-emerald-800',
        iconBg: 'bg-emerald-600',
      }
    : isWait
    ? {
        icon: Clock,
        accentBg: 'bg-amber-50',
        accentBorder: 'border-amber-200',
        accentText: 'text-amber-800',
        iconBg: 'bg-amber-500',
      }
    : {
        icon: AlertTriangle,
        accentBg: 'bg-blue-50',
        accentBorder: 'border-blue-200',
        accentText: 'text-blue-800',
        iconBg: 'bg-blue-600',
      };

  const Icon = selectedConfig.icon;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 animate-fade-in animate-fade-in-delay-3">
      <h3 className="text-base font-bold text-[#1e3a5f] mb-5">NauSaarthi Recommendation</h3>

      {/* Verdict hero */}
      <div
        className={`${selectedConfig.accentBg} ${selectedConfig.accentBorder} border rounded-lg p-5 mb-5 flex items-center gap-4`}
      >
        <div
          className={`w-12 h-12 rounded-lg ${selectedConfig.iconBg} flex items-center justify-center flex-shrink-0 shadow-sm`}
        >
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className={`text-xl font-bold ${selectedConfig.accentText}`}>{data.displayLabel}</p>
        </div>
      </div>

      {/* Reasons */}
      <div>
        <p className="text-sm font-semibold text-gray-600 mb-3">Why this recommendation?</p>
        <ul className="space-y-2">
          {data.reasons.map((reason, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm text-gray-600 leading-relaxed">
              <span
                className={`mt-1.5 w-1.5 h-1.5 rounded-full ${
                  isInfeasible
                    ? 'bg-amber-600'
                    : isBookNow
                      ? 'bg-emerald-600'
                      : 'bg-[#1e3a5f]'
                } flex-shrink-0`}
              />
              {reason}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
