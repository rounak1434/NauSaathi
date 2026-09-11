import { Anchor } from 'lucide-react';
import InputForm from '../components/InputForm';
import type { CargoRequirement } from '../types';

interface Props {
  initialValues?: Partial<CargoRequirement>;
  onSubmit: (data: CargoRequirement) => void;
}

export default function HomePage({ initialValues, onSubmit }: Props) {
  return (
    <div className="min-h-[calc(100vh-57px)] flex flex-col items-center justify-center px-4 py-12">
      {/* Hero */}
      <div className="text-center mb-10 animate-fade-in">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-[#1e3a5f] flex items-center justify-center">
            <Anchor className="w-5 h-5 text-white" strokeWidth={2.2} />
          </div>
          <h1 className="text-2xl font-bold text-[#1e3a5f] tracking-tight">NauSaarthi</h1>
        </div>
        <p className="text-sm font-medium text-gray-500 mb-1">
          Intelligent Freight Forecasting &amp; Vessel Chartering Intelligence
        </p>
        <p className="text-xs text-gray-400">
          Smarter decisions for bulk vessel chartering
        </p>
      </div>

      {/* Form */}
      <div className="w-full max-w-2xl mx-auto animate-fade-in animate-fade-in-delay-1">
        <InputForm initialValues={initialValues} onSubmit={onSubmit} />
      </div>
    </div>
  );
}
