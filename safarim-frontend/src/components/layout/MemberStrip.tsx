"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarDays } from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Badge from "@/components/ui/Badge";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useMounted } from "@/hooks/useMounted";
import { shortDate } from "@/lib/date";
import type { BookingResponse } from "@/types";

/** Faol (kelgusi) buyurtma — safar bo'lib o'tmaganlari */
const ACTIVE_STATUSES = ["pending", "confirmed", "awaiting_confirmation"];

/**
 * Bosh sahifaning shaxsiy qismi — kirgan yo'lovchi uchun.
 *
 * Sahifaning o'zi hammaga bir xil (mehmonga ham, kirgan odamga ham), bu
 * blok esa faqat kirgan foydalanuvchiga: salomlashuv va yaqin safar.
 * Haydovchi kasbiy taksist — unga bosh sahifa kerak emas, panelga o'tadi.
 */
export default function MemberStrip() {
  const router = useRouter();
  const mounted = useMounted();
  const { user } = useAuth();

  const isDriver = user?.is_driver === true;

  useEffect(() => {
    if (isDriver) router.replace("/driver");
  }, [isDriver, router]);

  const { data: bookings = [] } = useQuery<BookingResponse[]>({
    queryKey: ["bookings", "my"],
    queryFn: async () => (await api.get("/bookings/my")).data,
    enabled: !!user && !isDriver,
  });

  if (!mounted || !user || isDriver) return null;

  const upcoming = bookings
    .filter((b) => ACTIVE_STATUSES.includes(b.status) && b.trip)
    .sort((a, b) =>
      `${a.trip!.departure_date}${a.trip!.departure_time}`.localeCompare(
        `${b.trip!.departure_date}${b.trip!.departure_time}`
      )
    )[0];

  const firstName = user.full_name?.split(" ")[0] ?? "";

  return (
    <div className="bg-white border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center gap-3 flex-wrap">
        <Avatar src={user.profile_photo} name={user.full_name} size="sm" />
        <p className="text-[15px] font-bold text-gray-900">
          Salom{firstName && `, ${firstName}`}
        </p>

        {upcoming?.trip && (
          <Link
            href={`/trips/${upcoming.trip.id}`}
            className="ml-auto flex items-center gap-2.5 min-w-0 bg-gray-50 hover:bg-gray-100 rounded-xl px-3 py-2 transition-colors"
          >
            <span className="flex items-center gap-1.5 text-[13.5px] font-semibold text-gray-900 min-w-0">
              <span className="truncate">{upcoming.trip.from_region.name_uz}</span>
              <ArrowRight size={12} className="text-gray-300 shrink-0" />
              <span className="truncate">{upcoming.trip.to_region.name_uz}</span>
            </span>
            <span className="flex items-center gap-1 text-xs text-gray-500 shrink-0">
              <CalendarDays size={12} className="text-gray-400" />
              {shortDate(upcoming.trip.departure_date)} · {upcoming.trip.departure_time.slice(0, 5)}
            </span>
            <Badge variant={upcoming.status === "confirmed" ? "success" : "warning"} size="sm">
              {upcoming.status === "confirmed" ? "Tasdiqlangan" : "Kutilmoqda"}
            </Badge>
          </Link>
        )}
      </div>
    </div>
  );
}
