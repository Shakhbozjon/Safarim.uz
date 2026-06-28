"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftRight, Calendar, Users, Search } from "lucide-react";
import Button from "@/components/ui/Button";
import LocationPicker, { LocationValue, EMPTY_LOCATION } from "@/components/ui/LocationPicker";

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
        className="flex items-center gap-2 bg-white rounded-2xl border border-gray-200 shadow-card px-3 py-1"
      >
        <LocationPicker
          value={from}
          onChange={setFrom}
          placeholder="Qayerdan"
          compact
          className="flex-1"
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
          className="flex-1"
        />
        <div className="w-px h-5 bg-gray-100" />
        <div className="flex items-center gap-1.5">
          <Calendar size={14} className="text-gray-400" />
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="text-sm text-gray-700 bg-transparent outline-none w-[120px] py-2.5"
          />
        </div>
        <Button type="submit" size="sm" className="shrink-0" disabled={!canSearch}>
          <Search size={14} />
        </Button>
      </form>
    );
  }

  // ── Full (bosh sahifadagi katta forma) ────────────────────────────────────
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
      className="bg-white rounded-2xl shadow-card-lg border border-gray-100 overflow-visible"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_1px_1fr_1px_auto_auto] items-center">

        {/* Qayerdan */}
        <div className="px-5 py-1">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wide">
            Qayerdan
          </label>
          <LocationPicker
            value={from}
            onChange={setFrom}
            placeholder="Viloyat / shahar"
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
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wide">
            Qayerga
          </label>
          <LocationPicker
            value={to}
            onChange={setTo}
            placeholder="Viloyat / shahar"
          />
        </div>

        <div className="hidden lg:block w-px h-12 bg-gray-100" />

        {/* Sana */}
        <div className="px-5 py-1 border-t lg:border-t-0 border-l-0 lg:border-l border-gray-100">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wide">Sana</label>
          <div className="flex items-center gap-2">
            <Calendar size={15} className="text-gray-400 shrink-0" />
            <input
              type="date"
              value={date}
              min={new Date().toISOString().split("T")[0]}
              onChange={(e) => setDate(e.target.value)}
              className="flex-1 bg-transparent outline-none text-base text-gray-900 py-3"
            />
          </div>
        </div>

        <div className="hidden lg:block w-px h-12 bg-gray-100" />

        {/* O'rin */}
        <div className="px-5 py-1 border-t lg:border-t-0 border-l-0 lg:border-l border-gray-100">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wide">O'rin</label>
          <div className="flex items-center gap-3 py-3">
            <Users size={15} className="text-gray-400 shrink-0" />
            <button
              type="button"
              onClick={() => setSeats(Math.max(1, seats - 1))}
              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-medium transition-colors"
            >
              −
            </button>
            <span className="text-base font-semibold text-gray-900 w-4 text-center tabular-nums">
              {seats}
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
