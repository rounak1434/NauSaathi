import { Anchor, ShieldCheck, TrendingDown, Ship } from 'lucide-react';
import InputForm from '../components/InputForm';
import type { CargoRequirement } from '../types';

interface Props {
  initialValues?: Partial<CargoRequirement>;
  onSubmit: (data: CargoRequirement) => void;
}

export default function HomePage({ initialValues, onSubmit }: Props) {
  return (
    <div className="w-full min-h-[calc(100vh-60px)] flex flex-col justify-center items-center py-8 sm:py-12 px-4 sm:px-6 lg:px-8">
      {/* Hero Header */}
      <div className="w-full max-w-3xl text-center mb-8 animate-fade-in">
        <div className="inline-flex items-center gap-2.5 px-3 py-1 rounded-full bg-[#eef2ff] border border-[#d4dff7] text-[#1e3a5f] text-xs font-semibold mb-4 shadow-xs">
          <Anchor className="w-3.5 h-3.5" />
          <span>SAIL Commercial Decision-Support Platform</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#1e3a5f] tracking-tight">
          NauSaarthi
        </h1>
        <p className="text-base sm:text-lg font-medium text-gray-700 mt-1">
          Intelligent Freight &amp; Vessel Chartering Intelligence
        </p>
        <p className="text-xs sm:text-sm text-gray-400 max-w-xl mx-auto mt-1 leading-normal">
          Evaluate voyage economics, forecast Baltic freight trends, verify physical dual-port constraints, and optimize commercial chartering fixtures.
        </p>
      </div>

      {/* Main Intake Form Container */}
      <div className="w-full max-w-3xl animate-fade-in animate-fade-in-delay-1 shadow-sm">
        <InputForm initialValues={initialValues} onSubmit={onSubmit} />
      </div>

      {/* Enterprise Feature Badges below Form */}
      <div className="w-full max-w-3xl grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6 text-xs text-gray-500 animate-fade-in animate-fade-in-delay-2">
        <div className="flex items-center gap-2 p-3 bg-white/70 border border-gray-200/80 rounded-lg">
          <Ship className="w-4 h-4 text-[#1e3a5f] flex-shrink-0" />
          <span>Dual-port LOA, beam &amp; draft screening</span>
        </div>
        <div className="flex items-center gap-2 p-3 bg-white/70 border border-gray-200/80 rounded-lg">
          <TrendingDown className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>12-month forward freight curve analysis</span>
        </div>
        <div className="flex items-center gap-2 p-3 bg-white/70 border border-gray-200/80 rounded-lg">
          <ShieldCheck className="w-4 h-4 text-[#1e3a5f] flex-shrink-0" />
          <span>Transparent rule-based decision support</span>
        </div>
      </div>
    </div>
  );
}
