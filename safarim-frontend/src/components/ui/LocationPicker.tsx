"use client";

/**
 * LocationPicker — joyni yozib qidirib tanlash.
 *
 * ⚠️ Ilgari bu ikki bosqichli ro'yxat edi: avval viloyat, keyin tuman.
 * Maydonda esa «Viloyat, shahar, tuman» deb yozilgani uchun odam «Quva» deb
 * yozmoqchi bo'lardi va hech narsa topa olmasdi — qaysi viloyatda ekanini
 * bilishi shart edi. Endi bitta ro'yxat: yozilgan zahoti viloyat ham, tuman
 * ham qidiriladi; hech narsa yozilmasa viloyatlar ro'yxati turadi va har
 * birini ochib tumanlarini ko'rish mumkin.
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

/** Ro'yxatdagi bitta variant */
interface Option {
  key: string;
  label: string;
  /** Tuman uchun — qaysi viloyat ekani (viloyatning o'zida bo'sh) */
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
  const inputRef = useRef<HTMLInputElement | null>(null);
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
    // Tartib: nomi yozilgan so'zdan boshlanganlar tepada, viloyat o'z
    // tumanlaridan oldin ("Farg'ona" deb yozgan odam avval viloyatning
    // o'zini ko'rsin, keyin uning tumanlarini)
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

  function choose(opt: Option) {
    onChange(opt.value);
    setQuery("");
    setOpen(false);
  }

  function openList() {
    if (open) return;
    setOpen(true);
    setQuery("");
    setExpanded(value.regionId);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
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
      choose(results[cursor]);
    }
  }

  return (
    <div ref={boxRef} className={clsx("relative", className)}>
      {/* ── Maydon ──
          ⚠️ Input DOIM shu yerda turadi va faqat ochilganda paydo bo'lmaydi.
          Ilgari ro'yxat ochilgach input yaratilib, unga kechikish bilan fokus
          berilardi — iPhone'da bunday fokus klaviaturani ochmaydi (Safari
          faqat bevosita tegishga javob beradi), shuning uchun odam ikkinchi
          marta bosishga majbur bo'lardi. Endi bir tegish yetadi. */}
      <div
        className={clsx(
          "flex w-full cursor-text items-center gap-2",
          compact ? "py-2.5" : "py-3"
        )}
      >
        {open ? (
          <Search size={compact ? 15 : 17} className="shrink-0 text-primary-500" />
        ) : (
          <MapPin
            size={compact ? 15 : 17}
            className={clsx("shrink-0", error ? "text-red-400" : "text-primary-500")}
          />
        )}

        <input
          ref={inputRef}
          value={open ? query : display}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={openList}
          onKeyDown={onKeyDown}
          placeholder={open && display ? display : placeholder}
          className={clsx(
            "min-w-0 flex-1 cursor-text bg-transparent outline-none placeholder:font-normal placeholder:text-gray-400",
            compact ? "text-sm" : "text-base",
            !open && display ? "font-semibold text-gray-900" : "text-gray-900"
          )}
          aria-label="Viloyat, shahar yoki tuman qidirish"
          aria-expanded={open}
          role="combobox"
          aria-controls="location-list"
          autoComplete="off"
        />

        {display && !open && (
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
          {/* Yo'riqnoma ro'yxatdan OLDIN: odam viloyatlar ro'yxatini ko'rib,
              yozish mumkinligini bilmay qolmasin */}
          {!q && !isLoading && (
            <p className="flex items-center gap-1.5 border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-[11.5px] text-gray-500">
              <Search size={12} className="shrink-0 text-gray-400" />
              Yozib qidiring: viloyat, shahar yoki tuman nomi
            </p>
          )}

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 size={20} className="animate-spin text-primary-400" />
            </div>
          ) : q ? (
            // ── Qidiruv natijalari (viloyat ham, tuman ham) ──
            results.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-gray-400">
                «{query}» topilmadi
              </p>
            ) : (
              <ul id="location-list" ref={listRef} className="max-h-72 overflow-y-auto py-1">
                {results.map((o, i) => (
                  <li key={o.key}>
                    <button
                      type="button"
                      onMouseEnter={() => setCursor(i)}
                      onClick={() => choose(o)}
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
            // ── Bo'sh holat: viloyatlar, har biri ochiladi ──
            <ul className="max-h-72 overflow-y-auto py-1">
              {regions.map((r) => {
                const isOpen = expanded === r.id;
                const chosen = value.regionId === r.id && !value.districtId;
                return (
                  <li key={r.id}>
                    <div className="flex items-stretch">
                      <button
                        type="button"
                        onClick={() => choose({
                          key: `r${r.id}`, label: r.name_uz, needle: "", isRegion: true,
                          value: { regionId: r.id, regionName: r.name_uz, districtId: null, districtName: "" },
                        })}
                        className={clsx(
                          "flex min-w-0 flex-1 items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors",
                          chosen ? "bg-primary-50 font-medium text-primary-700" : "text-gray-700 hover:bg-gray-50"
                        )}
                      >
                        <MapPin size={13} className="shrink-0 text-gray-300" />
                        <span className="flex-1 truncate">{r.name_uz}</span>
                        {chosen && <Check size={13} className="shrink-0 text-primary-500" />}
                      </button>
                      {(r.districts?.length ?? 0) > 0 && (
                        <button
                          type="button"
                          onClick={() => setExpanded(isOpen ? null : r.id)}
                          aria-label={`${r.name_uz} tumanlari`}
                          className="px-3 text-gray-300 transition-colors hover:bg-gray-50 hover:text-gray-500"
                        >
                          <ChevronDown
                            size={15}
                            className={clsx("transition-transform", isOpen && "rotate-180")}
                          />
                        </button>
                      )}
                    </div>

                    {isOpen && (
                      <ul className="bg-gray-50/60 py-1">
                        {(r.districts ?? []).map((d) => {
                          const active = value.districtId === d.id;
                          return (
                            <li key={d.id}>
                              <button
                                type="button"
                                onClick={() => choose({
                                  key: `d${d.id}`, label: d.name_uz, needle: "", isRegion: false,
                                  value: {
                                    regionId: r.id, regionName: r.name_uz,
                                    districtId: d.id, districtName: d.name_uz,
                                  },
                                })}
                                className={clsx(
                                  "flex w-full items-center gap-3 py-2 pl-11 pr-4 text-left text-[13px] transition-colors",
                                  active ? "font-medium text-primary-700" : "text-gray-600 hover:text-gray-900"
                                )}
                              >
                                <span className="flex-1 truncate">{d.name_uz}</span>
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
