import Link from "next/link";
import { Luggage, MapPin, Users, CigaretteOff, PawPrint } from "lucide-react";
import { clsx } from "clsx";
import Avatar from "@/components/ui/Avatar";
import Stars from "@/components/ui/Stars";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import type { TripResponse } from "@/types";

interface TripCardProps {
  trip: TripResponse;
  className?: string;
}

function formatPrice(price: number) {
  return new Intl.NumberFormat("uz-UZ").format(price);
}

/** "HH:MM:SS" yoki "HH:MM" → "HH:MM" */
function fmtTime(t: string) {
  return t.slice(0, 5);
}

const UZ_MON = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];

/** "2026-08-10" → "10-avg" */
function fmtDate(d: string) {
  const parts = d.split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return d;
  const [, m, day] = parts;
  return `${day}-${UZ_MON[m - 1] ?? ""}`;
}

export default function TripCard({ trip, className }: TripCardProps) {
  const { driver } = trip;
  const waypoints = trip.waypoints ?? [];

  return (
    <Link href={`/trips/${trip.id}`} className="block group">
      <article
        className={clsx(
          "bg-white rounded-2xl border border-gray-100 p-4 sm:p-5 transition-all duration-200",
          "hover:border-gray-200 hover:shadow-card-hover group-hover:-translate-y-0.5",
          className
        )}
      >
        {/* Driver row */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <Avatar src={driver.profile_photo} name={driver.full_name} size="md" />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-900 leading-tight truncate">{driver.full_name}</p>
              <Stars
                rating={driver.rating_avg}
                size={12}
                showValue
                count={driver.rating_count}
                className="mt-0.5"
              />
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {trip.available_seats <= 2 && trip.available_seats > 0 && (
              <Badge variant="warning" size="sm">{trip.available_seats} joy qoldi</Badge>
            )}
            {trip.women_only && (
              <Badge variant="default" size="sm">Faqat ayollar</Badge>
            )}
          </div>
        </div>

        {/* Route — vertikal timeline (to'liq nomlar, mobilга mos) */}
        <div className="flex gap-3">
          <div className="flex flex-col items-center pt-1.5 shrink-0">
            <span className="w-2.5 h-2.5 rounded-full border-2 border-primary-500 bg-white shrink-0" />
            <span className="w-0.5 flex-1 min-h-[22px] bg-gray-200 my-1" />
            <span className="w-2.5 h-2.5 rounded-full bg-primary-500 shrink-0" />
          </div>
          <div className="flex-1 min-w-0 flex flex-col justify-between gap-3.5">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[17px] font-bold text-gray-900 truncate">{trip.from_region.name_uz}</p>
              <p className="text-sm font-semibold text-gray-600 shrink-0 tabular-nums">{fmtTime(trip.departure_time)}</p>
            </div>
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[17px] font-bold text-gray-900 truncate">{trip.to_region.name_uz}</p>
              <p className="text-sm text-gray-400 shrink-0">{fmtDate(trip.departure_date)}</p>
            </div>
          </div>
        </div>

        {/* Waypoints */}
        {waypoints.length > 0 && (
          <div className="flex items-center gap-1 mt-2.5 text-xs text-gray-400 min-w-0">
            <MapPin size={11} className="shrink-0" />
            <span className="truncate">{waypoints.map((w) => w.region.name_uz).join(" → ")} orqali</span>
          </div>
        )}

        {/* Footer row */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-50 gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex items-center gap-2 shrink-0">
              {trip.luggage_size === "large" && (
                <span title="Katta yukxalta" className="text-gray-400">
                  <Luggage size={15} />
                </span>
              )}
              {!trip.smoking_allowed && (
                <span title="Chekish ta'qiqlangan" className="text-gray-400">
                  <CigaretteOff size={15} />
                </span>
              )}
              {trip.pets_allowed && (
                <span title="Hayvon mumkin" className="text-gray-400">
                  <PawPrint size={15} />
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 text-sm text-gray-500 shrink-0">
              <Users size={13} />
              <span>{trip.available_seats} joy</span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <p className="text-lg font-extrabold text-accent-700 leading-tight tabular-nums tracking-tight">
                {formatPrice(trip.price_per_seat)}{" "}
                <span className="text-sm font-semibold text-gray-400">so'm</span>
              </p>
              <p className="text-xs text-gray-400">/ joy</p>
            </div>
            <Button size="sm" className="shrink-0">Band qilish</Button>
          </div>
        </div>
      </article>
    </Link>
  );
}
