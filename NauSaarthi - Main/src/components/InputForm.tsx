import { useState, useRef, useEffect, type FormEvent } from 'react';
import { ChevronDown, Search, ArrowRight, Package } from 'lucide-react';
import type { CargoRequirement, CharteringWindowOption } from '../types';
import { ORIGIN_OPTIONS, DESTINATION_PORTS, CHARTERING_WINDOW_LABELS } from '../data/locations';

interface InputFormProps {
  initialValues?: Partial<CargoRequirement>;
  onSubmit: (data: CargoRequirement) => void;
}

// ─── Searchable Dropdown ───────────────────────────────────────────────

function SearchableDropdown({
  label,
  helper,
  placeholder,
  options,
  value,
  onChange,
  error,
  id,
}: {
  label: string;
  helper: string;
  placeholder: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  error?: string;
  id: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filtered = options.filter((o) =>
    o.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div ref={ref} className="relative">
      <label htmlFor={id} className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
        {label}
      </label>
      <p className="text-[11px] text-gray-400 mb-1.5 leading-tight">{helper}</p>
      <button
        type="button"
        id={id}
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-3.5 py-2.5 bg-white border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/20 focus:border-[#1e3a5f] cursor-pointer ${
          error ? 'border-red-300 bg-red-50/20' : 'border-gray-300/80 hover:border-gray-400'
        }`}
      >
        <span className={value ? 'text-gray-900 font-medium' : 'text-gray-400'}>
          {value || placeholder}
        </span>
        <ChevronDown className="w-4 h-4 text-gray-400" />
      </button>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}

      {open && (
        <div className="dropdown-menu">
          <div className="sticky top-0 bg-white p-2 border-b border-gray-100">
            <div className="flex items-center gap-2 px-2 py-1.5 bg-gray-50 rounded-md">
              <Search className="w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="flex-1 bg-transparent text-sm outline-none placeholder-gray-400"
                autoFocus
              />
            </div>
          </div>
          {filtered.length === 0 && (
            <div className="px-4 py-3 text-sm text-gray-400">No results found</div>
          )}
          {filtered.map((opt) => (
            <div
              key={opt}
              className={`dropdown-item ${opt === value ? 'selected' : ''}`}
              onClick={() => {
                onChange(opt);
                setOpen(false);
                setSearch('');
              }}
            >
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Input Form ───────────────────────────────────────────────────

export default function InputForm({ initialValues, onSubmit }: InputFormProps) {
  const [cargoQty, setCargoQty] = useState(
    initialValues?.cargoQuantityMT?.toLocaleString() ?? '95,000'
  );
  const [origin, setOrigin] = useState(initialValues?.origin ?? 'Australia');
  const [destination, setDestination] = useState(initialValues?.destination ?? 'Paradip');
  const [window, setWindow] = useState<CharteringWindowOption | ''>(
    initialValues?.charteringWindow ?? 'within_30_days'
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  const originOptions = ORIGIN_OPTIONS.map((o) => o.country);
  const destinationOptions = DESTINATION_PORTS.map((p) => p.name);

  function formatNumber(raw: string): string {
    const digits = raw.replace(/[^0-9]/g, '');
    if (!digits) return '';
    return Number(digits).toLocaleString();
  }

  function validate(): Record<string, string> {
    const e: Record<string, string> = {};
    const qty = Number(cargoQty.replace(/,/g, ''));
    if (!cargoQty || isNaN(qty) || qty <= 0) {
      e.cargoQty = 'Please enter a valid cargo quantity.';
    }
    if (!origin) e.origin = 'Please select an origin.';
    if (!destination) e.destination = 'Please select a destination port.';
    if (!window) e.window = 'Please select a chartering window.';
    return e;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    onSubmit({
      cargoQuantityMT: Number(cargoQty.replace(/,/g, '')),
      origin,
      destination,
      charteringWindow: window as CharteringWindowOption,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 sm:p-8">
        <div className="border-b border-gray-100 pb-4 mb-6">
          <h2 className="text-lg sm:text-xl font-bold text-[#1e3a5f] tracking-tight">
            CHARTERING REQUIREMENT
          </h2>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">
            Specify bulk shipment volume, shipping corridor, and execution timeline for real-time voyage feasibility analysis.
          </p>
        </div>

        <div className="space-y-6">
          {/* Cargo Quantity */}
          <div>
            <label htmlFor="cargo-qty" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
              Cargo Quantity
            </label>
            <p className="text-[11px] text-gray-400 mb-1.5">
              Enter total bulk cargo parcel size in metric tonnes (MT).
            </p>
            <div className="flex rounded-lg shadow-2xs">
              <span className="inline-flex items-center px-3.5 bg-gray-50 border border-r-0 border-gray-300/80 rounded-l-lg text-gray-400">
                <Package className="w-4 h-4" />
              </span>
              <input
                id="cargo-qty"
                type="text"
                inputMode="numeric"
                value={cargoQty}
                onChange={(e) => setCargoQty(formatNumber(e.target.value))}
                placeholder="e.g. 95,000"
                className={`flex-1 px-3.5 py-2.5 bg-white border text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/20 focus:border-[#1e3a5f] font-medium ${
                  errors.cargoQty ? 'border-red-300 bg-red-50/20' : 'border-gray-300/80'
                }`}
              />
              <span className="inline-flex items-center px-4 py-2.5 bg-gray-100/70 border border-l-0 border-gray-300/80 rounded-r-lg text-xs font-bold text-gray-600">
                MT
              </span>
            </div>
            {errors.cargoQty && (
              <p className="text-xs text-red-500 mt-1">{errors.cargoQty}</p>
            )}
          </div>

          {/* 2-Column Route Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
            <SearchableDropdown
              id="origin"
              label="Loading / Origin"
              helper="Overseas loading terminal."
              placeholder="Select origin country"
              options={originOptions}
              value={origin}
              onChange={setOrigin}
              error={errors.origin}
            />

            <SearchableDropdown
              id="destination"
              label="Discharge / Destination Port"
              helper="Indian discharge port."
              placeholder="Select destination port"
              options={destinationOptions}
              value={destination}
              onChange={setDestination}
              error={errors.destination}
            />
          </div>

          {/* Chartering Window */}
          <div>
            <label htmlFor="window" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
              Required Chartering Window
            </label>
            <p className="text-[11px] text-gray-400 mb-2">
              Select your commercial fixture planning horizon.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {(Object.entries(CHARTERING_WINDOW_LABELS) as [CharteringWindowOption, string][]).map(
                ([key, label]) => {
                  if (key === 'custom') return null;
                  const isSelected = window === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setWindow(key)}
                      className={`px-3 py-2.5 text-xs sm:text-sm rounded-lg border transition-all cursor-pointer text-center font-medium ${
                        isSelected
                          ? 'border-[#1e3a5f] bg-[#1e3a5f] text-white shadow-xs font-semibold'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {label}
                    </button>
                  );
                }
              )}
            </div>
            {errors.window && (
              <p className="text-xs text-red-500 mt-1.5">{errors.window}</p>
            )}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="mt-8 w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-[#1e3a5f] text-white text-sm font-semibold rounded-lg hover:bg-[#162d4a] active:bg-[#0f2137] shadow-sm transition-all cursor-pointer hover:shadow-md"
        >
          Analyze with NauSaarthi
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
