"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftRight, Calendar, ChevronDown } from "lucide-react";
import LocationPicker, { LocationValue, EMPTY_LOCATION } from "@/components/ui/LocationPicker";

const LABEL = "block text-[14px] font-bold text-gray-800 mb-1";

const UZ_MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];

const isoOf = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** "2026-09-03" → "Bugun" | "Ertaga" | "3-sentabr".
 *  Sana raqam emas, odam tilida — ko'p hollarda foydalanuvchi unga tegmaydi ham. */
function dateLabel(iso: string): string {
  if (!iso) return "Bugun";
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (iso === isoOf(today)) return "Bugun";
  if (iso === isoOf(tomorrow)) return "Ertaga";
  const [, m, d] = iso.split("-").map(Number);
  return `${d}-${UZ_MONTHS[m - 1] ?? ""}`;
}

/** Bosh sahifa hero'sidagi ixcham qidiruv kartasi (mockup uslubi). */
export default function HeroSearchCard() {
  const router = useRouter();
  const [from, setFrom] = useState<LocationValue>(EMPTY_LOCATION);
  const [to, setTo] = useState<LocationValue>(EMPTY_LOCATION);
  const [date, setDate] = useState("");
  const [seats, setSeats] = useState(1);
  const [error, setError] = useState("");

  // Sukut bo'yicha bugun. Render paytida emas, mount'dan keyin qo'yiladi:
  // `new Date()` serverda va brauzerda har xil natija berib hydration
  // xatosiga olib kelishi mumkin.
  useEffect(() => setDate(isoOf(new Date())), []);

  // Tugma o'chirilmaydi: o'chiq tugma nima yetishmayotganini aytmaydi va
  // ko'k ramka ichida o'lik ko'rinadi. Bosilganda sabab yoziladi.
  function handleSearch() {
    if (!from.regionId || !to.regionId) {
      setError("Qayerdan va qayerga tanlang");
      return;
    }
    if (!date) {
      setError("Sanani tanlang");
      return;
    }
    setError("");
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
      className="bg-white border-2 border-primary-500 rounded-[18px] p-4 sm:p-5 shadow-[0_0_0_4px_rgba(79,70,229,0.08)]"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <div className="relative">
          <label className={LABEL}>Qayerdan</label>
          <LocationPicker value={from} onChange={(v) => { setFrom(v); setError(""); }} placeholder="Viloyat, shahar, tuman" />
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
          <LocationPicker value={to} onChange={(v) => { setTo(v); setError(""); }} placeholder="Viloyat, shahar, tuman" />
        </div>
      </div>

      <div className="space-y-3 mb-3.5">
        <div className="min-w-0">
          <label className={LABEL}>Sana</label>
          {/* Sana "Bugun" deb ko'rinadi, lekin bosilganda telefonning o'z
              kalendari ochilsin — shuning uchun input ustiga shaffof qo'yiladi.
              `showPicker()` hamma brauzerda yo'q, bu usul hamma joyda ishlaydi. */}
          <div className="relative">
            <div className="flex items-center gap-2 py-1">
              <Calendar size={17} className="text-primary-500 shrink-0" />
              <span className="text-[15px] font-semibold text-gray-900">{dateLabel(date)}</span>
              <ChevronDown size={15} className="text-gray-400 ml-auto shrink-0" />
            </div>
            <input
              type="date"
              value={date}
              min={date ? isoOf(new Date()) : undefined}
              onChange={(e) => setDate(e.target.value)}
              aria-label="Jo'nash sanasi"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
        </div>

        <div className="min-w-0">
          <label className={LABEL}>Yo&apos;lovchi</label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSeats(Math.max(1, seats - 1))}
              className="w-9 h-9 rounded-[10px] bg-gray-100 hover:bg-gray-200 text-gray-600 font-semibold shrink-0"
            >−</button>
            <span className="text-[15px] font-semibold text-gray-900 tabular-nums min-w-[92px] text-center">
              {seats} yo&apos;lovchi
            </span>
            <button
              type="button"
              onClick={() => setSeats(Math.min(4, seats + 1))}
              className="w-9 h-9 rounded-[10px] bg-gray-100 hover:bg-gray-200 text-gray-600 font-semibold shrink-0"
            >+</button>
          </div>
        </div>
      </div>

      {error && (
        <p className="text-[13px] font-semibold text-red-500 mb-2 text-center">{error}</p>
      )}

      <button
        type="submit"
        className="w-full py-[15px] bg-primary-500 hover:bg-primary-600 text-white rounded-[11px] text-[15.5px] font-bold shadow-primary-glow transition cursor-pointer"
      >
        Safar qidirish
      </button>
    </form>
  );
}
