"use client";

import { useState } from "react";
import { SlidersHorizontal, X, Wind, Luggage, ChevronDown } from "lucide-react";
import { clsx } from "clsx";
import Button from "@/components/ui/Button";

interface Filters {
  maxPrice: number;
  departureFrom: string;
  departureTo: string;
  amenities: { ac: boolean; luggage: boolean };
  minRating: number;
}

const DEFAULT: Filters = {
  maxPrice: 500_000,
  departureFrom: "00:00",
  departureTo: "23:59",
  amenities: { ac: false, luggage: false },
  minRating: 0,
};

interface TripFiltersProps {
  onChange?: (filters: Filters) => void;
  totalCount?: number;
}

const TIME_SLOTS = [
  { label: "Ertalab",    from: "05:00", to: "11:59", icon: "🌅" },
  { label: "Tushdan keyin", from: "12:00", to: "17:59", icon: "☀️" },
  { label: "Kechqurun",  from: "18:00", to: "23:59", icon: "🌆" },
  { label: "Kechasi",    from: "00:00", to: "04:59", icon: "🌙" },
];

const RATINGS = [
  { value: 0, label: "Barchasi" },
  { value: 4, label: "4+ ★" },
  { value: 4.5, label: "4.5+ ★" },
];

export default function TripFilters({ onChange, totalCount }: TripFiltersProps) {
  const [filters, setFilters] = useState<Filters>(DEFAULT);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [priceExpanded, setPriceExpanded] = useState(true);
  const [timeExpanded, setTimeExpanded] = useState(true);

  function update(partial: Partial<Filters>) {
    const next = { ...filters, ...partial };
    setFilters(next);
    onChange?.(next);
  }

  const hasActiveFilters =
    filters.maxPrice < 500_000 ||
    filters.amenities.ac ||
    filters.amenities.luggage ||
    filters.minRating > 0;

  function reset() {
    setFilters(DEFAULT);
    onChange?.(DEFAULT);
  }

  const content = (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={16} className="text-gray-500" />
          <span className="text-sm font-semibold text-gray-900">Filtrlar</span>
          {hasActiveFilters && (
            <span className="w-2 h-2 bg-primary-500 rounded-full" />
          )}
        </div>
        {hasActiveFilters && (
          <button onClick={reset} className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1">
            <X size={12} />Tozalash
          </button>
        )}
      </div>

      {/* Price */}
      <div>
        <button
          onClick={() => setPriceExpanded(p => !p)}
          className="flex items-center justify-between w-full mb-3"
        >
          <span className="text-sm font-medium text-gray-700">Maksimal narx</span>
          <ChevronDown size={14} className={clsx("text-gray-400 transition-transform", priceExpanded && "rotate-180")} />
        </button>
        {priceExpanded && (
          <div className="space-y-3">
            <input
              type="range"
              min={20_000}
              max={500_000}
              step={5_000}
              value={filters.maxPrice}
              onChange={(e) => update({ maxPrice: Number(e.target.value) })}
              className="w-full accent-primary-500"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>20,000 so'm</span>
              <span className="font-semibold text-gray-700">
                {new Intl.NumberFormat("uz-UZ").format(filters.maxPrice)} so'm
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Departure time */}
      <div>
        <button
          onClick={() => setTimeExpanded(p => !p)}
          className="flex items-center justify-between w-full mb-3"
        >
          <span className="text-sm font-medium text-gray-700">Jo'nash vaqti</span>
          <ChevronDown size={14} className={clsx("text-gray-400 transition-transform", timeExpanded && "rotate-180")} />
        </button>
        {timeExpanded && (
          <div className="grid grid-cols-2 gap-2">
            {TIME_SLOTS.map((slot) => {
              const active = filters.departureFrom === slot.from && filters.departureTo === slot.to;
              return (
                <button
                  key={slot.label}
                  onClick={() => update(
                    active
                      ? { departureFrom: "00:00", departureTo: "23:59" }
                      : { departureFrom: slot.from, departureTo: slot.to }
                  )}
                  className={clsx(
                    "flex items-center gap-2 px-3 py-2.5 rounded-xl text-xs font-medium border transition-all",
                    active
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-gray-100 bg-gray-50 text-gray-600 hover:border-gray-200"
                  )}
                >
                  <span>{slot.icon}</span>
                  {slot.label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Amenities */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Qulayliklar</p>
        <div className="space-y-2">
          {[
            { key: "ac" as const, icon: Wind, label: "Konditsioner" },
            { key: "luggage" as const, icon: Luggage, label: "Katta yukxalta" },
          ].map(({ key, icon: Icon, label }) => (
            <label key={key} className="flex items-center gap-3 cursor-pointer group">
              <div className={clsx(
                "w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all",
                filters.amenities[key]
                  ? "bg-primary-500 border-primary-500"
                  : "border-gray-300 group-hover:border-gray-400"
              )}>
                {filters.amenities[key] && (
                  <svg viewBox="0 0 10 8" fill="none" className="w-3 h-3">
                    <path d="M1 4L4 7L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
              <input
                type="checkbox"
                className="sr-only"
                checked={filters.amenities[key]}
                onChange={(e) => update({ amenities: { ...filters.amenities, [key]: e.target.checked } })}
              />
              <Icon size={14} className="text-gray-400" />
              <span className="text-sm text-gray-700">{label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Rating */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Minimal reyting</p>
        <div className="flex gap-2">
          {RATINGS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => update({ minRating: value })}
              className={clsx(
                "flex-1 py-2 rounded-xl text-xs font-medium border transition-all",
                filters.minRating === value
                  ? "border-primary-500 bg-primary-50 text-primary-700"
                  : "border-gray-100 bg-gray-50 text-gray-600 hover:border-gray-200"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {totalCount !== undefined && (
        <div className="pt-2 border-t border-gray-50">
          <p className="text-xs text-center text-gray-400">{totalCount} ta safar topildi</p>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-64 shrink-0">
        <div className="bg-white rounded-2xl border border-gray-100 p-5 sticky top-20">
          {content}
        </div>
      </aside>

      {/* Mobile filter button */}
      <div className="lg:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          className={clsx(
            "flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all",
            hasActiveFilters
              ? "border-primary-500 bg-primary-50 text-primary-700"
              : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
          )}
        >
          <SlidersHorizontal size={15} />
          Filtr
          {hasActiveFilters && (
            <span className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
          )}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <div className="absolute bottom-0 inset-x-0 bg-white rounded-t-3xl p-5 max-h-[85vh] overflow-y-auto animate-slide-up">
            {content}
            <div className="mt-6">
              <Button fullWidth onClick={() => setMobileOpen(false)}>
                {totalCount !== undefined ? `${totalCount} ta safarni ko'rish` : "Qo'llash"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
