"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import Link from "next/link";
import SearchBar from "@/components/trips/SearchBar";
import TripCard from "@/components/trips/TripCard";
import TripFilters, { DEFAULT_FILTERS, MAX_PRICE, type Filters } from "@/components/trips/TripFilters";
import { TripCardSkeleton } from "@/components/ui/Skeleton";
import api from "@/lib/api";
import { dateLabel } from "@/lib/date";
import type { TripResponse } from "@/types";

// `toLocaleDateString("uz-UZ")` Node'da va brauzerda har xil natija beradi
// (ICU ma'lumotlari boshqacha) — bu hydration xatosiga olib kelardi.
// Shuning uchun nomlar qo'lda, natija ikkala tomonda bir xil.
const UZ_MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];
const UZ_WEEKDAYS = ["Yak", "Dush", "Sesh", "Chor", "Pay", "Jum", "Shan"];

// Qidiruv natijasi shu bo'laklarda keladi (backenddagi `SEARCH_PAGE_SIZE` bilan bir xil)
const PAGE_SIZE = 20;

/** Filtrlar → so'rov parametrlari. Hammasi serverda qo'llanadi: natija
 *  sahifalab kelgani uchun brauzerda filtrlash faqat birinchi sahifani ko'rardi. */
function filterParams(f: Filters) {
  return {
    ...(f.womenOnly ? { women_only: true } : {}),
    ...(f.maxPrice < MAX_PRICE ? { max_price: f.maxPrice } : {}),
    ...(f.departureFrom !== DEFAULT_FILTERS.departureFrom ? { departure_from: f.departureFrom } : {}),
    ...(f.departureTo !== DEFAULT_FILTERS.departureTo ? { departure_to: f.departureTo } : {}),
    ...(f.minRating > 0 ? { min_rating: f.minRating } : {}),
    ...(f.amenities.luggage ? { large_luggage: true } : {}),
  };
}

interface SearchPage {
  trips: TripResponse[];
  total: number;
}

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

  // Qidiruvni o'zgartirish uchun ixcham panel bosiladi va to'liq forma ochiladi.
  // Saralash olib tashlandi: natijalar jo'nash vaqti bo'yicha keladi.
  const [expanded, setExpanded] = useState(false);

  // Yangi qidiruvdan keyin forma yopiladi. Sahifa o'sha marshrutda qolgani
  // uchun holat o'z-o'zidan tozalanmaydi va forma ochiq turib qolardi.
  useEffect(() => setExpanded(false), [fromId, toId, date, seats]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

  const isReady = fromId && toId && date;

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: [
      "trips", fromId, toId, fromDistrictId, toDistrictId,
      date, seats, filters,
    ],
    queryFn: async ({ pageParam }): Promise<SearchPage> => {
      const res = await api.get<TripResponse[]>("/trips/search", {
        params: {
          from_region_id:  fromId,
          to_region_id:    toId,
          departure_date:  date,
          seats,
          // Tuman berilmasa backend viloyat bo'ylab qidiradi
          ...(fromDistrictId ? { from_district_id: fromDistrictId } : {}),
          ...(toDistrictId   ? { to_district_id:   toDistrictId }   : {}),
          ...filterParams(filters),
          limit: PAGE_SIZE,
          offset: pageParam,
        },
      });
      return { trips: res.data, total: Number(res.headers["x-total-count"] ?? res.data.length) };
    },
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, p) => n + p.trips.length, 0);
      return last.trips.length === PAGE_SIZE && loaded < last.total ? loaded : undefined;
    },
    enabled: !!isReady,
  });

  const trips = data?.pages.flatMap((p) => p.trips) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  // Vaqt, reyting yoki yuk filtri yoqilgan — bo'sh natija shulardan bo'lishi mumkin
  const extraFiltersOn =
    filters.departureFrom !== DEFAULT_FILTERS.departureFrom ||
    filters.departureTo !== DEFAULT_FILTERS.departureTo ||
    filters.minRating > 0 ||
    filters.amenities.luggage;
  const noResults = !isLoading && !isError && total === 0;

  // Tuman tanlangan bo'lsa, bo'sh natijada odamni boshi berk ko'chada
  // qoldirmaymiz: viloyat bo'ylab nechta safar borligini oldindan bilib,
  // "kengaytirish" tugmasini raqami bilan ko'rsatamiz.
  const districtNarrowed = Boolean(fromDistrictId || toDistrictId);

  // Natija bo'sh bo'lsa: shu yo'nalishda yaqin kunlarda safar bormi?
  // "Boshqa sanani sinab ko'ring" degan maslahat o'rniga tayyor sanalar.
  const { data: nearest = [] } = useQuery<{ date: string; count: number }[]>({
    queryKey: ["nearest-dates", fromId, toId, fromDistrictId, toDistrictId, date, seats],
    queryFn: async () => {
      const { data } = await api.get("/trips/nearest-dates", {
        params: {
          from_region_id: fromId,
          to_region_id: toId,
          after: date,
          seats,
          ...(fromDistrictId ? { from_district_id: fromDistrictId } : {}),
          ...(toDistrictId   ? { to_district_id:   toDistrictId }   : {}),
        },
      });
      return data;
    },
    enabled: !!isReady && noResults && !extraFiltersOn,
  });

  // Xuddi shu so'rov, faqat tumansiz — "butun viloyat bo'yicha" tugmasi uchun.
  // Faqat soni kerak, shuning uchun bitta safar so'raladi va son sarlavhadan olinadi.
  const { data: regionWideCount = 0 } = useQuery<number>({
    queryKey: [
      "trips-region-wide", fromId, toId, date, seats, filters,
    ],
    queryFn: async () => {
      const res = await api.get<TripResponse[]>("/trips/search", {
        params: {
          from_region_id:  fromId,
          to_region_id:    toId,
          departure_date:  date,
          seats,
          ...filterParams(filters),
          limit: 1,
        },
      });
      return Number(res.headers["x-total-count"] ?? res.data.length);
    },
    enabled: !!isReady && noResults && districtNarrowed && !extraFiltersOn,
  });

  // Ro'yxat bo'sh: filtr sababmi yoki bu yo'nalishda umuman safar yo'qmi
  const hiddenByFilters = noResults && extraFiltersOn;

  /** Shu qidiruv, faqat tuman filtrisiz */
  function hrefWithoutDistricts() {
    const next = new URLSearchParams(Object.fromEntries(params));
    for (const k of ["from_district_id", "to_district_id", "from_district_name", "to_district_name"]) {
      next.delete(k);
    }
    return `?${next.toString()}`;
  }

  const narrowedNames = [fromDistrictName, toDistrictName].filter(Boolean).join(" va ");

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
      {/* Qidiruv: yig'ilgan holatda bitta qator. Yo'nalish avval ikki joyda
          — panelda va uning ostidagi sarlavhada — takrorlanardi. */}
      {expanded ? (
        <div className="mb-6">
          <SearchBar
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
      ) : (
        <div className="mb-6 flex items-center gap-2 bg-white border-2 border-primary-500 rounded-full pl-4 pr-2 py-2">
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="flex items-center gap-3 flex-1 min-w-0 text-left"
          >
            <Search size={18} className="text-gray-500 shrink-0" />
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-gray-900 truncate">
                {fromName} → {toName}
              </span>
              <span className="block text-[13px] text-gray-500">
                {dateLabel(date)}, {seats} yo&apos;lovchi
              </span>
            </span>
          </button>
          <div className="shrink-0">
            <TripFilters variant="button" totalCount={total} onChange={setFilters} />
          </div>
        </div>
      )}

      <div className="flex gap-6">
        {/* Sidebar filters (faqat desktop) */}
        <TripFilters variant="sidebar" totalCount={total} onChange={setFilters} />

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
          ) : trips.length > 0 ? (
            <div className="space-y-3">
              {trips.map((trip) => (
                <TripCard key={trip.id} trip={trip} />
              ))}
              {hasNextPage && (
                <button
                  type="button"
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                  className="w-full py-3 rounded-2xl border border-gray-200 bg-white text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-60"
                >
                  {isFetchingNextPage
                    ? "Yuklanmoqda…"
                    : `Yana ko'rsatish (${total - trips.length} ta qoldi)`}
                </button>
              )}
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
                    : regionWideCount > 0
                      ? `${narrowedNames || "Tanlangan tuman"} bo'yicha safar yo'q`
                      : nearest.length > 0
                        ? "Quyidagi kunlarda bor — yoki boshqa yo'nalishni sinang"
                        : "Boshqa sana yoki yo'nalishni sinab ko'ring"}
                </p>
              </div>

              {/* Tuman bo'yicha bo'sh, lekin viloyat bo'ylab safar bor —
                  eng foydali qadam shu, shuning uchun eng tepada turadi */}
              {!hiddenByFilters && regionWideCount > 0 && (
                <div className="bg-white rounded-2xl border border-gray-100 p-5">
                  <p className="text-sm font-semibold text-gray-900 mb-1">
                    Butun viloyat bo&apos;ylab {regionWideCount} ta safar bor
                  </p>
                  <p className="text-xs text-gray-500 mb-3">
                    Tuman filtrini olib tashlasangiz shular chiqadi
                  </p>
                  <Link
                    href={hrefWithoutDistricts()}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-primary-500 hover:bg-primary-600 text-white font-bold text-sm px-4 py-2.5 transition-colors"
                  >
                    <Search size={15} />
                    Butun viloyat bo&apos;yicha qidirish
                  </Link>
                </div>
              )}

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
