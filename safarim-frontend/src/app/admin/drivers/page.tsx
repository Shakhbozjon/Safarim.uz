"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { clsx } from "clsx";
import { Check, ChevronRight, Car, Clock, Loader2, Phone, Search, X } from "lucide-react";
import api from "@/lib/api";
import type { AdminDriverListItem } from "@/types";
import Avatar from "@/components/ui/Avatar";

type StatusKey = "pending" | "approved" | "rejected" | "all";

const TABS: { key: StatusKey; label: string }[] = [
  { key: "pending", label: "Kutayotgan" },
  { key: "approved", label: "Tasdiqlangan" },
  { key: "rejected", label: "Rad etilgan" },
  { key: "all", label: "Hammasi" },
];

const STATUS_BADGE: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
  pending:  { label: "Kutmoqda",    cls: "bg-orange-100 text-orange-700", icon: Clock },
  approved: { label: "Tasdiqlangan", cls: "bg-green-100 text-green-700",  icon: Check },
  rejected: { label: "Rad etilgan",  cls: "bg-red-100 text-red-700",      icon: X },
};

async function fetchDrivers(status: StatusKey, q: string): Promise<AdminDriverListItem[]> {
  const { data } = await api.get("/admin/drivers", {
    params: { status, q: q || undefined },
  });
  return data;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("uz-UZ", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export default function AdminDriversPage() {
  const [tab, setTab] = useState<StatusKey>("pending");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 350);
    return () => clearTimeout(t);
  }, [search]);

  // Qidiruv paytida bo'lim e'tiborga olinmaydi: "Kutayotgan" bo'limida turib
  // tasdiqlangan haydovchini yozgan odam "topilmadi" degan javob olardi va
  // buning sababi ko'rinmasdi. Yozilgan zahoti butun baza bo'ylab qidiriladi.
  const effectiveTab: StatusKey = debounced ? "all" : tab;

  const { data: drivers, isLoading, isFetching } = useQuery<AdminDriverListItem[]>({
    queryKey: ["admin", "drivers", effectiveTab, debounced],
    queryFn: () => fetchDrivers(effectiveTab, debounced),
    refetchInterval: 60_000,
    placeholderData: (prev) => prev,
  });

  return (
    <div className="p-5 sm:p-8">
      <div className="mb-5">
        <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">Haydovchilar</h1>
        <p className="mt-1 text-sm text-gray-500">
          {!drivers
            ? "Yuklanmoqda..."
            : debounced
              ? `«${debounced}» bo'yicha ${drivers.length} ta topildi (barcha holatlar)`
              : `${drivers.length} ta ko'rsatilmoqda`}
        </p>
      </div>

      {/* Holat bo'yicha bo'limlar + qidiruv */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <div className="flex rounded-xl border border-gray-200 bg-white p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => { setTab(t.key); setSearch(""); }}
              className={clsx(
                "rounded-lg px-3 py-1.5 text-[13px] font-semibold transition-colors",
                effectiveTab === t.key ? "bg-primary-500 text-white" : "text-gray-500 hover:text-gray-800",
                debounced && t.key !== "all" && "opacity-50"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative w-full max-w-xs">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ism, telefon yoki avto raqami..."
            className="w-full rounded-xl border border-gray-200 py-2.5 pl-10 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          {isFetching && (
            <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-gray-300" />
          )}
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 p-5 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gray-100 rounded-full" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-100 rounded w-40" />
                  <div className="h-3 bg-gray-100 rounded w-28" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && drivers?.length === 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <Car size={40} className="mx-auto text-gray-200 mb-3" />
          <p className="font-medium text-gray-500">
            {debounced ? "Hech narsa topilmadi" : "Bu bo'limda haydovchi yo'q"}
          </p>
          <p className="mt-1 text-sm text-gray-400">
            {debounced ? "Boshqa so'z bilan qidirib ko'ring" : "Barcha arizalar ko'rib chiqilgan"}
          </p>
        </div>
      )}

      {!isLoading && drivers && drivers.length > 0 && (
        <div className="space-y-3">
          {drivers.map((driver) => (
            <Link
              key={driver.id}
              href={`/admin/drivers/${driver.id}`}
              className="block bg-white rounded-2xl border border-gray-100 p-5 hover:border-primary-200 hover:shadow-sm transition-all group"
            >
              <div className="flex items-center gap-4">
                <Avatar
                  src={driver.user.profile_photo}
                  name={driver.user.full_name}
                  size="md"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900">{driver.user.full_name}</p>
                    {(() => {
                      const b = STATUS_BADGE[driver.status] ?? STATUS_BADGE.pending;
                      const Icon = b.icon;
                      return (
                        <span className={clsx("flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", b.cls)}>
                          <Icon size={10} />
                          {b.label}
                        </span>
                      );
                    })()}
                  </div>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="flex items-center gap-1.5 text-sm text-gray-500">
                      <Phone size={13} />
                      {driver.user.phone}
                    </span>
                    <span className="flex items-center gap-1.5 text-sm text-gray-500">
                      <Car size={13} />
                      {driver.vehicle_make} {driver.vehicle_model} · {driver.vehicle_plate}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1.5">
                    Ariza: {formatDate(driver.created_at)}
                  </p>
                </div>
                <ChevronRight
                  size={18}
                  className="text-gray-300 group-hover:text-primary-400 transition-colors shrink-0"
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
