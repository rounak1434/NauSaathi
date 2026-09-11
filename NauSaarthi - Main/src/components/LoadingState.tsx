export default function LoadingState() {
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

      <h2 className="text-lg font-semibold text-[#1e3a5f] mb-2">
        Analysing your chartering requirement...
      </h2>
      <p className="text-sm text-gray-400 text-center max-w-md leading-relaxed">
        Forecasting freight trends&ensp;•&ensp;Evaluating vessel suitability&ensp;•&ensp;Identifying chartering window
      </p>
    </div>
  );
}
