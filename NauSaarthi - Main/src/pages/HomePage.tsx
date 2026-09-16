import { Anchor, ShieldCheck, TrendingDown, Ship } from 'lucide-react';
import InputForm from '../components/InputForm';
import type { CargoRequirement } from '../types';

interface Props {
  initialValues?: Partial<CargoRequirement>;
  onSubmit: (data: CargoRequirement) => void;
}

export default function HomePage({ initialValues, onSubmit }: Props) {
  return (
    <div className="w-full min-h-[calc(100vh-64px)] flex flex-col items-center pt-8 sm:pt-12 pb-16 sm:pb-24 px-4 sm:px-6 lg:px-8">
      {/* Hero Header */}
      <div className="w-full max-w-4xl text-center mb-8 sm:mb-10 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#eef2ff] border border-[#d4dff7] text-[#1e3a5f] text-xs font-semibold mb-4 shadow-xs">
          <Anchor className="w-3.5 h-3.5" />
          <span>SAIL Commercial Decision-Support Platform</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-[#1e3a5f] tracking-tight">
          NauSaarthi
        </h1>
        <p className="text-base sm:text-lg font-semibold text-gray-700 mt-1.5">
          Intelligent Freight &amp; Vessel Chartering Intelligence
        </p>
        <p className="text-xs sm:text-sm text-gray-500 max-w-2xl mx-auto mt-2 leading-relaxed">
          Evaluate voyage economics, forecast Baltic freight trends, verify physical dual-port constraints, and optimize commercial chartering fixtures.
        </p>
      </div>

      {/* Main Intake Form Container */}
      <div className="w-full max-w-4xl animate-fade-in animate-fade-in-delay-1">
        <InputForm initialValues={initialValues} onSubmit={onSubmit} />
      </div>

      {/* Enterprise Feature Badges below Form */}
      <div className="w-full max-w-4xl grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8 text-xs sm:text-sm text-gray-600 animate-fade-in animate-fade-in-delay-2">
        <div className="flex items-center gap-3 p-4 bg-white border border-gray-200/90 rounded-xl shadow-2xs">
          <Ship className="w-5 h-5 text-[#1e3a5f] flex-shrink-0" />
          <span className="font-medium">Dual-port LOA, beam &amp; draft screening</span>
        </div>
        <div className="flex items-center gap-3 p-4 bg-white border border-gray-200/90 rounded-xl shadow-2xs">
          <TrendingDown className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span className="font-medium">12-month forward freight curve analysis</span>
        </div>
        <div className="flex items-center gap-3 p-4 bg-white border border-gray-200/90 rounded-xl shadow-2xs">
          <ShieldCheck className="w-5 h-5 text-[#1e3a5f] flex-shrink-0" />
          <span className="font-medium">Transparent rule-based decision support</span>
        </div>
      </div>
    </div>
  );
}

