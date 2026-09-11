import { useState } from 'react';
import Header from './components/Header';
import HomePage from './pages/HomePage';
import AnalysisPage from './pages/AnalysisPage';
import LoadingState from './components/LoadingState';
import { analyzeCharteringRequirement } from './services/api';
import type { CargoRequirement, AnalysisResponse } from './types';

type AppView = 'overview' | 'loading' | 'analysis';

export default function App() {
  const [view, setView] = useState<AppView>('overview');
  const [lastInput, setLastInput] = useState<Partial<CargoRequirement>>({});
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CargoRequirement) {
    setLastInput(data);
    setView('loading');
    setError(null);

    try {
      const result = await analyzeCharteringRequirement(data);
      setAnalysis(result);
      setView('analysis');
    } catch (err: unknown) {
      console.error('Analysis failed:', err);
      const msg = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      setError(msg);
      setView('overview');
    }
  }

  function handleModifyInputs() {
    setView('overview');
  }

  function handleNewAnalysis() {
    setLastInput({});
    setAnalysis(null);
    setView('overview');
  }

  function handleNavigate(page: 'overview' | 'analysis') {
    if (page === 'analysis' && analysis) {
      setView('analysis');
    } else {
      setView('overview');
    }
  }

  return (
    <div className="min-h-screen bg-[#f8f9fb]">
      <Header
        activePage={view === 'analysis' ? 'analysis' : 'overview'}
        onNavigate={handleNavigate}
        hasAnalysis={analysis !== null}
      />

      {error && (
        <div className="max-w-2xl mx-auto mt-4 px-4">
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        </div>
      )}

      {view === 'overview' && (
        <HomePage initialValues={lastInput} onSubmit={handleSubmit} />
      )}

      {view === 'loading' && <LoadingState />}

      {view === 'analysis' && analysis && (
        <AnalysisPage
          analysis={analysis}
          onModifyInputs={handleModifyInputs}
          onNewAnalysis={handleNewAnalysis}
        />
      )}
    </div>
  );
}
