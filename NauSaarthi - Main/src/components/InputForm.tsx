import { useState, useRef, useEffect, type FormEvent } from 'react';
import { ChevronDown, Search, ArrowRight, Loader2 } from 'lucide-react';
import type { CargoRequirement, CharteringWindowOption } from '../types';
import { ORIGIN_OPTIONS, DESTINATION_PORTS, CHARTERING_WINDOW_LABELS } from '../data/locations';

interface InputFormProps {
  initialValues?: Partial<CargoRequirement>;
  onSubmit: (data: CargoRequirement) => void;
  loading?: boolean;
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
      <label htmlFor={id} className="block text-sm font-semibold text-gray-700 mb-1">
        {label}
      </label>
      <p className="text-xs text-gray-400 mb-2 h-4">{helper}</p>
      <button
        type="button"
        id={id}
        onClick={() => setOpen(!open)}
        className={`w-full h-11 flex items-center justify-between px-4 bg-white border rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/20 focus:border-[#1e3a5f] ${
          error ? 'border-red-300' : 'border-gray-200 hover:border-gray-300'
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

export default function InputForm({ initialValues, onSubmit, loading = false }: InputFormProps) {
  const [cargoQty, setCargoQty] = useState(
    initialValues?.cargoQuantityMT?.toLocaleString() ?? '75,000'
  );
  const [origin, setOrigin] = useState(initialValues?.origin ?? 'Australia');
  const [destination, setDestination] = useState(initialValues?.destination ?? 'Dhamra');
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
    if (qty > 500000) {
      e.cargoQty = 'Cargo quantity cannot exceed 500,000 MT.';
    }
    if (!origin) e.origin = 'Please select an origin.';
    if (!destination) e.destination = 'Please select a destination port.';
    if (!window) e.window = 'Please select a chartering window.';
    return e;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (loading) return;

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
    <form onSubmit={handleSubmit} className="w-full max-w-4xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200/90 shadow-sm p-7 sm:p-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-8">
          <div>
            <h2 className="text-xl font-bold text-[#1e3a5f]">Chartering Requirement</h2>
            <p className="text-sm text-gray-500 mt-1">
              Enter your cargo and route details to analyse freight price, vessel suitability, and ideal chartering time.
            </p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Cargo Quantity */}
          <div>
            <label htmlFor="cargo-qty" className="block text-sm font-semibold text-gray-700 mb-1">
              Cargo Quantity
            </label>
            <p className="text-xs text-gray-400 mb-2">
              Enter the quantity of cargo (coal) to be imported in metric tonnes.
            </p>
            <div className="flex max-w-md">
              <input
                id="cargo-qty"
                type="text"
                inputMode="numeric"
                value={cargoQty}
                onChange={(e) => setCargoQty(formatNumber(e.target.value))}
                placeholder="e.g. 75,000"
                className={`flex-1 h-11 px-4 bg-white border rounded-l-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/20 focus:border-[#1e3a5f] ${
                  errors.cargoQty ? 'border-red-300' : 'border-gray-200 hover:border-gray-300'
                }`}
              />
              <span className="inline-flex items-center px-4 h-11 bg-gray-50 border border-l-0 border-gray-200 rounded-r-lg text-sm font-semibold text-gray-600">
                MT
              </span>
            </div>
            {errors.cargoQty && (
              <p className="text-xs text-red-500 mt-1">{errors.cargoQty}</p>
            )}
          </div>

          {/* Origin and Destination side by side on wider screens */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Origin */}
            <SearchableDropdown
              id="origin"
              label="Loading / Origin"
              helper="Country where the cargo will be loaded."
              placeholder="Select origin country"
              options={originOptions}
              value={origin}
              onChange={(val) => {
                setOrigin(val);
                if (errors.route) setErrors((prev) => { const n = { ...prev }; delete n.route; return n; });
              }}
              error={errors.origin}
            />

            {/* Destination */}
            <SearchableDropdown
              id="destination"
              label="Discharge / Destination Port"
              helper="East Coast Indian port for cargo arrival."
              placeholder="Select destination port"
              options={destinationOptions}
              value={destination}
              onChange={(val) => {
                setDestination(val);
                if (errors.route) setErrors((prev) => { const n = { ...prev }; delete n.route; return n; });
              }}
              error={errors.destination}
            />
          </div>

          {errors.route && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
              {errors.route}
            </div>
          )}

          {/* Chartering Window */}
          <div>
            <label htmlFor="window" className="block text-sm font-semibold text-gray-700 mb-1">
              Required Chartering Window
            </label>
            <p className="text-xs text-gray-400 mb-2">
              When do you expect to charter the vessel?
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {(Object.entries(CHARTERING_WINDOW_LABELS) as [CharteringWindowOption, string][])
                .filter(([key]) => key !== 'custom')
                .map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setWindow(key)}
                    className={`h-11 px-3 text-sm rounded-lg border transition-all ${
                      window === key
                        ? 'border-[#1e3a5f] bg-[#eef2ff] text-[#1e3a5f] font-semibold ring-1 ring-[#1e3a5f]'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
            </div>
            {errors.window && (
              <p className="text-xs text-red-500 mt-1.5">{errors.window}</p>
            )}
          </div>
        </div>

        {/* Submit Section */}
        <div className="mt-9">
          <button
            type="submit"
            disabled={loading}
            className={`w-full h-12 flex items-center justify-center gap-2 px-6 text-white text-sm font-semibold rounded-xl transition-all shadow-sm ${
              loading
                ? 'bg-[#1e3a5f]/70 cursor-not-allowed'
                : 'bg-[#1e3a5f] hover:bg-[#162d4a] active:bg-[#0f2137] hover:shadow'
            }`}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing with NauSaathi...
              </>
            ) : (
              <>
                Analyze with NauSaathi
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
