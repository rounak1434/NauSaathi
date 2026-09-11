import { useState, useEffect } from 'react';

const STATUS_STEPS = [
  'Connecting to decision engine...',
  'Evaluating freight forecast...',
  'Checking vessel & port feasibility...',
  'Generating recommendation...',
];

export default function LoadingState() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % STATUS_STEPS.length);
    }, 1800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-32 animate-fade-in">
      {/* Loading bars */}
      <div className="flex items-end gap-0.5 mb-6">
        <span className="loading-bar" />
        <span className="loading-bar" />
        <span className="loading-bar" />
        <span className="loading-bar" />
        <span className="loading-bar" />
      </div>

      <h2 className="text-lg font-semibold text-[#1e3a5f] mb-2 transition-all duration-300 min-h-[1.75rem] text-center">
        {STATUS_STEPS[stepIndex]}
      </h2>
      <p className="text-sm text-gray-400 text-center max-w-md leading-relaxed">
        Forecasting freight trends&ensp;•&ensp;Evaluating vessel suitability&ensp;•&ensp;Identifying chartering window
      </p>

      {/* Progress pill indicator */}
      <div className="flex items-center gap-1.5 mt-4">
        {STATUS_STEPS.map((_, i) => (
          <span
            key={i}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              i === stepIndex ? 'w-5 bg-[#1e3a5f]' : 'w-1.5 bg-gray-200'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
