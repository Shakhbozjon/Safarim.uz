"use client";

/**
 * LocationPicker — joy tanlash: ro'yxatdan yoki yozib qidirib.
 *
 * Xatti-harakat qoidalari (telefonda sinab aniqlangan):
 *  1. Maydonni bosish → faqat ro'yxat ochiladi, klaviatura CHIQMAYDI.
 *     Ko'pchilik ro'yxatdan tanlaydi; klaviatura darrov chiqsa ekranning
 *     yarmini yopib, ro'yxatni ko'rsatmay qo'yadi.
 *  2. Ro'yxat tepasida qidiruv maydoni turadi — yozmoqchi bo'lgan odam
 *     unga tegadi va klaviatura o'shanda chiqadi. U avtomatik fokus
 *     OLMAYDI (aynan shu narsa 1-qoidani buzardi).
 *  3. Viloyat qatorini bosish → uning tumanlari ochiladi. Viloyatning
 *     hammasi bo'yicha qidirish uchun ichidagi «Barcha tumanlar» qatori
 *     bosiladi — ilgari
 *     qator bosilganda viloyat tanlanib ro'yxat yopilardi, tumanlarni esa
 *     faqat yondagi kichkina belgi orqali ochish mumkin edi va buni
 *     ko'pchilik topmasdi.
 *
 * Qidiruv viloyat va tumanlarni birga qidiradi: «Quva» deb yozgan odam
 * uning qaysi viloyatda ekanini bilishi shart emas.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Loader2, MapPin, Search } from "lucide-react";
import { clsx } from "clsx";
import { normalize, useAllLocations } from "@/hooks/useLocations";

export interface LocationValue {
  regionId: number | null;
  regionName: string;
  districtId: number | null;
  districtName: string;
}

export const EMPTY_LOCATION: LocationValue = {
  regionId: null, regionName: "",
  districtId: null, districtName: "",
};

interface LocationPickerProps {
  value: LocationValue;
  onChange: (val: LocationValue) => void;
  placeholder?: string;
  compact?: boolean;
  className?: string;
  error?: string;
}

/** Qidiruv natijasidagi bitta variant */
interface Option {
  key: string;
  label: string;
  /** Tuman uchun — qaysi viloyat ekani */
  sub?: string;
  isRegion: boolean;
  value: LocationValue;
  needle: string;
}

const MAX_RESULTS = 40;

export default function LocationPicker({
  value,
  onChange,
  placeholder = "Viloyat, shahar, tuman",
  compact = false,
  className,
  error,
}: LocationPickerProps) {
  const { data: regions = [], isLoading } = useAllLocations();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [cursor, setCursor] = useState(0);

  const boxRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);

  // Tashqariga bosilsa yopiladi
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  // Barcha joylar bitta ro'yxatda — qidiruv shu bo'yicha ketadi
  const all = useMemo<Option[]>(() => {
    const out: Option[] = [];
    for (const r of regions) {
      out.push({
        key: `r${r.id}`,
        label: r.name_uz,
        isRegion: true,
        value: { regionId: r.id, regionName: r.name_uz, districtId: null, districtName: "" },
        needle: normalize(r.name_uz),
      });
      for (const d of r.districts ?? []) {
        out.push({
          key: `d${d.id}`,
          label: d.name_uz,
          isRegion: false,
          sub: r.name_uz,
          value: { regionId: r.id, regionName: r.name_uz, districtId: d.id, districtName: d.name_uz },
          needle: `${normalize(d.name_uz)} ${normalize(r.name_uz)}`,
        });
      }
    }
    return out;
  }, [regions]);

  const q = normalize(query);
  const results = useMemo(() => {
    if (!q) return [];
    // Tartib: nomi yozilgan so'zdan boshlanganlar tepada, viloyat esa o'z
    // tumanlaridan oldin
    const scored = all
      .filter((o) => o.needle.includes(q))
      .map((o) => ({
        o,
        score: (o.needle.startsWith(q) ? 0 : 2) + (o.isRegion ? 0 : 1),
      }));
    scored.sort((a, b) => a.score - b.score || a.o.label.localeCompare(b.o.label));
    return scored.slice(0, MAX_RESULTS).map((s) => s.o);
  }, [all, q]);

  useEffect(() => setCursor(0), [query]);

  const display = value.regionName
    ? value.districtName
      ? `${value.districtName}, ${value.regionName}`
      : value.regionName
    : "";

  function pick(val: LocationValue) {
    onChange(val);
    setQuery("");
    setOpen(false);
  }

  function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    setQuery("");
    setExpanded(value.regionId);   // tanlangan viloyat ochiq turadi
  }

  function onSearchKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") { setOpen(false); return; }
    if (!results.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const next = e.key === "ArrowDown"
        ? Math.min(cursor + 1, results.length - 1)
        : Math.max(cursor - 1, 0);
      setCursor(next);
      listRef.current?.children[next]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(results[cursor].value);
    }
  }

  return (
    <div ref={boxRef} className={clsx("relative", className)}>
      {/* ── Maydon: bosilganda faqat ro'yxat ochiladi (klaviatura yo'q) ── */}
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={toggle}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && toggle()}
        className={clsx(
          "flex w-full cursor-pointer items-center gap-2 outline-none",
          compact ? "py-2.5" : "py-3"
        )}
      >
        <MapPin
          size={compact ? 15 : 17}
          className={clsx("shrink-0", error ? "text-red-400" : "text-primary-500")}
        />
        <span
          className={clsx(
            "min-w-0 flex-1 select-none truncate",
            compact ? "text-sm" : "text-base",
            display ? "font-semibold text-gray-900" : "text-gray-500"
          )}
        >
          {display || placeholder}
        </span>
        {display && (
          <span
            role="button"
            tabIndex={-1}
            onClick={(e) => { e.stopPropagation(); onChange(EMPTY_LOCATION); }}
            className="flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded-full text-base leading-none text-gray-300 transition-colors hover:bg-gray-100 hover:text-gray-500"
            aria-label="Tozalash"
          >
            ×
          </span>
        )}
      </div>

      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}

      {/* ── Ro'yxat ── */}
      {open && (
        <div
          className={clsx(
            "absolute left-0 top-full z-50 mt-1 overflow-hidden rounded-2xl border border-gray-100 bg-white",
            "shadow-[0_8px_32px_rgba(0,0,0,0.12)]",
            compact ? "w-72" : "w-80",
            "max-w-[calc(100vw-2rem)]"
          )}
        >
          {/* Qidiruv maydoni — avtomatik fokus OLMAYDI: klaviatura faqat
              foydalanuvchi shu yerga tekkanda chiqadi */}
          <div className="border-b border-gray-100 p-2">
            <label className="flex items-center gap-2 rounded-xl bg-gray-100 px-3 py-2.5 focus-within:bg-white focus-within:ring-2 focus-within:ring-primary-500/30">
              <Search size={15} className="shrink-0 text-gray-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onSearchKeyDown}
                placeholder="Qidirish: viloyat, shahar, tuman"
                className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-gray-400"
                aria-label="Joy qidirish"
                autoComplete="off"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  aria-label="Qidiruvni tozalash"
                  className="shrink-0 text-gray-300 hover:text-gray-500"
                >
                  ×
                </button>
              )}
            </label>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 size={20} className="animate-spin text-primary-400" />
            </div>
          ) : q ? (
            // ── Qidiruv natijalari ──
            results.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-gray-400">
                «{query}» topilmadi
              </p>
            ) : (
              <ul ref={listRef} className="max-h-64 overflow-y-auto py-1">
                {results.map((o, i) => (
                  <li key={o.key}>
                    <button
                      type="button"
                      onMouseEnter={() => setCursor(i)}
                      onClick={() => pick(o.value)}
                      className={clsx(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors",
                        i === cursor ? "bg-primary-50" : "hover:bg-gray-50"
                      )}
                    >
                      <MapPin size={13} className="shrink-0 text-gray-300" />
                      <span className="min-w-0 flex-1">
                        <span className="text-gray-900">{o.label}</span>
                        {o.sub && <span className="ml-1.5 text-xs text-gray-400">{o.sub}</span>}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )
          ) : (
            // ── Viloyatlar: qatorni bosish tumanlarni ochadi ──
            <ul className="max-h-64 overflow-y-auto py-1">
              {regions.map((r) => {
                const isOpen = expanded === r.id;
                const chosen = value.regionId === r.id;
                const districts = r.districts ?? [];
                return (
                  <li key={r.id}>
                    <button
                      type="button"
                      onClick={() =>
                        districts.length
                          ? setExpanded(isOpen ? null : r.id)
                          : pick({ regionId: r.id, regionName: r.name_uz, districtId: null, districtName: "" })
                      }
                      aria-expanded={isOpen}
                      className={clsx(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors",
                        isOpen ? "bg-gray-50 font-medium text-gray-900" : "text-gray-700 hover:bg-gray-50"
                      )}
                    >
                      <MapPin
                        size={13}
                        className={clsx("shrink-0", chosen ? "text-primary-500" : "text-gray-300")}
                      />
                      <span className="min-w-0 flex-1 truncate">{r.name_uz}</span>
                      {districts.length > 0 && (
                        <ChevronDown
                          size={15}
                          className={clsx(
                            "shrink-0 text-gray-300 transition-transform",
                            isOpen && "rotate-180"
                          )}
                        />
                      )}
                    </button>

                    {isOpen && (
                      <ul className="bg-gray-50/70 py-1">
                        {/* Barcha tumanlar — viloyat bo'yicha, tumansiz qidirish */}
                        <li>
                          <button
                            type="button"
                            onClick={() => pick({
                              regionId: r.id, regionName: r.name_uz,
                              districtId: null, districtName: "",
                            })}
                            className={clsx(
                              "flex w-full items-center gap-2 py-2 pl-11 pr-4 text-left text-[13px] transition-colors",
                              chosen && !value.districtId
                                ? "font-semibold text-primary-700"
                                : "font-medium text-primary-600 hover:text-primary-700"
                            )}
                          >
                            <span className="flex-1">Barcha tumanlar</span>
                            {chosen && !value.districtId && (
                              <Check size={12} className="shrink-0 text-primary-500" />
                            )}
                          </button>
                        </li>

                        {districts.map((d) => {
                          const active = value.districtId === d.id;
                          return (
                            <li key={d.id}>
                              <button
                                type="button"
                                onClick={() => pick({
                                  regionId: r.id, regionName: r.name_uz,
                                  districtId: d.id, districtName: d.name_uz,
                                })}
                                className={clsx(
                                  "flex w-full items-center gap-2 py-2 pl-11 pr-4 text-left text-[13px] transition-colors",
                                  active ? "font-medium text-primary-700" : "text-gray-600 hover:text-gray-900"
                                )}
                              >
                                <span className="min-w-0 flex-1 truncate">{d.name_uz}</span>
                                {active && <Check size={12} className="shrink-0 text-primary-500" />}
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
