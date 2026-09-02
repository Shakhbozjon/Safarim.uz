"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpDown, MapPin, Plus } from "lucide-react";
import Link from "next/link";
import SearchBar from "@/components/trips/SearchBar";
import TripCard from "@/components/trips/TripCard";
import TripFilters, { DEFAULT_FILTERS, MAX_PRICE, type Filters } from "@/components/trips/TripFilters";
import { TripCardSkeleton } from "@/components/ui/Skeleton";
import api from "@/lib/api";
import type { TripResponse } from "@/types";

type SortKey = "time_asc" | "price_asc" | "price_desc";

// `toLocaleDateString("uz-UZ")` Node'da va brauzerda har xil natija beradi
// (ICU ma'lumotlari boshqacha) — bu hydration xatosiga olib kelardi.
// Shuning uchun nomlar qo'lda, natija ikkala tomonda bir xil.
const UZ_MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];
const UZ_WEEKDAYS = ["Yak", "Dush", "Sesh", "Chor", "Pay", "Jum", "Shan"];

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "time_asc",    label: "Jo'nash vaqti" },
  { value: "price_asc",  label: "Arzon narx" },
  { value: "price_desc", label: "Qimmat narx" },
];

function TripsContent() {
  const params = useSearchParams();

  const fromId             = Number(params.get("from_id"));
  const toId               = Number(params.get("to_id"));
  const fromName           = params.get("from_name") || "";
  const toName             = params.get("to_name") || "";
  const fromDistrictId     = Number(params.get("from_district_id")) || undefined;
  const toDistrictId       = Number(params.get("to_district_id"))   || undefined;
  const fromDistrictName   = params.get("from_district_name") || "";
  const toDistrictName     = params.get("to_district_name")   || "";
  const date               = params.get("date") || "";
  const seats              = Number(params.get("seats")) || 1;

  const [sort, setSort] = useState<SortKey>("time_asc");
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

  const isReady = fromId && toId && date;

  const { data: trips = [], isLoading, isError } = useQuery<TripResponse[]>({
    // Backend faqat women_only va max_price ni qo'llab-quvvatlaydi — o'shalar
    // so'rovga qo'shiladi va queryKey ga kiradi. Vaqt, reyting va yuk esa
    // kelgan ro'yxat ustida pastda filtrlanadi (backendda bunday parametr yo'q).
    queryKey: ["trips", fromId, toId, date, seats, sort, filters.womenOnly, filters.maxPrice],
    queryFn: async () => {
      const { data } = await api.get("/trips/search", {
        params: {
          from_region_id:  fromId,
          to_region_id:    toId,
          departure_date:  date,
          seats,
          sort,
          ...(filters.womenOnly ? { women_only: true } : {}),
          ...(filters.maxPrice < MAX_PRICE ? { max_price: filters.maxPrice } : {}),
        },
      });
      return data;
    },
    enabled: !!isReady,
  });

  // Natija bo'sh bo'lsa: shu yo'nalishda yaqin kunlarda safar bormi?
  // "Boshqa sanani sinab ko'ring" degan maslahat o'rniga tayyor sanalar.
  const { data: nearest = [] } = useQuery<{ date: string; count: number }[]>({
    queryKey: ["nearest-dates", fromId, toId, date, seats],
    queryFn: async () => {
      const { data } = await api.get("/trips/nearest-dates", {
        params: { from_region_id: fromId, to_region_id: toId, after: date, seats },
      });
      return data;
    },
    enabled: !!isReady && !isLoading && trips.length === 0,
  });

  const visibleTrips = trips.filter((t) => {
    const time = t.departure_time.slice(0, 5);            // "HH:MM:SS" → "HH:MM"
    if (time < filters.departureFrom || time > filters.departureTo) return false;
    if (filters.minRating > 0 && (t.driver.rating_avg ?? 0) < filters.minRating) return false;
    if (filters.amenities.luggage && t.luggage_size !== "large") return false;
    return true;
  });

  // Ro'yxat bo'sh: filtr sababmi yoki bu yo'nalishda umuman safar yo'qmi
  const hiddenByFilters = trips.length > 0 && visibleTrips.length === 0;

  /** "2026-08-18" → "Sesh, 18-avgust" */
  function formatDate(d: string) {
    if (!d) return "";
    const [y, m, day] = d.split("-").map(Number);
    if (!y || !m || !day) return d;
    // Sanani qismlardan quramiz: "2026-08-18" satrini Date'ga berish uni UTC deb
    // o'qiydi va mahalliy vaqt mintaqasida kun siljib ketishi mumkin.
    const wd = UZ_WEEKDAYS[new Date(y, m - 1, day).getDay()];
    return `${wd}, ${day}-${UZ_MONTHS[m - 1] ?? ""}`;
  }

  if (!isReady) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        {/* `text-center` faqat pastdagi xabar uchun: konteynerda tursa
            formaning yorliqlari ham markazga tortilib qolardi */}
        <div className="mb-8">
          <SearchBar />
        </div>
        <div className="text-center">
          <div className="text-5xl mb-4">🚗</div>
          <p className="text-lg font-semibold text-gray-900 mb-2">Qidirish uchun shahar va sana tanlang</p>
          <p className="text-sm text-gray-500">Qayerdan, qayerga va qachon — uchta maydonni to'ldiring</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Search bar */}
      <div className="mb-6">
        <SearchBar
          compact
          defaultFromId={fromId}
          defaultToId={toId}
          defaultFromName={fromName}
          defaultToName={toName}
          defaultFromDistrictId={fromDistrictId}
          defaultToDistrictId={toDistrictId}
          defaultFromDistrictName={fromDistrictName}
          defaultToDistrictName={toDistrictName}
          defaultDate={date}
          defaultSeats={seats}
        />
      </div>

      {/* Heading */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <MapPin size={18} className="text-primary-500" />
            {fromName} → {toName}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {formatDate(date)} · {seats} yo'lovchi
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <TripFilters variant="button" totalCount={visibleTrips.length} onChange={setFilters} />

          <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-xl px-1 py-1">
            <ArrowUpDown size={13} className="text-gray-400 ml-1.5" />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="text-sm text-gray-700 bg-transparent outline-none py-1.5 pr-2 cursor-pointer"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sidebar filters (faqat desktop) */}
        <TripFilters variant="sidebar" totalCount={visibleTrips.length} onChange={setFilters} />

        {/* List */}
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => <TripCardSkeleton key={i} />)}
            </div>
          ) : isError ? (
            <div className="bg-red-50 rounded-2xl p-10 text-center">
              <p className="text-red-600 font-semibold">Xatolik yuz berdi</p>
              <p className="text-sm text-red-400 mt-1">Internet aloqasini tekshiring</p>
            </div>
          ) : visibleTrips.length > 0 ? (
            <div className="space-y-3">
              {visibleTrips.map((trip) => (
                <TripCard key={trip.id} trip={trip} />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center">
                <div className="text-4xl mb-3">🚗</div>
                <p className="text-lg font-semibold text-gray-900 mb-1.5">
                  {formatDate(date)} kuni safar yo&apos;q
                </p>
                <p className="text-sm text-gray-500">
                  {hiddenByFilters
                    ? "Filtrlarga mos safar yo'q — ularni yumshatib ko'ring"
                    : nearest.length > 0
                      ? "Quyidagi kunlarda bor — yoki boshqa yo'nalishni sinang"
                      : "Boshqa sana yoki yo'nalishni sinab ko'ring"}
                </p>
              </div>

              {!hiddenByFilters && nearest.length > 0 && (
                <div className="bg-white rounded-2xl border border-gray-100 p-5">
                  <p className="text-sm font-semibold text-gray-900 mb-1">
                    Shu yo&apos;nalishda yaqin kunlarda bor
                  </p>
                  <p className="text-xs text-gray-500 mb-3">Sanani bosing — natijalar yangilanadi</p>
                  <div className="flex flex-wrap gap-2">
                    {nearest.map((n) => (
                      <Link
                        key={n.date}
                        href={`?${new URLSearchParams({ ...Object.fromEntries(params), date: n.date })}`}
                        className="rounded-xl border border-gray-200 hover:border-primary-300 px-3.5 py-2.5 transition-colors"
                      >
                        <span className="block text-[13px] font-bold text-gray-800">{formatDate(n.date)}</span>
                        <span className="block text-[11px] font-semibold text-primary-600">
                          {n.count} ta safar
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Bu ekranga tushganlarning bir qismi mashinali — ularga ham yo'l */}
              <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-5">
                <p className="text-sm font-semibold text-gray-900 mb-1">
                  O&apos;zingiz shu yo&apos;lga ketyapsizmi?
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  E&apos;lon qo&apos;ying — bir necha daqiqa. Komissiya olinmaydi.
                </p>
                <Link
                  href="/create-trip"
                  className="inline-flex items-center gap-1.5 rounded-xl border-[1.5px] border-primary-500 text-primary-600 hover:bg-primary-50 font-bold text-sm px-4 py-2.5 transition-colors"
                >
                  <Plus size={15} />
                  Safar e&apos;lon qilish
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TripsPage() {
  return (
    <Suspense fallback={
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        {[1, 2, 3].map((i) => <TripCardSkeleton key={i} />)}
      </div>
    }>
      <TripsContent />
    </Suspense>
  );
}
