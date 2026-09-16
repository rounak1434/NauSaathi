import { Anchor } from 'lucide-react';

interface HeaderProps {
  activePage: 'overview' | 'analysis';
  onNavigate: (page: 'overview' | 'analysis') => void;
  hasAnalysis: boolean;
}

export default function Header({ activePage, onNavigate, hasAnalysis }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30 w-full shadow-xs">
      <div className="w-full px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        {/* Brand */}
        <div
          className="flex items-center gap-3 cursor-pointer select-none"
          onClick={() => onNavigate('overview')}
        >
          <div className="w-8 h-8 rounded-lg bg-[#1e3a5f] flex items-center justify-center shadow-xs">
            <Anchor className="w-4.5 h-4.5 text-white" strokeWidth={2.2} />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold text-[#1e3a5f] tracking-tight leading-none">
              NauSaarthi
            </span>
            <span className="text-[11px] text-gray-400 hidden sm:inline leading-tight mt-0.5 font-medium">
              Intelligent Freight &amp; Vessel Chartering Intelligence
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1.5">
          <button
            onClick={() => onNavigate('overview')}
            className={`px-3.5 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-colors cursor-pointer ${
              activePage === 'overview'
                ? 'bg-[#eef2ff] text-[#1e3a5f] font-semibold'
                : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100/70'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => hasAnalysis && onNavigate('analysis')}
            disabled={!hasAnalysis}
            className={`px-3.5 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-colors ${
              activePage === 'analysis'
                ? 'bg-[#eef2ff] text-[#1e3a5f] font-semibold cursor-pointer'
                : hasAnalysis
                  ? 'text-gray-500 hover:text-gray-800 hover:bg-gray-100/70 cursor-pointer'
                  : 'text-gray-300 cursor-not-allowed'
            }`}
          >
            Analysis
          </button>
        </nav>
      </div>
    </header>
  );
}
