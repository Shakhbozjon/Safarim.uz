"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftRight, Calendar, ChevronDown, Users, Search } from "lucide-react";
import Button from "@/components/ui/Button";
import LocationPicker, { LocationValue, EMPTY_LOCATION } from "@/components/ui/LocationPicker";
import { dateLabel, isoOf } from "@/lib/date";

const LABEL = "block text-[14px] font-bold text-gray-800 mb-1";

interface SearchBarProps {
  compact?:          boolean;
  defaultFromId?:    number;
  defaultToId?:      number;
  defaultFromName?:  string;
  defaultToName?:    string;
  defaultFromDistrictId?:   number;
  defaultToDistrictId?:     number;
  defaultFromDistrictName?: string;
  defaultToDistrictName?:   string;
  defaultDate?:      string;
  defaultSeats?:     number;
}

export default function SearchBar({
  compact = false,
  defaultFromId,
  defaultToId,
  defaultFromName        = "",
  defaultToName          = "",
  defaultFromDistrictId,
  defaultToDistrictId,
  defaultFromDistrictName = "",
  defaultToDistrictName   = "",
  defaultDate    = "",
  defaultSeats   = 1,
}: SearchBarProps) {
  const router = useRouter();

  const [from, setFrom] = useState<LocationValue>({
    regionId:     defaultFromId     ?? null,
    regionName:   defaultFromName,
    districtId:   defaultFromDistrictId  ?? null,
    districtName: defaultFromDistrictName,
  });
  const [to, setTo] = useState<LocationValue>({
    regionId:     defaultToId     ?? null,
    regionName:   defaultToName,
    districtId:   defaultToDistrictId  ?? null,
    districtName: defaultToDistrictName,
  });
  const [date, setDate]   = useState(defaultDate);
  const [seats, setSeats] = useState(defaultSeats);

  // Sana berilmagan bo'lsa sukut bo'yicha bugun. Render paytida emas,
  // mount'dan keyin: `new Date()` serverda va brauzerda farq qilib
  // hydration xatosiga olib kelishi mumkin.
  useEffect(() => {
    if (!defaultDate) setDate(isoOf(new Date()));
  }, [defaultDate]);

  function swap() {
    setFrom(to);
    setTo(from);
  }

  function handleSearch() {
    if (!from.regionId || !to.regionId || !date) return;
    const p = new URLSearchParams({
      from_id:   String(from.regionId),
      to_id:     String(to.regionId),
      from_name: from.regionName,
      to_name:   to.regionName,
      date,
      seats:     String(seats),
    });
    if (from.districtId)   p.set("from_district_id",   String(from.districtId));
    if (from.districtName) p.set("from_district_name", from.districtName);
    if (to.districtId)     p.set("to_district_id",     String(to.districtId));
    if (to.districtName)   p.set("to_district_name",   to.districtName);
    router.push(`/trips?${p.toString()}`);
  }

  const canSearch = !!from.regionId && !!to.regionId && !!date;

  // ── Compact (trips sahifasidagi kichik forma) ──────────────────────────────
  if (compact) {
    return (
      <form
        onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
        className="flex flex-col sm:flex-row sm:items-center gap-2 bg-white rounded-2xl border border-gray-200 shadow-card p-2 sm:px-3 sm:py-1"
      >
        {/* Yo'nalish (mobilда 1-qator) */}
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <LocationPicker
            value={from}
            onChange={setFrom}
            placeholder="Qayerdan"
            compact
            className="flex-1 min-w-0"
          />
          <button
            type="button"
            onClick={swap}
            className="p-1 text-gray-300 hover:text-primary-500 transition-colors shrink-0"
          >
            <ArrowLeftRight size={14} />
          </button>
          <LocationPicker
            value={to}
            onChange={setTo}
            placeholder="Qayerga"
            compact
            className="flex-1 min-w-0"
          />
        </div>

        <div className="hidden sm:block w-px h-5 bg-gray-100 shrink-0" />

        {/* Sana + qidirish (mobilда 2-qator) */}
        <div className="flex items-center gap-2">
          <div className="relative flex items-center gap-1.5 flex-1 min-w-0">
            <Calendar size={14} className="text-gray-400 shrink-0" />
            <span className="text-sm font-medium text-gray-700 py-2.5 flex-1 min-w-0 sm:w-[120px]">
              {dateLabel(date)}
            </span>
            <input
              type="date"
              value={date}
              min={date ? isoOf(new Date()) : undefined}
              onChange={(e) => setDate(e.target.value)}
              aria-label="Sana"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
          <Button type="submit" size="sm" className="shrink-0" disabled={!canSearch}>
            <Search size={14} />
          </Button>
        </div>
      </form>
    );
  }

  // ── Full (bosh sahifadagi katta forma) ────────────────────────────────────
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
      className="bg-white rounded-2xl shadow-float border border-gray-200 overflow-visible"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_1px_1fr_1px_auto_auto] items-center">

        {/* Qayerdan */}
        <div className="px-5 py-1">
          <label className={LABEL}>Qayerdan</label>
          <LocationPicker
            value={from}
            onChange={setFrom}
            placeholder="Viloyat, shahar, tuman"
          />
        </div>

        {/* Swap */}
        <div className="hidden lg:flex items-center justify-center px-1">
          <button
            type="button"
            onClick={swap}
            className="w-8 h-8 bg-gray-50 hover:bg-primary-50 hover:text-primary-500 rounded-xl flex items-center justify-center text-gray-400 transition-colors"
          >
            <ArrowLeftRight size={15} />
          </button>
        </div>

        {/* Qayerga */}
        <div className="px-5 py-1 border-t sm:border-t-0 sm:border-l border-gray-100">
          <label className={LABEL}>Qayerga</label>
          <LocationPicker
            value={to}
            onChange={setTo}
            placeholder="Viloyat, shahar, tuman"
          />
        </div>

        <div className="hidden lg:block w-px h-12 bg-gray-100" />

        {/* Sana */}
        <div className="px-5 py-1 border-t lg:border-t-0 border-l-0 lg:border-l border-gray-100">
          <label className={LABEL}>Sana</label>
          {/* Sana "Bugun" deb ko'rinadi, bosilganda telefonning o'z kalendari
              ochilsin — input matn ustiga shaffof qo'yiladi. */}
          <div className="relative flex items-center gap-2 py-3">
            <Calendar size={16} className="text-primary-500 shrink-0" />
            <span className="flex-1 text-base font-medium text-gray-900">{dateLabel(date)}</span>
            <ChevronDown size={15} className="text-gray-400 shrink-0" />
            <input
              type="date"
              value={date}
              min={date ? isoOf(new Date()) : undefined}
              onChange={(e) => setDate(e.target.value)}
              aria-label="Sana"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
        </div>

        <div className="hidden lg:block w-px h-12 bg-gray-100" />

        {/* O'rin */}
        <div className="px-5 py-1 border-t lg:border-t-0 border-l-0 lg:border-l border-gray-100">
          <label className={LABEL}>Yo&apos;lovchi</label>
          <div className="flex items-center gap-3 py-3">
            <Users size={16} className="text-primary-500 shrink-0" />
            <button
              type="button"
              onClick={() => setSeats(Math.max(1, seats - 1))}
              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-medium transition-colors"
            >
              −
            </button>
            <span className="text-base font-semibold text-gray-900 min-w-[92px] text-center tabular-nums">
              {seats} yo&apos;lovchi
            </span>
            <button
              type="button"
              onClick={() => setSeats(Math.min(4, seats + 1))}
              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-medium transition-colors"
            >
              +
            </button>
          </div>
        </div>

        {/* Qidirish */}
        <div className="p-3 border-t lg:border-t-0 border-l-0 lg:border-l border-gray-100">
          <Button
            type="submit"
            size="lg"
            disabled={!canSearch}
            className="w-full lg:w-auto gap-2 h-14 px-8"
          >
            <Search size={18} />
            <span className="lg:hidden xl:inline">Qidirish</span>
          </Button>
        </div>
      </div>
    </form>
  );
}
