"use client";

/**
 * LocationPicker — viloyat + tuman/shahar tanlash komponenti.
 *
 * UX oqimi:
 *  1. Bosish → viloyatlar ro'yxati ochiladi
 *  2. Viloyat bosish → tumanlar ko'rinadi
 *  3. "Barcha tumanlar" → faqat viloyat (tuman yo'q)
 *  4. Tuman bosish → tanlash yakunlanadi, yopiladi
 *  5. Tashqariga bosish (backdrop) → yopiladi
 */

import { useState } from "react";
import { MapPin, ChevronLeft, ChevronRight, Check, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { useRegions } from "@/hooks/useRegions";
import { useDistricts } from "@/hooks/useDistricts";
import type { Region, District } from "@/types";

// ─── Turlari ─────────────────────────────────────────────────────────────────

export interface LocationValue {
  regionId:     number | null;
  regionName:   string;
  districtId:   number | null;
  districtName: string;
}

export const EMPTY_LOCATION: LocationValue = {
  regionId: null, regionName: "",
  districtId: null, districtName: "",
};

interface LocationPickerProps {
  value:        LocationValue;
  onChange:     (val: LocationValue) => void;
  placeholder?: string;
  compact?:     boolean;
  className?:   string;
  error?:       string;
}

// ─── Komponent ───────────────────────────────────────────────────────────────

export default function LocationPicker({
  value,
  onChange,
  placeholder = "Viloyat tanlang",
  compact = false,
  className,
  error,
}: LocationPickerProps) {
  const { data: regions = [] } = useRegions();

  const [open, setOpen]     = useState(false);
  const [step, setStep]     = useState<"region" | "district">("region");
  const [pendingId, setPendingId] = useState<number | null>(null);

  const { data: districts = [], isLoading: distLoading } = useDistricts(pendingId);

  // ── Yopish ────────────────────────────────────────────────────────────────
  function close() {
    setOpen(false);
  }

  // ── Ochish ────────────────────────────────────────────────────────────────
  function open_() {
    setPendingId(value.regionId);
    setStep("region");
    setOpen(true);
  }

  // ── Viloyat tanlash ───────────────────────────────────────────────────────
  function pickRegion(r: Region) {
    setPendingId(r.id);
    setStep("district");
  }

  // ── Faqat viloyat (tuman yo'q) ────────────────────────────────────────────
  function pickOnlyRegion() {
    const r = regions.find((x) => x.id === pendingId);
    if (!r) return;
    onChange({ regionId: r.id, regionName: r.name_uz, districtId: null, districtName: "" });
    close();
  }

  // ── Viloyat + tuman ───────────────────────────────────────────────────────
  function pickDistrict(d: District) {
    const r = regions.find((x) => x.id === pendingId);
    if (!r) return;
    onChange({ regionId: r.id, regionName: r.name_uz, districtId: d.id, districtName: d.name_uz });
    close();
  }

  // ── Tozalash ──────────────────────────────────────────────────────────────
  function clearValue(e: React.MouseEvent) {
    e.stopPropagation();
    onChange(EMPTY_LOCATION);
  }

  // ── Ko'rsatiladigan matn ──────────────────────────────────────────────────
  const display = value.regionName
    ? value.districtName
      ? `${value.regionName}, ${value.districtName}`
      : value.regionName
    : "";

  const pendingRegionName = regions.find((r) => r.id === pendingId)?.name_uz ?? "";

  return (
    <>
      {/* Backdrop — tashqariga bosish yopadi */}
      {open && (
        <div
          className="fixed inset-0 z-40"
          onClick={close}
        />
      )}

      <div className={clsx("relative", className)}>
        {/* ── Trigger ── */}
        <div
          role="button"
          tabIndex={0}
          onClick={open_}
          onKeyDown={(e) => e.key === "Enter" && open_()}
          className={clsx(
            "flex items-center gap-2 cursor-pointer w-full outline-none",
            compact ? "py-2.5" : "py-3"
          )}
        >
          <MapPin
            size={compact ? 14 : 15}
            className={clsx("shrink-0", error ? "text-red-400" : "text-gray-400")}
          />
          <span
            className={clsx(
              "flex-1 min-w-0 truncate select-none",
              compact ? "text-sm" : "text-base",
              display ? "text-gray-900" : "text-gray-400"
            )}
          >
            {display || placeholder}
          </span>
          {display && (
            <span
              role="button"
              tabIndex={-1}
              onClick={clearValue}
              className="shrink-0 w-5 h-5 flex items-center justify-center rounded-full text-gray-300 hover:bg-gray-100 hover:text-gray-500 transition-colors cursor-pointer text-base leading-none"
            >
              ×
            </span>
          )}
        </div>

        {error && <p className="text-xs text-red-500 mt-1 -mt-1">{error}</p>}

        {/* ── Dropdown paneli ── */}
        {open && (
          <div
            className={clsx(
              "absolute left-0 top-full mt-1 bg-white rounded-2xl border border-gray-100",
              "shadow-[0_8px_32px_rgba(0,0,0,0.12)] z-50 overflow-hidden",
              compact ? "w-72" : "w-80"
            )}
          >
            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 bg-gray-50">
              {step === "district" && (
                <button
                  type="button"
                  onClick={() => setStep("region")}
                  className="p-1 rounded-lg hover:bg-gray-200 text-gray-500 transition-colors"
                >
                  <ChevronLeft size={16} />
                </button>
              )}
              <span className="text-sm font-semibold text-gray-900 flex-1">
                {step === "region" ? "Viloyat tanlang" : pendingRegionName}
              </span>
              {step === "district" && (
                <span className="text-xs text-gray-400 bg-gray-200 px-2 py-0.5 rounded-full">
                  ixtiyoriy
                </span>
              )}
            </div>

            {/* ── Viloyatlar ── */}
            {step === "region" && (
              <ul className="max-h-72 overflow-y-auto py-1">
                {regions.length === 0 ? (
                  <li className="py-6 text-center text-sm text-gray-400">
                    <Loader2 size={18} className="animate-spin mx-auto mb-1" />
                    Yuklanmoqda...
                  </li>
                ) : (
                  regions.map((r) => {
                    const active = value.regionId === r.id && !value.districtName;
                    return (
                      <li key={r.id}>
                        <button
                          type="button"
                          onClick={() => pickRegion(r)}
                          className={clsx(
                            "w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors",
                            active
                              ? "bg-primary-50 text-primary-700 font-medium"
                              : "text-gray-700 hover:bg-gray-50"
                          )}
                        >
                          <MapPin size={13} className="text-gray-300 shrink-0" />
                          <span className="flex-1">{r.name_uz}</span>
                          {active
                            ? <Check size={13} className="text-primary-500 shrink-0" />
                            : <ChevronRight size={13} className="text-gray-300 shrink-0" />
                          }
                        </button>
                      </li>
                    );
                  })
                )}
              </ul>
            )}

            {/* ── Tumanlar ── */}
            {step === "district" && (
              <ul className="max-h-72 overflow-y-auto py-1">
                {/* Barcha tumanlar — faqat viloyat */}
                <li>
                  <button
                    type="button"
                    onClick={pickOnlyRegion}
                    className={clsx(
                      "w-full flex items-center gap-3 px-4 py-3 text-sm text-left border-b border-gray-100 transition-colors",
                      !value.districtId && value.regionId === pendingId
                        ? "bg-primary-50 text-primary-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50"
                    )}
                  >
                    <MapPin size={13} className="text-gray-400 shrink-0" />
                    <span className="flex-1">Barcha tumanlar</span>
                    {!value.districtId && value.regionId === pendingId && (
                      <Check size={13} className="text-primary-500 shrink-0" />
                    )}
                  </button>
                </li>

                {distLoading ? (
                  <li className="py-6 flex justify-center">
                    <Loader2 size={20} className="animate-spin text-primary-400" />
                  </li>
                ) : districts.length === 0 ? (
                  <li className="px-4 py-5 text-sm text-gray-400 text-center">
                    Tumanlar topilmadi
                  </li>
                ) : (
                  districts.map((d) => {
                    const active = value.districtId === d.id && value.regionId === pendingId;
                    return (
                      <li key={d.id}>
                        <button
                          type="button"
                          onClick={() => pickDistrict(d)}
                          className={clsx(
                            "w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors",
                            active
                              ? "bg-primary-50 text-primary-700 font-medium"
                              : "text-gray-700 hover:bg-gray-50"
                          )}
                        >
                          <span className="w-3 shrink-0" />
                          <span className="flex-1">{d.name_uz}</span>
                          {active && <Check size={13} className="text-primary-500 shrink-0" />}
                        </button>
                      </li>
                    );
                  })
                )}
              </ul>
            )}
          </div>
        )}
      </div>
    </>
  );
}
