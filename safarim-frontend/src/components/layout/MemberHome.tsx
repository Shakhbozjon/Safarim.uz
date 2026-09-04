"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarDays, MapPin } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import HeroSearchCard from "@/components/trips/HeroSearchCard";
import RouteLink from "@/components/trips/RouteLink";
import Badge from "@/components/ui/Badge";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useMounted } from "@/hooks/useMounted";
import type { BookingResponse } from "@/types";

const QUICK = [
  { from: "Toshkent", to: "Samarqand", fromSlug: "tashkent-city", toSlug: "samarqand" },
  { from: "Toshkent", to: "Namangan",  fromSlug: "tashkent-city", toSlug: "namangan" },
  { from: "Toshkent", to: "Buxoro",    fromSlug: "tashkent-city", toSlug: "bukhara" },
  { from: "Samarqand", to: "Buxoro",   fromSlug: "samarqand",     toSlug: "bukhara" },
];

const UZ_MON = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];

function fmtDate(d: string) {
  const parts = d.split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return d;
  const [, m, day] = parts;
  return `${day}-${UZ_MON[m - 1] ?? ""}`;
}

/** Faol (kelgusi) buyurtma — safar bo'lib o'tmaganlari */
const ACTIVE_STATUSES = ["pending", "confirmed", "awaiting_confirmation"];

/**
 * Kirgan foydalanuvchi uchun bosh sahifa.
 *
 * Haydovchi — kasbiy taksist, bosh sahifa unga kerak emas → panelga yo'naltiriladi.
 * Yo'lovchi esa "/" da qoladi: marketing o'rniga qidiruv va yaqin safari ko'rsatiladi.
 */
export default function MemberHome() {
  const router = useRouter();
  const mounted = useMounted();
  const { user, isLoading } = useAuth();

  const isDriver = user?.is_driver === true;

  useEffect(() => {
    if (isDriver) router.replace("/driver");
  }, [isDriver, router]);

  const { data: bookings = [] } = useQuery<BookingResponse[]>({
    queryKey: ["bookings", "my"],
    queryFn: async () => (await api.get("/bookings/my")).data,
    enabled: !!user && !isDriver,
  });

  const upcoming = bookings
    .filter((b) => ACTIVE_STATUSES.includes(b.status) && b.trip)
    .sort((a, b) =>
      `${a.trip!.departure_date}${a.trip!.departure_time}`.localeCompare(
        `${b.trip!.departure_date}${b.trip!.departure_time}`
      )
    )[0];

  // Haydovchi yo'naltirilguncha / profil yuklanguncha — bo'sh ekran o'rniga spinner.
  // `mounted` shart: serverda cookie ko'rinmaydi, brauzerda ko'rinadi — ikkala
  // tomon birinchi renderda aynan shu spinnerni chizsin (hydration mos kelsin).
  if (!mounted || isLoading || isDriver) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <span className="w-7 h-7 rounded-full border-2 border-gray-200 border-t-primary-500 animate-spin" />
      </div>
    );
  }

  const firstName = user?.full_name?.split(" ")[0] ?? "";

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden bg-gray-50/60">
      <Navbar />

      <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-14">
        <h1 className="text-[clamp(24px,4vw,32px)] font-extrabold tracking-tight text-gray-900 mb-1">
          Salom{firstName && `, ${firstName}`}!
        </h1>
        <p className="text-[15px] text-gray-500 mb-7">Qayerga bormoqchisiz?</p>

        {/* Qidiruv — yo'lovchining asosiy amali */}
        <div className="mb-8">
          <HeroSearchCard />
        </div>

        {/* Yaqin safar */}
        {upcoming?.trip && (
          <section className="mb-8">
            <div className="flex items-center justify-between gap-3 mb-3">
              <h2 className="text-[17px] font-bold text-gray-900">Yaqin safaringiz</h2>
              <Link href="/my-trips" className="text-sm font-semibold text-primary-600 hover:text-primary-700">
                Barchasi →
              </Link>
            </div>
            <Link
              href={`/trips/${upcoming.trip.id}`}
              className="block bg-white rounded-2xl border border-gray-100 p-4 sm:p-5 hover:border-gray-200 hover:shadow-card-hover transition-all"
            >
              <div className="flex items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2 text-[16px] font-bold text-gray-900 min-w-0">
                  <span className="truncate">{upcoming.trip.from_region.name_uz}</span>
                  <ArrowRight size={15} className="text-gray-300 shrink-0" />
                  <span className="truncate">{upcoming.trip.to_region.name_uz}</span>
                </div>
                <Badge variant={upcoming.status === "confirmed" ? "success" : "warning"} size="sm">
                  {upcoming.status === "confirmed" ? "Tasdiqlangan" : "Kutilmoqda"}
                </Badge>
              </div>
              <div className="flex items-center gap-4 text-[13px] text-gray-500">
                <span className="flex items-center gap-1.5">
                  <CalendarDays size={13} className="text-gray-400" />
                  {fmtDate(upcoming.trip.departure_date)} · {upcoming.trip.departure_time.slice(0, 5)}
                </span>
                <span className="tabular-nums">{upcoming.seats_count} joy</span>
              </div>
            </Link>
          </section>
        )}

        {/* Ommabop yo'nalishlar */}
        <section>
          <h2 className="text-[17px] font-bold text-gray-900 mb-3">Ommabop yo'nalishlar</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {QUICK.map((r) => (
              <RouteLink
                key={`${r.from}-${r.to}`}
                fromSlug={r.fromSlug}
                toSlug={r.toSlug}
                className="flex items-center gap-2.5 bg-white border border-gray-100 rounded-2xl px-4 py-3.5 text-[15px] font-semibold text-gray-800 hover:border-primary-200 hover:shadow-card-hover transition"
              >
                <MapPin size={15} className="text-primary-500 shrink-0" />
                <span className="truncate">{r.from}</span>
                <ArrowRight size={14} className="text-gray-300 shrink-0" />
                <span className="truncate">{r.to}</span>
              </RouteLink>
            ))}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
