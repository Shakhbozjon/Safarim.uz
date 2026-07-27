"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftRight } from "lucide-react";
import LocationPicker, { LocationValue, EMPTY_LOCATION } from "@/components/ui/LocationPicker";

const LABEL = "block text-[11.5px] font-bold uppercase tracking-wide text-gray-500 mb-1.5";
const FIELD =
  "w-full px-3.5 py-3 border border-gray-200 rounded-[10px] text-sm bg-gray-50/70 focus:bg-white outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition";

/** Bosh sahifa hero'sidagi ixcham qidiruv kartasi (mockup uslubi). */
export default function HeroSearchCard() {
  const router = useRouter();
  const [from, setFrom] = useState<LocationValue>(EMPTY_LOCATION);
  const [to, setTo] = useState<LocationValue>(EMPTY_LOCATION);
  const [date, setDate] = useState("");
  const [seats, setSeats] = useState(1);

  const canSearch = !!from.regionId && !!to.regionId && !!date;

  function handleSearch() {
    if (!canSearch) return;
    const p = new URLSearchParams({
      from_id: String(from.regionId),
      to_id: String(to.regionId),
      from_name: from.regionName,
      to_name: to.regionName,
      date,
      seats: String(seats),
    });
    if (from.districtId) p.set("from_district_id", String(from.districtId));
    if (from.districtName) p.set("from_district_name", from.districtName);
    if (to.districtId) p.set("to_district_id", String(to.districtId));
    if (to.districtName) p.set("to_district_name", to.districtName);
    router.push(`/trips?${p.toString()}`);
  }

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
      className="bg-white border border-gray-100 rounded-[18px] p-4 sm:p-5 shadow-float"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <div className="relative">
          <label className={LABEL}>Qayerdan</label>
          <LocationPicker value={from} onChange={setFrom} placeholder="Toshkent" />
        </div>
        <div className="relative">
          <div className="flex items-center justify-between mb-1.5">
            <label className={LABEL + " mb-0"}>Qayerga</label>
            <button
              type="button"
              onClick={() => { setFrom(to); setTo(from); }}
              className="text-gray-300 hover:text-primary-500 transition-colors"
              aria-label="Almashtirish"
            >
              <ArrowLeftRight size={14} />
            </button>
          </div>
          <LocationPicker value={to} onChange={setTo} placeholder="Samarqand" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3.5">
        <div>
          <label className={LABEL}>Sana</label>
          <input
            type="date"
            value={date}
            min={new Date().toISOString().split("T")[0]}
            onChange={(e) => setDate(e.target.value)}
            className={FIELD}
          />
        </div>
        <div>
          <label className={LABEL}>O'rin</label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSeats(Math.max(1, seats - 1))}
              className="w-9 h-[42px] rounded-[10px] bg-gray-100 hover:bg-gray-200 text-gray-600 font-semibold shrink-0"
            >−</button>
            <span className="flex-1 text-center text-base font-bold text-gray-900 tabular-nums">{seats}</span>
            <button
              type="button"
              onClick={() => setSeats(Math.min(4, seats + 1))}
              className="w-9 h-[42px] rounded-[10px] bg-gray-100 hover:bg-gray-200 text-gray-600 font-semibold shrink-0"
            >+</button>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={!canSearch}
        className="w-full py-[15px] bg-primary-500 hover:bg-primary-600 disabled:opacity-50 text-white rounded-[11px] text-[15.5px] font-bold shadow-primary-glow transition"
      >
        Safar qidirish
      </button>
    </form>
  );
}
