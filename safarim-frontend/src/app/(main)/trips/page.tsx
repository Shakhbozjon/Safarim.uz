"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpDown, MapPin } from "lucide-react";
import SearchBar from "@/components/trips/SearchBar";
import TripCard from "@/components/trips/TripCard";
import TripFilters from "@/components/trips/TripFilters";
import { TripCardSkeleton } from "@/components/ui/Skeleton";
import api from "@/lib/api";
import type { TripResponse } from "@/types";

type SortKey = "time_asc" | "price_asc" | "price_desc";

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

  const isReady = fromId && toId && date;

  const { data: trips = [], isLoading, isError } = useQuery<TripResponse[]>({
    queryKey: ["trips", fromId, toId, date, seats, sort],
    queryFn: async () => {
      const { data } = await api.get("/trips/search", {
        params: {
          from_region_id:  fromId,
          to_region_id:    toId,
          departure_date:  date,
          seats,
          sort,
        },
      });
      return data;
    },
    enabled: !!isReady,
  });

  function formatDate(d: string) {
    if (!d) return "";
    return new Date(d).toLocaleDateString("uz-UZ", {
      day: "numeric", month: "long", weekday: "short",
    });
  }

  if (!isReady) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="mb-8">
          <SearchBar />
        </div>
        <div className="text-5xl mb-4">🚗</div>
        <p className="text-lg font-semibold text-gray-900 mb-2">Qidirish uchun shahar va sana tanlang</p>
        <p className="text-sm text-gray-500">Qayerdan, qayerga va qachon — uchta maydonni to'ldiring</p>
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
          <TripFilters totalCount={trips.length} />

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
        {/* Sidebar filters */}
        <TripFilters totalCount={trips.length} />

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
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
              <div className="text-5xl mb-4">🚗</div>
              <p className="text-lg font-semibold text-gray-900 mb-2">Safarlar topilmadi</p>
              <p className="text-sm text-gray-500">Boshqa sana yoki yo'nalishni sinab ko'ring</p>
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
