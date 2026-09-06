"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarDays } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import HeroSearchCard from "@/components/trips/HeroSearchCard";
import Badge from "@/components/ui/Badge";
import Avatar from "@/components/ui/Avatar";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useMounted } from "@/hooks/useMounted";
import type { BookingResponse } from "@/types";
import PopularRoutes from "@/components/trips/PopularRoutes";

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

      {/* Navbar o'zi 64px joy egallaydi — bu yerda yana katta bo'shliq
          qoldirilsa, qidiruv ekrandan pastga tushib ketadi */}
      <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 pt-5 pb-14">
        <div className="flex items-center gap-3 mb-4">
          <Avatar src={user?.profile_photo ?? null} name={user?.full_name} size="md" />
          <div className="min-w-0">
            <p className="text-[17px] font-bold text-gray-900 truncate leading-tight">
              Salom{firstName && `, ${firstName}`}
            </p>
            <p className="text-[13px] text-gray-500">Qayerga bormoqchisiz?</p>
          </div>
        </div>

        {/* Qidiruv — yo'lovchining asosiy amali */}
        <div className="mb-4">
          <HeroSearchCard />
        </div>

        {/* Eng ko'p safar bor yo'nalishlar — bir bosishda qidiruvga o'tadi */}
        <PopularRoutes
          variant="chips"
          limit={4}
          className="flex gap-2 overflow-x-auto pb-1 mb-8 -mx-4 px-4 sm:mx-0 sm:px-0"
        />

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

        {/* Ommabop yo'nalishlar — safar bor yo'nalishlargina ko'rsatiladi */}
        <section>
          <PopularRoutes
            variant="cards"
            limit={6}
            heading="Ommabop yo'nalishlar"
            moreHref="/trips"
            className="grid gap-3.5 sm:grid-cols-2"
          />
        </section>
      </main>

      <Footer />
    </div>
  );
}
