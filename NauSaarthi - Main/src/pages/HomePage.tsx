import {
  TrendingUp,
  Ship,
  Clock,
  CheckCircle2,
  BarChart3,
  Database,
  Cpu,
  ShieldCheck,
  Layers,
} from 'lucide-react';
import InputForm from '../components/InputForm';
import type { CargoRequirement } from '../types';

interface Props {
  initialValues?: Partial<CargoRequirement>;
  onSubmit: (data: CargoRequirement) => void;
}

export default function HomePage({ initialValues, onSubmit }: Props) {
  return (
    <div className="w-full max-w-[1560px] mx-auto px-4 sm:px-6 lg:px-8 py-5 sm:py-6 animate-fade-in">
      {/* 2. Strong Page Header */}
      <div className="mb-5 sm:mb-6 border-b border-slate-200/80 pb-4">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#1e3a5f] tracking-tight leading-none">
              NauSaarthi
            </h1>
            <p className="text-sm sm:text-base font-semibold text-slate-700 mt-1">
              Intelligent Freight &amp; Vessel Chartering Intelligence
            </p>
            <p className="text-xs sm:text-sm text-slate-500 max-w-3xl mt-1 leading-normal">
              Evaluate freight outlook, vessel suitability, port feasibility and chartering windows through an integrated decision-support workflow.
            </p>
          </div>
          <div className="hidden lg:flex items-center gap-2 text-xs font-semibold text-[#1e3a5f] bg-slate-100/90 px-3 py-1.5 rounded-lg border border-slate-200 self-start md:self-auto">
            <Layers className="w-3.5 h-3.5" />
            <span>PRICE → VESSEL → TIME = COMMERCIAL DECISION</span>
          </div>
        </div>
      </div>

      {/* 3. Main Dashboard Layout (Two-Column Desktop) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 items-start">
        {/* Left Column: Primary Chartering Requirement Card */}
        <div className="lg:col-span-7 xl:col-span-7 w-full">
          <InputForm initialValues={initialValues} onSubmit={onSubmit} />
        </div>

        {/* Right Column: Three Dimensions. One Decision. + Why NauSaarthi? */}
        <div className="lg:col-span-5 xl:col-span-5 w-full flex flex-col gap-4 sm:gap-5">
          {/* Three Dimensions. One Decision. Card */}
          <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-5 sm:p-6">
            <div className="border-b border-slate-100 pb-3 mb-4">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Three Dimensions. One Decision.
              </span>
              <h3 className="text-base sm:text-lg font-bold text-[#1e3a5f] tracking-tight mt-0.5">
                Integrated Chartering Intelligence
              </h3>
            </div>

            <div className="space-y-3.5">
              {/* PRICE */}
              <div className="flex items-start gap-3.5 p-3 rounded-lg bg-slate-50/70 border border-slate-200/70">
                <div className="w-9 h-9 rounded-lg bg-[#1e3a5f] flex items-center justify-center flex-shrink-0 text-white shadow-2xs">
                  <TrendingUp className="w-4.5 h-4.5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#1e3a5f] uppercase tracking-wider">
                      PRICE
                    </span>
                    <span className="text-[10px] font-medium text-slate-400">Voyage Economics</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5 leading-snug">
                    Forecast freight trends and estimate voyage economics.
                  </p>
                </div>
              </div>

              {/* VESSEL */}
              <div className="flex items-start gap-3.5 p-3 rounded-lg bg-slate-50/70 border border-slate-200/70">
                <div className="w-9 h-9 rounded-lg bg-[#1e3a5f] flex items-center justify-center flex-shrink-0 text-white shadow-2xs">
                  <Ship className="w-4.5 h-4.5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#1e3a5f] uppercase tracking-wider">
                      VESSEL
                    </span>
                    <span className="text-[10px] font-medium text-slate-400">Physical Feasibility</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5 leading-snug">
                    Match suitable vessel classes based on cargo, route and port constraints.
                  </p>
                </div>
              </div>

              {/* TIME */}
              <div className="flex items-start gap-3.5 p-3 rounded-lg bg-slate-50/70 border border-slate-200/70">
                <div className="w-9 h-9 rounded-lg bg-[#1e3a5f] flex items-center justify-center flex-shrink-0 text-white shadow-2xs">
                  <Clock className="w-4.5 h-4.5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#1e3a5f] uppercase tracking-wider">
                      TIME
                    </span>
                    <span className="text-[10px] font-medium text-slate-400">Chartering Horizon</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5 leading-snug">
                    Identify suitable chartering windows using forecast trends.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-medium">
              <span>Decision Output</span>
              <span className="px-2 py-0.5 rounded bg-slate-100 font-bold text-[#1e3a5f]">
                BOOK NOW / WAIT Advisory
              </span>
            </div>
          </div>

          {/* 5. "Why NauSaarthi?" Card */}
          <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-5 sm:p-6">
            <div className="border-b border-slate-100 pb-3 mb-3.5">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Why NauSaarthi?
              </span>
              <h3 className="text-sm sm:text-base font-bold text-[#1e3a5f] tracking-tight mt-0.5">
                Enterprise Maritime Decision Support
              </h3>
            </div>

            <div className="space-y-2.5">
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#1e3a5f] flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-bold text-slate-800">
                    Integrated freight + vessel + port analysis
                  </span>
                  <p className="text-[11px] text-slate-500 leading-snug">
                    Unifies freight economics with physical vessel dimensions and draft limits.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#1e3a5f] flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-bold text-slate-800">
                    Forecast-driven charter timing
                  </span>
                  <p className="text-[11px] text-slate-500 leading-snug">
                    Identifies whether immediate booking or strategic deferral yields freight savings.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#1e3a5f] flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-bold text-slate-800">
                    Feasibility-first recommendations
                  </span>
                  <p className="text-[11px] text-slate-500 leading-snug">
                    Hard physical screening of draft, LOA, and beam prevents costly demurrage.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#1e3a5f] flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-bold text-slate-800">
                    Explainable decision support
                  </span>
                  <p className="text-[11px] text-slate-500 leading-snug">
                    Transparent rule-based factor chains rather than opaque black-box recommendations.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Below Main Section: Compact Row of Four Information Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-5 sm:mt-6">
        {/* Card 1: BDI / BCI / BPI */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-4 flex items-start gap-3.5 hover:border-slate-300 transition-colors">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[#1e3a5f] flex-shrink-0 mt-0.5">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800">BDI / BCI / BPI</div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
              Global dry-bulk market benchmarks
            </p>
            <span className="text-[10px] font-semibold text-[#1e3a5f] mt-1 inline-block">
              Baltic Exchange Indexes
            </span>
          </div>
        </div>

        {/* Card 2: Vessel & Port Data */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-4 flex items-start gap-3.5 hover:border-slate-300 transition-colors">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[#1e3a5f] flex-shrink-0 mt-0.5">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800">Vessel &amp; Port Data</div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
              Vessel specifications and port infrastructure inputs
            </p>
            <span className="text-[10px] font-semibold text-[#1e3a5f] mt-1 inline-block">
              Draft, LOA &amp; Beam Verified
            </span>
          </div>
        </div>

        {/* Card 3: ML-Driven Forecasting */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-4 flex items-start gap-3.5 hover:border-slate-300 transition-colors">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[#1e3a5f] flex-shrink-0 mt-0.5">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800">ML-Driven Forecasting</div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
              Random Forest + SARIMA benchmark
            </p>
            <span className="text-[10px] font-semibold text-[#1e3a5f] mt-1 inline-block">
              12-Month Forward Curves
            </span>
          </div>
        </div>

        {/* Card 4: Commercial Decision Support */}
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-4 flex items-start gap-3.5 hover:border-slate-300 transition-colors">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[#1e3a5f] flex-shrink-0 mt-0.5">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-800">Commercial Decision Support</div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
              From market data to chartering recommendation
            </p>
            <span className="text-[10px] font-semibold text-[#1e3a5f] mt-1 inline-block">
              BOOK NOW / WAIT Governance
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
