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
import { TrendingUp, TrendingDown, Minus, Info, ArrowDown, ArrowUp } from 'lucide-react';
import type { FreightForecast as FreightForecastType, MarketTrend } from '../types';

interface Props {
  data: FreightForecastType;
}

function TrendBadge({ trend }: { trend: MarketTrend }) {
  const config = {
    RISING: { label: 'Rising Freight', icon: TrendingUp, bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    FALLING: { label: 'Falling Freight', icon: TrendingDown, bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    STABLE: { label: 'Stable Market', icon: Minus, bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' },
  }[trend] ?? { label: trend, icon: Minus, bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' };

  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full border ${config.bg} ${config.text} ${config.border}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  );
}

function ForecastSignalBadge({ level, detail }: { level: string; detail?: string }) {
  const config = {
    Strong: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    Moderate: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    Weak: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200' },
  }[level] ?? { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full border ${config.bg} ${config.text} ${config.border}`}
      title={detail || `Forecast signal: ${level}`}
    >
      <span className="font-bold">{level}</span>
      {detail && <Info className="w-3 h-3 opacity-60" />}
    </span>
  );
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      date: string;
      historical: number | null;
      forecast: number | null;
      isForecast: boolean;
    };
  }>;
  label?: string;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  const isBridge = item.historical !== null && item.forecast !== null;
  const val = item.forecast ?? item.historical;
  const tag = isBridge ? 'Current Observation' : item.isForecast ? 'Forward Pipeline Forecast' : 'Derived';
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3.5 py-2 text-xs">
      <p className="font-bold text-gray-800 mb-0.5">{label}</p>
      <p className="text-[#1e3a5f] font-semibold text-sm">
        ${val?.toFixed(2)} <span className="text-xs text-gray-400 font-normal">/ MT</span>
      </p>
      <p className="text-[10px] text-gray-400 mt-0.5">
        {tag}
      </p>
    </div>
  );
}

export default function FreightForecast({ data }: Props) {
  const historical = data.chartData.filter((d) => d.type === 'historical');
  const forecast = data.chartData.filter((d) => d.type === 'forecast');
  const histLen = historical.length;
  const lastHist = histLen > 0 ? historical[histLen - 1] : null;
  const todayLabel = lastHist?.date ?? '';

  const chartPoints = [
    ...historical.map((d, i) => ({
      date: d.date,
      historical: d.rate,
      forecast: i === histLen - 1 ? d.rate : null,
      isForecast: false,
    })),
    ...forecast.map((d) => ({
      date: d.date,
      historical: null as number | null,
      forecast: d.rate,
      isForecast: true,
    })),
  ];

  const combined = chartPoints.reduce(
    (acc, cur) => {
      const existing = acc.find((item) => item.date === cur.date);
      if (existing) {
        if (cur.historical !== null) existing.historical = cur.historical;
        if (cur.forecast !== null) existing.forecast = cur.forecast;
      } else {
        acc.push({ ...cur });
      }
      return acc;
    },
    [] as typeof chartPoints
  );

  const allRates = data.chartData.map((d) => d.rate).filter((r) => r > 0);

  const minRate = allRates.length > 0 ? Math.min(...allRates) : 0;
  const maxRate = allRates.length > 0 ? Math.max(...allRates) : 50;
  const yPadding = (maxRate - minRate) * 0.15 || 2;
  const yMin = Math.max(0, Math.floor(minRate - yPadding));
  const yMax = Math.ceil(maxRate + yPadding);

  // Rate delta display
  const deltaAbs = Math.abs(data.rateDeltaPct);
  const isLower = data.rateDeltaPct < -0.1;
  const isHigher = data.rateDeltaPct > 0.1;
  const deltaColor = isLower ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : isHigher ? 'text-amber-700 bg-amber-50 border-amber-200' : 'text-gray-600 bg-gray-50 border-gray-200';

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-5 sm:p-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
        <div>
          <h3 className="text-base font-bold text-[#1e3a5f] tracking-tight">
            FREIGHT PRICE FORECAST
          </h3>
          <p className="text-xs text-gray-400">
            Route-calibrated Baltic index and bunker trajectory across forward horizons.
          </p>
        </div>

        {/* Delta badge */}
        {deltaAbs > 0.1 && (
          <div className={`inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-full border ${deltaColor} self-start sm:self-auto`}>
            {isLower ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />}
            <span>Forecast is {deltaAbs.toFixed(1)}% {isLower ? 'below' : 'above'} current rate</span>
          </div>
        )}
      </div>

      {/* Rate Comparison Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        {/* Current Rate Card */}
        <div className="bg-gray-50/90 rounded-lg p-4 border border-gray-100">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
              Current Freight Rate
            </span>
            {data.currentRateDate && (
              <span className="text-[11px] text-gray-400 font-medium">({data.currentRateDate})</span>
            )}
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight">
              ${data.currentRatePerMT.toFixed(2)}
            </span>
            <span className="text-sm font-semibold text-gray-400">/ MT</span>
          </div>
          <p className="text-[11px] text-gray-500 mt-1">
            {data.currentRateDataStatus === 'DERIVED_ESTIMATE'
              ? 'Derived via Voyage Economics using spot bunker & Baltic benchmark'
              : 'Market spot observation'}
          </p>
        </div>

        {/* Forecast Rate Card */}
        <div className="bg-[#f0f4ff]/90 rounded-lg p-4 border border-[#d4dff7]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-[#1e3a5f]">
              Forecast Freight Rate
            </span>
            {data.expectedRateHorizon && (
              <span className="text-[11px] text-[#1e3a5f]/70 font-semibold">({data.expectedRateHorizon})</span>
            )}
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-[#1e3a5f] tracking-tight">
              ${data.expectedRatePerMT.toFixed(2)}
            </span>
            <span className="text-sm font-semibold text-[#1e3a5f]/60">/ MT</span>
          </div>
          <p className="text-[11px] text-gray-500 mt-1">
            {data.expectedRateDataStatus === 'FORECAST'
              ? 'Forward Baltic curve projection inside selected chartering horizon'
              : 'Derived horizon estimate'}
          </p>
        </div>
      </div>

      {/* Responsive Full-Width Chart */}
      <div className="h-64 sm:h-72 w-full mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={combined} margin={{ top: 10, right: 15, left: -5, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={false}
              dy={4}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${v}`}
              width={52}
              domain={[yMin, yMax]}
            />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine
              x={todayLabel}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              label={{ value: 'Current', position: 'top', fontSize: 10, fill: '#64748b', fontWeight: 600 }}
            />
            {/* Current/Historical line (solid) */}
            <Line
              dataKey="historical"
              stroke="#1e3a5f"
              strokeWidth={2.5}
              dot={{ r: 3.5, fill: '#1e3a5f', stroke: '#fff', strokeWidth: 2 }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />
            {/* Forward Forecast line (dashed) */}
            <Line
              dataKey="forecast"
              stroke="#1e3a5f"
              strokeWidth={2.5}
              strokeDasharray="6 4"
              dot={{ r: 3.5, fill: '#fff', stroke: '#1e3a5f', strokeWidth: 2 }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Chart Footer: Legend & Analytical Signals */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 border-t border-gray-100">
        {/* Legend */}
        <div className="flex items-center gap-5 text-xs text-gray-500 font-medium">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-4 h-1 bg-[#1e3a5f] rounded-full" />
            Current Observation
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-5 border-t-2 border-dashed border-[#1e3a5f]" />
            Forward Forecast Curve
          </span>
        </div>

        {/* Signals */}
        <div className="flex flex-wrap items-center gap-3.5">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-medium">Trend:</span>
            <TrendBadge trend={data.trend} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-medium" title="Evaluates forward data coverage & stability">
              Signal:
            </span>
            <ForecastSignalBadge
              level={data.forecastSignalLabel}
              detail={data.forecastSignal?.detail}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
