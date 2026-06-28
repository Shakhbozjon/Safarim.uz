"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Clock, Users, Luggage, MapPin, CheckCircle,
  ChevronRight, Star, Shield, MessageCircle, Phone,
  CigaretteOff, PawPrint, Wind,
} from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Stars from "@/components/ui/Stars";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { TripDetailSkeleton } from "@/components/ui/Skeleton";
import api from "@/lib/api";
import { isAuthenticated, getApiError } from "@/lib/auth";
import type { TripResponse, BookingResponse } from "@/types";
import { clsx } from "clsx";

function formatPrice(n: number) {
  return new Intl.NumberFormat("uz-UZ").format(n);
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("uz-UZ", {
    day: "numeric", month: "long", year: "numeric", weekday: "long",
  });
}

function fmtTime(t: string) {
  return t.slice(0, 5);
}

export default function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [seats, setSeats] = useState(1);
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "click" | "payme">("cash");
  const [bookingModal, setBookingModal] = useState(false);
  const [bookingError, setBookingError] = useState("");

  // ── Trip yuklab olish ──
  const { data: trip, isLoading, isError } = useQuery<TripResponse>({
    queryKey: ["trip", id],
    queryFn: async () => {
      const { data } = await api.get(`/trips/${id}`);
      return data;
    },
  });

  // ── Bron qilish mutation ──
  const bookMutation = useMutation<BookingResponse, Error, void>({
    mutationFn: async () => {
      const { data } = await api.post("/bookings/", {
        trip_id: id,
        seats_count: seats,
        payment_method: paymentMethod,
      });
      return data;
    },
    onSuccess: (booking) => {
      setBookingModal(false);
      qc.invalidateQueries({ queryKey: ["trip", id] });
      qc.invalidateQueries({ queryKey: ["my-bookings"] });
      router.push(`/my-trips?booked=${booking.id}`);
    },
    onError: (err: any) => {
      setBookingError(getApiError(err));
    },
  });

  function handleBook() {
    if (!isAuthenticated()) {
      router.push("/login?next=/trips/" + id);
      return;
    }
    setBookingError("");
    bookMutation.mutate();
  }

  // ── Skeletons ──
  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
        <TripDetailSkeleton />
      </div>
    );
  }

  if (isError || !trip) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 text-center">
        <p className="text-lg font-semibold text-gray-900 mb-2">Safar topilmadi</p>
        <Button onClick={() => router.back()} variant="outline">Orqaga</Button>
      </div>
    );
  }

  const totalPrice = trip.price_per_seat * seats;
  const commission = totalPrice * (totalPrice > 200_000 ? 0.05 : 0.02);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Orqaga
      </button>

      <div className="grid lg:grid-cols-[1fr_340px] gap-6">
        {/* Left column */}
        <div className="space-y-5">

          {/* Route card */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-5">
              <Clock size={14} />
              {formatDate(trip.departure_date)}
            </div>

            <div className="relative">
              {/* From */}
              <div className="flex items-start gap-4">
                <div className="flex flex-col items-center">
                  <div className="route-dot-from mt-1.5" />
                  <div className="w-0.5 bg-gray-200 flex-1 my-1" style={{ minHeight: "2.5rem" }} />
                </div>
                <div className="pb-6">
                  <p className="text-2xl font-bold text-gray-900">{trip.from_region.name_uz}</p>
                  <p className="text-3xl font-bold text-primary-500 tabular-nums mt-0.5">
                    {fmtTime(trip.departure_time)}
                  </p>
                  {trip.from_address && (
                    <p className="text-sm text-gray-400 mt-1">{trip.from_address}</p>
                  )}
                </div>
              </div>

              {/* Waypoints */}
              {trip.waypoints.map((wp) => (
                <div key={wp.id} className="flex items-start gap-4 mb-0">
                  <div className="flex flex-col items-center">
                    <div className="w-2 h-2 rounded-full bg-gray-300 border-2 border-white ring-1 ring-gray-200 mt-1.5" />
                    <div className="w-0.5 bg-gray-200 flex-1 my-1" style={{ minHeight: "2.5rem" }} />
                  </div>
                  <div className="pb-6">
                    <p className="text-base font-semibold text-gray-700">{wp.region.name_uz}</p>
                    {wp.arrival_time && (
                      <p className="text-sm text-gray-500 tabular-nums">{fmtTime(wp.arrival_time)}</p>
                    )}
                    {wp.price_from_start > 0 && (
                      <p className="text-xs text-primary-500 mt-0.5">
                        {formatPrice(wp.price_from_start)} so'm
                      </p>
                    )}
                  </div>
                </div>
              ))}

              {/* To */}
              <div className="flex items-start gap-4">
                <div className="route-dot-to mt-1.5" />
                <div>
                  <p className="text-2xl font-bold text-gray-900">{trip.to_region.name_uz}</p>
                  {trip.to_address && (
                    <p className="text-sm text-gray-400 mt-1">{trip.to_address}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Driver card */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Haydovchi</h2>
            <div className="flex items-start gap-4">
              <Avatar src={trip.driver.profile_photo} name={trip.driver.full_name} size="lg" />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-lg font-bold text-gray-900">{trip.driver.full_name}</p>
                    <Stars
                      rating={trip.driver.rating_avg}
                      showValue
                      count={trip.driver.rating_count}
                      className="mt-1"
                    />
                  </div>
                  <Badge variant="success" dot>Tasdiqlangan</Badge>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  {[
                    { label: "Jami safarlar", value: trip.driver.total_trips },
                    { label: "Muloqot darajasi", value: {
                        silent: "Jim", normal: "Oddiy", talkative: "Suhbatdosh"
                      }[trip.driver.talk_level] },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-gray-50 rounded-xl p-3">
                      <p className="text-xs text-gray-400">{label}</p>
                      <p className="text-sm font-semibold text-gray-900 mt-0.5">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Amenities & conditions */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Shartlar</h2>
            <div className="flex flex-wrap gap-3">
              <div className={clsx(
                "flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium",
                trip.luggage_size === "large"
                  ? "bg-gray-50 text-gray-700"
                  : "bg-gray-50 text-gray-400"
              )}>
                <Luggage size={15} />
                {{small: "Kichik yukxalta", medium: "O'rtacha yukxalta", large: "Katta yukxalta"}[trip.luggage_size]}
              </div>

              {!trip.smoking_allowed && (
                <div className="flex items-center gap-2 bg-red-50 text-red-600 px-4 py-2.5 rounded-xl text-sm font-medium">
                  <CigaretteOff size={15} />Chekish ta'qiqlangan
                </div>
              )}
              {trip.pets_allowed && (
                <div className="flex items-center gap-2 bg-amber-50 text-amber-700 px-4 py-2.5 rounded-xl text-sm font-medium">
                  <PawPrint size={15} />Hayvon mumkin
                </div>
              )}
              {trip.women_only && (
                <div className="flex items-center gap-2 bg-pink-50 text-pink-600 px-4 py-2.5 rounded-xl text-sm font-medium">
                  Faqat ayollar
                </div>
              )}
              <div className="flex items-center gap-2 bg-gray-50 text-gray-500 px-4 py-2.5 rounded-xl text-sm">
                <Shield size={15} />Himoyalangan to'lov
              </div>
            </div>

            {trip.description && (
              <div className="mt-4 pt-4 border-t border-gray-50">
                <p className="text-sm text-gray-600 leading-relaxed">{trip.description}</p>
              </div>
            )}
          </div>

          {/* To'lov turi */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">To'lov turi</h2>
            <p className="text-sm text-gray-600">
              {{cash: "Naqd pul", click: "Click", payme: "Payme", any: "Har qanday usul"}[trip.payment_type]}
            </p>
          </div>
        </div>

        {/* Right column — Booking widget */}
        <div className="lg:sticky lg:top-20 h-fit">
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-card-hover">
            {trip.status !== "active" ? (
              <div className="text-center py-4">
                <p className="text-lg font-bold text-gray-700 mb-1">
                  {trip.status === "full" ? "Joylar tugadi" : "Safar yakunlandi"}
                </p>
                <p className="text-sm text-gray-400">Boshqa safarlarni ko'ring</p>
                <Link href="/trips" className="mt-4 block">
                  <Button variant="outline" fullWidth>Qidirish</Button>
                </Link>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <p className="text-3xl font-bold text-gray-900 tabular-nums">
                      {formatPrice(trip.price_per_seat * seats)}{" "}
                      <span className="text-base font-normal text-gray-400">so'm</span>
                    </p>
                    {seats > 1 && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {formatPrice(trip.price_per_seat)} so'm × {seats} joy
                      </p>
                    )}
                  </div>
                  <Badge variant={trip.available_seats <= 2 ? "warning" : "success"} dot>
                    {trip.available_seats} joy bor
                  </Badge>
                </div>

                {/* Seats selector */}
                <div className="mb-5">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                    Joy soni
                  </label>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setSeats(Math.max(1, seats - 1))}
                      className="w-9 h-9 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-bold transition-colors"
                    >−</button>
                    <span className="flex-1 text-center text-lg font-bold text-gray-900 tabular-nums">{seats}</span>
                    <button
                      onClick={() => setSeats(Math.min(trip.available_seats, seats + 1))}
                      className="w-9 h-9 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 font-bold transition-colors"
                    >+</button>
                  </div>
                </div>

                <Button
                  fullWidth
                  size="lg"
                  onClick={() => {
                    if (!isAuthenticated()) {
                      router.push("/login?next=/trips/" + id);
                      return;
                    }
                    setBookingModal(true);
                  }}
                >
                  Joy band qilish
                </Button>

                <div className="mt-5 space-y-2.5">
                  {[
                    { icon: Shield, text: "Himoyalangan to'lov" },
                    { icon: Phone, text: "Bron tasdiqlanganidan keyin telefon ochiladi" },
                    { icon: CheckCircle, text: "Bepul bekor qilish (24s oldin)" },
                  ].map(({ icon: Icon, text }) => (
                    <div key={text} className="flex items-start gap-2.5 text-xs text-gray-500">
                      <Icon size={13} className="text-green-500 mt-0.5 shrink-0" />
                      {text}
                    </div>
                  ))}
                </div>

                <div className="mt-4 pt-4 border-t border-gray-50">
                  <Link
                    href={isAuthenticated() ? `/messages/new?driver=${trip.driver.id}` : `/login`}
                    className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    <MessageCircle size={15} />
                    Haydovchiga savol berish
                    <ChevronRight size={14} className="ml-auto" />
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Booking modal */}
      <Modal open={bookingModal} onClose={() => setBookingModal(false)} title="Bronni tasdiqlash">
        <div className="space-y-4">
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Marshrut</span>
              <span className="font-medium text-gray-900">
                {trip.from_region.name_uz} → {trip.to_region.name_uz}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Sana</span>
              <span className="font-medium text-gray-900">
                {trip.departure_date} · {fmtTime(trip.departure_time)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Joy</span>
              <span className="font-medium text-gray-900">{seats} ta</span>
            </div>
            <div className="flex justify-between text-sm border-t border-gray-200 pt-3">
              <span className="font-semibold text-gray-900">Jami</span>
              <span className="text-lg font-bold text-primary-600 tabular-nums">
                {formatPrice(totalPrice)} so'm
              </span>
            </div>
          </div>

          {/* To'lov usuli */}
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
              To'lov usuli
            </label>
            <div className="grid grid-cols-3 gap-2">
              {([
                { value: "cash",  label: "Naqd" },
                { value: "click", label: "Click" },
                { value: "payme", label: "Payme" },
              ] as const).filter(({ value }) =>
                trip.payment_type === "any" || trip.payment_type === value
              ).map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setPaymentMethod(value)}
                  className={clsx(
                    "py-2.5 rounded-xl text-sm font-medium border transition-all",
                    paymentMethod === value
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {bookingError && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
              {bookingError}
            </div>
          )}

          <div className="flex gap-3">
            <Button variant="outline" fullWidth onClick={() => setBookingModal(false)}>
              Bekor qilish
            </Button>
            <Button fullWidth onClick={handleBook} loading={bookMutation.isPending}>
              Tasdiqlash
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
