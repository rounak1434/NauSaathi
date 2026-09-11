import { Ship, Check, X } from 'lucide-react';
import type { VesselRecommendation as VesselRecType, SuitabilityStatus } from '../types';

interface Props {
  data: VesselRecType;
}

function StatusCell({ status }: { status: SuitabilityStatus }) {
  if (status === 'Recommended') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#1e3a5f]">
        <Check className="w-3.5 h-3.5" />
        Recommended
      </span>
    );
  }
  if (status === 'Suitable') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
        <Check className="w-3.5 h-3.5" />
        Suitable
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-400">
      <X className="w-3.5 h-3.5" />
      Not Suitable
    </span>
  );
}

export default function VesselRecommendationCard({ data }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 animate-fade-in animate-fade-in-delay-1">
      <h3 className="text-base font-bold text-[#1e3a5f] mb-5">Recommended Vessel</h3>

      {/* Hero recommendation */}
      <div className="bg-[#f0f4ff] border border-[#d4dff7] rounded-lg p-5 mb-6 flex items-center gap-4">
        <div className="w-12 h-12 rounded-lg bg-[#1e3a5f] flex items-center justify-center flex-shrink-0">
          <Ship className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-xl font-bold text-[#1e3a5f]">{data.recommended}</p>
          <p className="text-sm text-gray-500">{data.reason}</p>
        </div>
      </div>

      {/* Vessel comparison table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-2.5 pr-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Vessel Class
              </th>
              <th className="text-left py-2.5 px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Cargo Fit
              </th>
              <th className="text-left py-2.5 px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Port Fit
              </th>
              <th className="text-left py-2.5 pl-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Route Fit
              </th>
            </tr>
          </thead>
          <tbody>
            {data.vessels.map((v) => (
              <tr
                key={v.vesselClass}
                className={`border-b border-gray-50 ${
                  v.isRecommended ? 'bg-[#f8faff]' : ''
                }`}
              >
                <td className="py-3 pr-4">
                  <span
                    className={`font-medium ${
                      v.isRecommended ? 'text-[#1e3a5f] font-semibold' : 'text-gray-700'
                    }`}
                  >
                    {v.vesselClass}
                  </span>
                  {v.isRecommended && (
                    <span className="ml-2 text-[10px] font-bold uppercase tracking-wide bg-[#1e3a5f] text-white px-1.5 py-0.5 rounded">
                      Best Fit
                    </span>
                  )}
                </td>
                <td className="py-3 px-3">
                  <StatusCell status={v.cargoFit} />
                </td>
                <td className="py-3 px-3">
                  <StatusCell status={v.portFit} />
                </td>
                <td className="py-3 pl-3">
                  <StatusCell status={v.routeFit} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
