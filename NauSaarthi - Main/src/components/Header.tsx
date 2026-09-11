import { Anchor } from 'lucide-react';

interface HeaderProps {
  activePage: 'overview' | 'analysis';
  onNavigate: (page: 'overview' | 'analysis') => void;
  hasAnalysis: boolean;
}

export default function Header({ activePage, onNavigate, hasAnalysis }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="w-full px-6 sm:px-10 lg:px-16 py-3 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => onNavigate('overview')}>
          <div className="w-8 h-8 rounded-lg bg-[#1e3a5f] flex items-center justify-center">
            <Anchor className="w-4.5 h-4.5 text-white" strokeWidth={2.2} />
          </div>
          <span className="text-lg font-bold text-[#1e3a5f] tracking-tight">
            NauSaarthi
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          <button
            onClick={() => onNavigate('overview')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activePage === 'overview'
                ? 'bg-[#eef2ff] text-[#1e3a5f]'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => hasAnalysis && onNavigate('analysis')}
            disabled={!hasAnalysis}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activePage === 'analysis'
                ? 'bg-[#eef2ff] text-[#1e3a5f]'
                : hasAnalysis
                  ? 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
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
