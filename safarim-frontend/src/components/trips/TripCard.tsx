import Link from "next/link";
import { Wind, Luggage, MapPin, Clock, Users, CigaretteOff, PawPrint } from "lucide-react";
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

export default function TripCard({ trip, className }: TripCardProps) {
  const { driver } = trip;
  const waypoints = trip.waypoints ?? [];

  return (
    <Link href={`/trips/${trip.id}`} className="block group">
      <article
        className={clsx(
          "bg-white rounded-2xl border border-gray-100 p-5 transition-all duration-200",
          "hover:border-gray-200 hover:shadow-card-hover group-hover:-translate-y-0.5",
          className
        )}
      >
        {/* Driver row */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <Avatar src={driver.profile_photo} name={driver.full_name} size="md" />
            <div>
              <p className="text-sm font-semibold text-gray-900 leading-tight">{driver.full_name}</p>
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

        {/* Route row */}
        <div className="flex items-center gap-3">
          {/* From */}
          <div className="flex-1 min-w-0">
            <p className="text-xl font-bold text-gray-900 truncate">{trip.from_region.name_uz}</p>
            <p className="text-sm text-gray-500 mt-0.5 font-medium">{fmtTime(trip.departure_time)}</p>
          </div>

          {/* Line */}
          <div className="flex flex-col items-center gap-1.5 shrink-0 px-2">
            <div className="flex items-center gap-1">
              <span className="route-dot-from" />
              <div className="w-12 sm:w-20 h-px bg-gray-200 relative">
                {waypoints.length > 0 && (
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 flex gap-1">
                    {waypoints.map((_, i) => (
                      <span key={i} className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                    ))}
                  </div>
                )}
              </div>
              <span className="route-dot-to" />
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Clock size={10} />
              <span>{driver.total_trips} safar</span>
            </div>
          </div>

          {/* To */}
          <div className="flex-1 min-w-0 text-right">
            <p className="text-xl font-bold text-gray-900 truncate">{trip.to_region.name_uz}</p>
            <p className="text-sm text-gray-500 mt-0.5 font-medium">{trip.departure_date}</p>
          </div>
        </div>

        {/* Waypoints */}
        {waypoints.length > 0 && (
          <div className="flex items-center gap-1 mt-2 text-xs text-gray-400">
            <MapPin size={11} />
            <span>{waypoints.map((w) => w.region.name_uz).join(" → ")} orqali</span>
          </div>
        )}

        {/* Footer row */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-50 gap-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
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
            <div className="flex items-center gap-1 text-sm text-gray-500">
              <Users size={13} />
              <span>{trip.available_seats} joy</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-lg font-bold text-gray-900 leading-tight tabular-nums">
                {formatPrice(trip.price_per_seat)}{" "}
                <span className="text-sm font-medium text-gray-400">so'm</span>
              </p>
              <p className="text-xs text-gray-400">/ joy</p>
            </div>
            <Button size="sm" className="shrink-0">Bron</Button>
          </div>
        </div>
      </article>
    </Link>
  );
}
