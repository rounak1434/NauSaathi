import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { FreightForecast as FreightForecastType } from '../types';

interface Props {
  data: FreightForecastType;
}

function TrendBadge({ trend }: { trend: string }) {
  const config = {
    RISING: { label: 'Rising', icon: TrendingUp, bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    FALLING: { label: 'Falling', icon: TrendingDown, bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    STABLE: { label: 'Stable', icon: Minus, bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' },
  }[trend] ?? { label: trend, icon: Minus, bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' };

  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full border ${config.bg} ${config.text} ${config.border}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  );
}

function ConfidenceBadge({ level }: { level: string }) {
  const config = {
    HIGH: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    MEDIUM: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    LOW: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200' },
  }[level] ?? { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' };

  return (
    <span className={`inline-flex items-center px-3 py-1 text-xs font-semibold rounded-full border ${config.bg} ${config.text} ${config.border}`}>
      {level}
    </span>
  );
}

// Custom tooltip
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  const isBridge = item.historical !== null && item.forecast !== null;
  const val = item.forecast ?? item.historical;
  const tag = isBridge ? 'Current Observation' : item.isForecast ? 'Forecast' : 'Historical';
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-0.5">{label}</p>
      <p className="text-[#1e3a5f] font-medium">
        ${val?.toFixed(2)} / MT
        <span className="ml-1 text-gray-400 font-normal">
          ({tag})
        </span>
      </p>
    </div>
  );
}

export default function FreightForecastCard({ data }: Props) {
  // Build combined dataset with separate historical / forecast keys.
  // The bridge point (last historical = current market observation) shares both
  // keys so the dashed forecast line smoothly connects from the current observation.
  const combined = data.chartData.map((d, idx) => {
    const isLastHistorical =
      d.type === 'historical' &&
      (idx === data.chartData.length - 1 || data.chartData[idx + 1]?.type === 'forecast');
    return {
      date: d.date,
      historical: d.type === 'historical' ? d.rate : null,
      forecast: d.type === 'forecast' ? d.rate : isLastHistorical ? d.rate : null,
      isForecast: d.type === 'forecast',
    };
  });

  const bridgePoint = data.chartData.find((d, idx) =>
    d.type === 'historical' &&
    (idx === data.chartData.length - 1 || data.chartData[idx + 1]?.type === 'forecast')
  );
  const todayLabel = bridgePoint?.date ?? (data.chartData[0]?.date ?? '');

  // Dynamic Y-axis scale based on actual rate range
  const allRates = data.chartData.map((d) => d.rate).filter((r) => !isNaN(r) && r > 0);
  const minRate = allRates.length > 0 ? Math.min(...allRates) : 0;
  const maxRate = allRates.length > 0 ? Math.max(...allRates) : 50;
  const yPadding = (maxRate - minRate) * 0.15 || 2;
  const yMin = Math.max(0, Math.floor(minRate - yPadding));
  const yMax = Math.ceil(maxRate + yPadding);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 animate-fade-in">
      <h3 className="text-base font-bold text-[#1e3a5f] mb-5">Freight Price Forecast</h3>

      {/* Rate cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Current Market Rate</p>
          <p className="text-2xl font-bold text-gray-900">
            ${data.currentRatePerMT.toFixed(2)}
            <span className="text-sm font-normal text-gray-400 ml-1">/ MT</span>
          </p>
        </div>
        <div className="bg-[#f0f4ff] rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Expected Rate</p>
          <p className="text-2xl font-bold text-[#1e3a5f]">
            ${data.expectedRatePerMT.toFixed(2)}
            <span className="text-sm font-normal text-gray-400 ml-1">/ MT</span>
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="h-56 mb-5">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={combined} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${v}`}
              width={48}
              domain={[yMin, yMax]}
            />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine
              x={todayLabel}
              stroke="#cbd5e1"
              strokeDasharray="4 4"
              label={{ value: 'Today', position: 'top', fontSize: 10, fill: '#94a3b8' }}
            />
            {/* Historical line (solid) */}
            <Line
              dataKey="historical"
              stroke="#1e3a5f"
              strokeWidth={2}
              dot={{ r: 3, fill: '#1e3a5f', stroke: '#fff', strokeWidth: 2 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
            {/* Forecast line (dashed) */}
            <Line
              dataKey="forecast"
              stroke="#1e3a5f"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={{ r: 3, fill: '#fff', stroke: '#1e3a5f', strokeWidth: 2 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 text-xs text-gray-400 mb-5">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-0.5 bg-[#1e3a5f] rounded" /> Historical
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dashed border-[#1e3a5f]" /> Forecast
        </span>
      </div>

      {/* Trend + Confidence */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <span className="text-xs text-gray-400 mr-2">Market Trend</span>
          <TrendBadge trend={data.trend} />
        </div>
        <div>
          <span className="text-xs text-gray-400 mr-2">Forecast Confidence</span>
          <ConfidenceBadge level={data.confidence} />
        </div>
      </div>
    </div>
  );
}
