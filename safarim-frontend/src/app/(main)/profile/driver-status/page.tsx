"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Clock, CheckCircle, XCircle, ChevronLeft, Car, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import Button from "@/components/ui/Button";
import api from "@/lib/api";

interface DriverStatus {
  status: "pending" | "approved" | "rejected";
  rejection_reason: string | null;
  message: string;
}

interface DriverProfile {
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: number;
  vehicle_color: string;
  vehicle_plate: string;
  vehicle_seats: number;
  status: string;
  created_at: string;
}

const STATUS_CONFIG = {
  pending: {
    icon: Clock,
    iconBg: "bg-yellow-100",
    iconColor: "text-yellow-500",
    title: "Ko'rib chiqilmoqda",
    color: "text-yellow-700",
    bg: "bg-yellow-50",
    border: "border-yellow-100",
  },
  approved: {
    icon: CheckCircle,
    iconBg: "bg-green-100",
    iconColor: "text-green-500",
    title: "Tasdiqlandi!",
    color: "text-green-700",
    bg: "bg-green-50",
    border: "border-green-100",
  },
  rejected: {
    icon: XCircle,
    iconBg: "bg-red-100",
    iconColor: "text-red-500",
    title: "Rad etildi",
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-100",
  },
};

export default function DriverStatusPage() {
  const router = useRouter();

  const { data: status, isLoading: statusLoading, refetch } = useQuery<DriverStatus>({
    queryKey: ["driver-status"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me/status");
      return data;
    },
    refetchInterval: (query) =>
      (query.state.data as DriverStatus | undefined)?.status === "pending" ? 30_000 : false,
  });

  const { data: profile, isLoading: profileLoading } = useQuery<DriverProfile>({
    queryKey: ["driver-profile"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me");
      return data;
    },
  });

  const isLoading = statusLoading || profileLoading;

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto" />
      </div>
    );
  }

  if (!status || !profile) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <p className="text-gray-500 mb-4">Ariza topilmadi</p>
        <Button onClick={() => router.push("/profile/driver-apply")}>
          Ariza topshirish
        </Button>
      </div>
    );
  }

  const cfg = STATUS_CONFIG[status.status];
  const StatusIcon = cfg.icon;

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push("/profile")}
          className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Ariza holati</h1>
          <p className="text-sm text-gray-500">Haydovchi verifikatsiyasi</p>
        </div>
      </div>

      {/* Status card */}
      <div className={clsx(
        "rounded-2xl border p-6 mb-5 text-center",
        cfg.bg, cfg.border
      )}>
        <div className={clsx(
          "w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4",
          cfg.iconBg
        )}>
          <StatusIcon size={32} className={cfg.iconColor} />
        </div>

        <h2 className={clsx("text-xl font-bold mb-2", cfg.color)}>
          {cfg.title}
        </h2>

        <p className="text-sm text-gray-600 leading-relaxed">
          {status.message}
        </p>

        {status.status === "rejected" && status.rejection_reason && (
          <div className="mt-4 bg-white rounded-xl p-3 text-left">
            <p className="text-xs font-semibold text-gray-500 mb-1">Sabab:</p>
            <p className="text-sm text-gray-700">{status.rejection_reason}</p>
          </div>
        )}

        {status.status === "pending" && (
          <button
            onClick={() => refetch()}
            className="mt-4 flex items-center gap-1.5 text-xs text-yellow-600 hover:text-yellow-700 mx-auto"
          >
            <RefreshCw size={12} />
            Yangilash
          </button>
        )}
      </div>

      {/* Vehicle info */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-5">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Avtomobil
        </h3>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center text-2xl">
            🚗
          </div>
          <div>
            <p className="font-bold text-gray-900">
              {profile.vehicle_make} {profile.vehicle_model}
            </p>
            <p className="text-sm text-gray-500">
              {profile.vehicle_year} · {profile.vehicle_color}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Davlat raqami", value: profile.vehicle_plate },
            { label: "O'rinlar soni", value: `${profile.vehicle_seats} ta` },
            { label: "Ariza topshirilgan", value: new Date(profile.created_at).toLocaleDateString("uz-UZ") },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-400">{label}</p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      {status.status === "approved" && (
        <Button fullWidth size="lg" onClick={() => router.push("/create-trip")}>
          <Car size={16} />
          Safar e'lon qilish
        </Button>
      )}

      {status.status === "rejected" && (
        <Button fullWidth size="lg" onClick={() => router.push("/profile/driver-apply")}>
          Qaytadan ariza topshirish
        </Button>
      )}

      {status.status === "pending" && (
        <div className="bg-gray-50 rounded-2xl p-5 text-center">
          <p className="text-sm text-gray-500">
            Ariza ko'rib chiqilganda sizga SMS xabar yuboriladi
          </p>
        </div>
      )}
    </div>
  );
}
