import { useState } from 'react';
import {
  Anchor,
  BarChart3,
  BookOpen,
  History,
  ShieldCheck,
  X,
  TrendingDown,
} from 'lucide-react';

interface HeaderProps {
  activePage: 'overview' | 'analysis';
  onNavigate: (page: 'overview' | 'analysis') => void;
  hasAnalysis: boolean;
}

type ModalType = 'past_analyses' | 'market_insights' | 'documentation' | null;

export default function Header({ activePage, onNavigate, hasAnalysis }: HeaderProps) {
  const [activeModal, setActiveModal] = useState<ModalType>(null);

  return (
    <>
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 w-full shadow-2xs">
        <div className="w-full px-4 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-4">
          {/* Left: Brand Identity */}
          <div
            className="flex items-center gap-3 cursor-pointer select-none flex-shrink-0"
            onClick={() => onNavigate('overview')}
          >
            <div className="w-9 h-9 rounded-lg bg-[#1e3a5f] flex items-center justify-center shadow-xs">
              <Anchor className="w-5 h-5 text-white" strokeWidth={2.2} />
            </div>
            <div className="flex flex-col">
              <span className="text-base sm:text-lg font-extrabold text-[#1e3a5f] tracking-tight leading-none">
                NauSaarthi
              </span>
              <span className="text-[11px] text-slate-500 hidden md:inline leading-tight mt-0.5 font-medium">
                Intelligent Freight &amp; Vessel Chartering Intelligence
              </span>
            </div>
          </div>

          {/* Center: Main Navigation */}
          <nav className="flex items-center gap-1 sm:gap-1.5 overflow-x-auto py-1">
            <button
              onClick={() => onNavigate('overview')}
              className={`px-3 sm:px-3.5 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
                activePage === 'overview'
                  ? 'bg-[#1e3a5f] text-white font-semibold shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => hasAnalysis && onNavigate('analysis')}
              disabled={!hasAnalysis}
              className={`px-3 sm:px-3.5 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                activePage === 'analysis'
                  ? 'bg-[#1e3a5f] text-white font-semibold shadow-2xs cursor-pointer'
                  : hasAnalysis
                    ? 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 cursor-pointer'
                    : 'text-slate-300 cursor-not-allowed'
              }`}
            >
              Analysis
              {hasAnalysis && (
                <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              )}
            </button>
            <button
              onClick={() => setActiveModal('past_analyses')}
              className="px-3 sm:px-3.5 py-1.5 text-xs sm:text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer hidden lg:inline-flex items-center gap-1.5 whitespace-nowrap"
            >
              <History className="w-3.5 h-3.5 text-slate-400" />
              Past Analyses
            </button>
            <button
              onClick={() => setActiveModal('market_insights')}
              className="px-3 sm:px-3.5 py-1.5 text-xs sm:text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer hidden lg:inline-flex items-center gap-1.5 whitespace-nowrap"
            >
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              Market Insights
            </button>
            <button
              onClick={() => setActiveModal('documentation')}
              className="px-3 sm:px-3.5 py-1.5 text-xs sm:text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer hidden xl:inline-flex items-center gap-1.5 whitespace-nowrap"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-400" />
              Documentation
            </button>
          </nav>

          {/* Right: Enterprise Badge & User Profile */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200/90 text-xs font-medium text-slate-700">
              <ShieldCheck className="w-3.5 h-3.5 text-[#1e3a5f]" />
              <span className="truncate max-w-[210px]">SAIL Commercial Platform</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            </div>

            <div className="flex items-center gap-2 pl-1 sm:pl-2 sm:border-l border-slate-200">
              <div className="w-8 h-8 rounded-full bg-[#1e3a5f]/10 border border-[#1e3a5f]/20 flex items-center justify-center text-[#1e3a5f] font-semibold text-xs">
                SC
              </div>
              <div className="hidden 2xl:flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-800 leading-none">Chartering Desk</span>
                <span className="text-[10px] text-slate-400 leading-tight">Steel Authority of India</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Interactive Modal: Past Analyses */}
      {activeModal === 'past_analyses' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 relative">
            <button
              onClick={() => setActiveModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 mb-4">
              <History className="w-5 h-5 text-[#1e3a5f]" />
              <h3 className="text-base font-bold text-slate-900">Recent Chartering Fixture Inquiries</h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Historical scenario runs cached for SAIL commercial chartering evaluation.
            </p>
            <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-800">Australia → Paradip (95,000 MT)</div>
                  <div className="text-[11px] text-slate-500">Capesize • Within 30 Days • Sept 2026</div>
                </div>
                <span className="px-2.5 py-1 rounded text-xs font-semibold bg-amber-100 text-amber-800">
                  WAIT / DEFER
                </span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-800">Australia → Dhamra (80,000 MT)</div>
                  <div className="text-[11px] text-slate-500">Panamax • Within 7 Days • Immediate Fixture</div>
                </div>
                <span className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">
                  BOOK NOW
                </span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-800">South Africa → Visakhapatnam (75,000 MT)</div>
                  <div className="text-[11px] text-slate-500">Panamax • Within 60 Days • Forward Trough</div>
                </div>
                <span className="px-2.5 py-1 rounded text-xs font-semibold bg-amber-100 text-amber-800">
                  WAIT / DEFER
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Modal: Market Insights */}
      {activeModal === 'market_insights' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 relative">
            <button
              onClick={() => setActiveModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-5 h-5 text-[#1e3a5f]" />
              <h3 className="text-base font-bold text-slate-900">Global Dry-Bulk Benchmarks &amp; Bunker Feeds</h3>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="text-xs text-slate-500 font-medium">Baltic Capesize Index (BCI)</div>
                <div className="text-lg font-bold text-[#1e3a5f] mt-0.5">2,845 pts</div>
                <div className="text-[11px] text-red-600 mt-0.5 font-medium flex items-center gap-1">
                  <TrendingDown className="w-3 h-3" /> -14.2% forward trend
                </div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="text-xs text-slate-500 font-medium">Baltic Panamax Index (BPI)</div>
                <div className="text-lg font-bold text-[#1e3a5f] mt-0.5">1,620 pts</div>
                <div className="text-[11px] text-slate-500 mt-0.5 font-medium">Stable forward curve</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="text-xs text-slate-500 font-medium">VLSFO Bunker (Singapore)</div>
                <div className="text-lg font-bold text-slate-800 mt-0.5">$615.50 / MT</div>
                <div className="text-[11px] text-slate-500 mt-0.5 font-medium">STEP7B verified fuel feed</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="text-xs text-slate-500 font-medium">Hay Point → Paradip Benchmark</div>
                <div className="text-lg font-bold text-[#1e3a5f] mt-0.5">$25.63 / MT</div>
                <div className="text-[11px] text-emerald-600 mt-0.5 font-medium">Current benchmark baseline</div>
              </div>
            </div>
            <p className="text-[11px] text-slate-400">
              Data synchronized with Baltic Exchange index definitions and standard voyage distance matrices.
            </p>
          </div>
        </div>
      )}

      {/* Interactive Modal: Documentation */}
      {activeModal === 'documentation' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 relative">
            <button
              onClick={() => setActiveModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-5 h-5 text-[#1e3a5f]" />
              <h3 className="text-base font-bold text-slate-900">NauSaarthi Architecture &amp; Methodology</h3>
            </div>
            <div className="space-y-3 text-xs text-slate-600">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="font-bold text-slate-800 text-xs mb-1">Three-Dimensional Decision Architecture</div>
                <p className="leading-relaxed">
                  NauSaarthi synthesizes <strong>Freight Price (Economics)</strong>, <strong>Vessel &amp; Port Compatibility (Physical Feasibility)</strong>, and <strong>Chartering Horizon (Timing Signal)</strong> into a single explainable advisory.
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="font-bold text-slate-800 text-xs mb-1">Dual-Port Feasibility Engine</div>
                <p className="leading-relaxed">
                  Evaluates vessel maximum summer draft, LOA, and beam against both loading and destination port operational profiles to prevent demurrage penalties.
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="font-bold text-slate-800 text-xs mb-1">Deterministic Rule-Based Governance</div>
                <p className="leading-relaxed">
                  Decision actions (BOOK NOW / WAIT) are governed by transparent commercial thresholds comparing prompt fixtures against forward rate curves and risk parameters.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
