"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Clock, ChevronRight, Car, Phone } from "lucide-react";
import api from "@/lib/api";
import type { AdminDriverListItem } from "@/types";
import Avatar from "@/components/ui/Avatar";

async function fetchPendingDrivers(): Promise<AdminDriverListItem[]> {
  const { data } = await api.get("/admin/drivers/pending");
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
  const { data: drivers, isLoading } = useQuery<AdminDriverListItem[]>({
    queryKey: ["admin", "drivers", "pending"],
    queryFn: fetchPendingDrivers,
    refetchInterval: 60_000,
  });

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Kutayotgan haydovchilar</h1>
        <p className="text-sm text-gray-500 mt-1">
          Arizalar ko'rib chiqilishi kerak
        </p>
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
          <p className="text-gray-500 font-medium">Kutayotgan ariza yo'q</p>
          <p className="text-sm text-gray-400 mt-1">Barcha arizalar ko'rib chiqilgan</p>
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
                    <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-medium rounded-full flex items-center gap-1">
                      <Clock size={10} />
                      Kutmoqda
                    </span>
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
