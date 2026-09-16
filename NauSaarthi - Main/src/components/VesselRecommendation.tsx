import { Ship, AlertTriangle } from 'lucide-react';
import type { VesselRecommendation as VesselRecType, SuitabilityStatus } from '../types';

interface Props {
  data: VesselRecType;
}

function StatusSymbol({ status }: { status: SuitabilityStatus }) {
  if (status === 'Recommended') {
    return <span className="inline-flex items-center text-xs font-bold text-[#1e3a5f]">✓</span>;
  }
  if (status === 'Suitable') {
    return <span className="inline-flex items-center text-xs font-bold text-emerald-600">✓</span>;
  }
  return <span className="inline-flex items-center text-xs font-bold text-red-400">✗</span>;
}

export default function VesselRecommendationCard({ data }: Props) {
  const isInfeasible =
    data.recommended === 'No Single-Vessel Fit' ||
    data.operationalMode === 'INFEASIBLE' ||
    data.reason.toLowerCase().includes('no vessel');

  // Format operational mode for display
  const modeDisplay = data.operationalMode === 'ALTERNATIVE_DISCHARGE'
    ? 'Alternative Discharge (Lighterage)'
    : data.operationalMode === 'DIRECT_PORT_CALL'
      ? 'Direct Port Call'
      : data.operationalMode === 'INFEASIBLE'
        ? 'Infeasible'
        : data.operationalMode || 'Direct';

  // Find recommended vessel specs
  const recVessel = data.vessels.find((v) => v.isRecommended);

  const cargoFitSymbol = recVessel?.cargoFit === 'Recommended' || recVessel?.cargoFit === 'Suitable' ? '✓' : '✗';
  const portFitSymbol = recVessel?.portFit === 'Recommended' || recVessel?.portFit === 'Suitable' ? '✓' : '⚠';
  const routeFitSymbol = recVessel?.routeFit === 'Recommended' || recVessel?.routeFit === 'Suitable' ? '✓' : '✓';
  const modeShort = data.operationalMode === 'ALTERNATIVE_DISCHARGE' ? 'Lighterage' : 'Direct';

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-5 sm:p-6 flex flex-col justify-between animate-fade-in animate-fade-in-delay-1 h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-[#1e3a5f] tracking-tight">
              RECOMMENDED VESSEL
            </h3>
            <p className="text-xs text-gray-400">
              Optimal deadweight class based on dual-port physical screening.
            </p>
          </div>
          <Ship className="w-5 h-5 text-gray-300" />
        </div>

        {/* Hero Recommendation Block */}
        <div
          className={`${
            isInfeasible
              ? 'bg-amber-50 border-amber-300'
              : 'bg-[#f0f4ff]/90 border-[#d4dff7]'
          } border rounded-lg p-4 mb-4 flex items-center gap-3.5`}
        >
          <div
            className={`w-11 h-11 rounded-lg ${
              isInfeasible ? 'bg-amber-600' : 'bg-[#1e3a5f]'
            } flex items-center justify-center flex-shrink-0 shadow-xs`}
          >
            {isInfeasible ? (
              <AlertTriangle className="w-5 h-5 text-white" />
            ) : (
              <Ship className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-lg sm:text-xl font-extrabold tracking-tight ${
                  isInfeasible ? 'text-amber-900' : 'text-[#1e3a5f]'
                }`}
              >
                {data.recommended.toUpperCase()}
              </span>
              {modeDisplay && (
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                    isInfeasible
                      ? 'bg-amber-200 text-amber-900'
                      : data.operationalMode === 'ALTERNATIVE_DISCHARGE'
                        ? 'bg-amber-100 text-amber-900 border border-amber-200'
                        : 'bg-[#1e3a5f] text-white'
                  }`}
                >
                  {modeDisplay}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 mt-1 leading-snug line-clamp-2">
              {data.reason}
            </p>
          </div>
        </div>

        {/* Key Screening Criteria Row */}
        {!isInfeasible && (
          <div className="grid grid-cols-4 gap-2 mb-4 text-center">
            <div className="bg-gray-50 rounded-lg p-2 border border-gray-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
                Cargo Fit
              </span>
              <span className="text-xs font-bold text-gray-800">
                {cargoFitSymbol} {recVessel?.cargoFit || 'Optimal'}
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 border border-gray-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
                Port Fit
              </span>
              <span className={`text-xs font-bold ${portFitSymbol === '✓' ? 'text-emerald-600' : 'text-amber-700'}`}>
                {portFitSymbol} {recVessel?.portFit || 'Pass'}
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 border border-gray-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
                Route Fit
              </span>
              <span className="text-xs font-bold text-gray-800">
                {routeFitSymbol} {recVessel?.routeFit || 'Economy'}
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 border border-gray-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-0.5">
                Mode
              </span>
              <span className="text-xs font-bold text-[#1e3a5f]">
                {modeShort}
              </span>
            </div>
          </div>
        )}

        {/* 4-Class Comparison Table */}
        <div className="overflow-x-auto rounded-lg border border-gray-100">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-100 text-gray-500">
                <th className="text-left py-2 px-3 font-semibold">Vessel Class</th>
                <th className="text-center py-2 px-2 font-semibold">DWT</th>
                <th className="text-center py-2 px-2 font-semibold">Cargo</th>
                <th className="text-center py-2 px-2 font-semibold">Port</th>
                <th className="text-center py-2 px-2 font-semibold">Route</th>
                <th className="text-left py-2 px-3 font-semibold">Mode</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.vessels.map((v) => {
                const opMode = v.operationalMode || '';
                const modeTag = opMode.includes('Lighterage') || opMode.includes('Transshipment')
                  ? '⚠ Lighterage'
                  : opMode.includes('Infeasible') || opMode.includes('Constrained')
                    ? '✗ Infeasible'
                    : opMode.includes('Direct')
                      ? '✓ Direct'
                      : opMode.split('/')[0].trim();

                const isRec = v.isRecommended;

                return (
                  <tr
                    key={v.vesselClass}
                    className={`transition-colors ${
                      isRec ? 'bg-[#eef2ff]/70 font-semibold' : 'hover:bg-gray-50/50'
                    }`}
                  >
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5">
                        {isRec && <span className="w-1.5 h-1.5 rounded-full bg-[#1e3a5f]" />}
                        <span className={isRec ? 'text-[#1e3a5f] font-bold' : 'text-gray-700'}>
                          {v.vesselClass}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-2 text-center text-gray-500 font-mono">
                      {v.dwtRange || '—'}
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <StatusSymbol status={v.cargoFit} />
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <StatusSymbol status={v.portFit} />
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <StatusSymbol status={v.routeFit} />
                    </td>
                    <td className="py-2.5 px-3 text-left">
                      <span className={`text-[11px] font-medium ${
                        modeTag.includes('✓') ? 'text-emerald-700' : modeTag.includes('⚠') ? 'text-amber-700 font-semibold' : 'text-gray-400'
                      }`}>
                        {modeTag}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
