"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Users, Luggage, MapPin, CheckCircle,
  ChevronRight, Shield, MessageCircle, Phone, CalendarClock,
  CigaretteOff, PawPrint, Wallet,
} from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Stars from "@/components/ui/Stars";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { TripDetailSkeleton } from "@/components/ui/Skeleton";
import PhoneVerifyModal from "@/components/auth/PhoneVerifyModal";
import WomenOnlyGate from "@/components/trips/WomenOnlyGate";
import { useAuth } from "@/hooks/useAuth";
import { useMounted } from "@/hooks/useMounted";
import { useGeolocation } from "@/hooks/useGeolocation";
import api from "@/lib/api";
import { isAuthenticated, getApiError } from "@/lib/auth";
import type { TripResponse, BookingResponse } from "@/types";
import { clsx } from "clsx";
import { formatPrice } from "@/lib/format";

const MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];
const WEEKDAYS = [
  "Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba",
];

// "Payshanba, 3-sentabr" — sahifa sarlavhasi sifatida
function formatDate(d: string) {
  const dt = new Date(`${d}T00:00:00`);
  return `${WEEKDAYS[dt.getDay()]}, ${dt.getDate()}-${MONTHS[dt.getMonth()]}`;
}

function fmtTime(t: string) {
  return t.slice(0, 5);
}

// Bo'limlar orasidagi kulrang polosa — alohida kartalar o'rniga
function Band() {
  return <div className="h-2 bg-gray-100" />;
}

export default function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const mounted = useMounted();
  const { user } = useAuth();

  const [seats, setSeats] = useState(1);
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "click" | "payme">("cash");
  const [bookingModal, setBookingModal] = useState(false);
  const [verifyModal, setVerifyModal] = useState(false);
  const [genderModal, setGenderModal] = useState(false);
  const [bookingError, setBookingError] = useState("");

  // Olib ketish joyi — haydovchi shu manzilga boradi. Koordinata ixtiyoriy:
  // brauzerning o'zi beradi, xarita provayderi kerak emas.
  const [pickup, setPickup] = useState("");
  const { coords, state: geoState, error: geoError, request: useMyLocation } = useGeolocation();

  // ── Trip yuklab olish ──
  const { data: trip, isLoading, isError } = useQuery<TripResponse>({
    queryKey: ["trip", id],
    queryFn: async () => {
      const { data } = await api.get(`/trips/${id}`);
      return data;
    },
  });

  // ── Band qilish mutation ──
  const bookMutation = useMutation<BookingResponse, Error, void>({
    mutationFn: async () => {
      const { data } = await api.post("/bookings/", {
        trip_id: id,
        seats_count: seats,
        payment_method: paymentMethod,
        pickup_address: pickup.trim(),
        pickup_lat: coords?.lat,
        pickup_lng: coords?.lng,
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
    if (pickup.trim().length < 5) {
      setBookingError("Haydovchi sizni qayerdan olishini yozing");
      return;
    }
    setBookingError("");
    bookMutation.mutate();
  }

  // ── Skeletons ──
  if (isLoading) {
    return (
      <div className="max-w-[640px] mx-auto px-4 sm:px-6 py-6">
        <TripDetailSkeleton />
      </div>
    );
  }

  if (isError || !trip) {
    return (
      <div className="max-w-[640px] mx-auto px-4 sm:px-6 py-16 text-center">
        <p className="text-lg font-semibold text-gray-900 mb-2">Safar topilmadi</p>
        <Button onClick={() => router.back()} variant="outline">Orqaga</Button>
      </div>
    );
  }

  const totalPrice = trip.price_per_seat * seats;
  const isActive = trip.status === "active";
  // Haydovchi panelidan "Safar sahifasi" ga o'tganda o'z safarini ko'radi —
  // unga band qilish taklif qilinmaydi
  const isOwner = !!user && user.id === trip.driver.id;

  const fromSub = [trip.from_district?.name_uz, trip.from_address]
    .filter(Boolean).join(", ");
  const toSub = [trip.to_district?.name_uz, trip.to_address]
    .filter(Boolean).join(", ");

  function startBooking() {
    if (!isAuthenticated()) {
      router.push("/login?next=/trips/" + id);
      return;
    }
    // Tasdiqlanmagan raqamni backend baribir rad etadi — sababini
    // xato xabaridan emas, shu yerda ko'rsatamiz
    if (user && !user.is_phone_verified) {
      setVerifyModal(true);
      return;
    }
    // "Faqat ayollar" safari — jins belgilanmagan yoki erkak
    // bo'lsa, backend rad etadi; sababini shu yerda tushuntiramiz
    if (trip!.women_only && user && user.gender !== "female") {
      setGenderModal(true);
      return;
    }
    setBookingModal(true);
  }

  return (
    <div className="max-w-[640px] mx-auto sm:px-6 sm:py-6">
      <div className="bg-white sm:rounded-2xl sm:border sm:border-gray-100">

        {/* ── Sana + marshrut ── */}
        <div className="px-4 sm:px-6 pt-4 sm:pt-6 pb-5">
          <button
            onClick={() => router.back()}
            className="-ml-2 mb-4 w-9 h-9 rounded-full flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors"
            aria-label="Orqaga"
          >
            <ArrowLeft size={18} />
          </button>

          <h1 className="text-[26px] sm:text-3xl font-bold tracking-tight text-gray-900 mb-6">
            {formatDate(trip.departure_date)}
          </h1>

          {/* Jo'nash */}
          <div className="flex gap-3">
            <div className="w-12 shrink-0 pt-0.5 text-[17px] font-bold text-gray-900 tabular-nums">
              {fmtTime(trip.departure_time)}
            </div>
            <div className="w-3 shrink-0 flex flex-col items-center pt-2">
              <span className="w-3 h-3 rounded-full border-[3px] border-gray-900 shrink-0" />
              <span className="w-0.5 flex-1 bg-gray-900 my-1" />
            </div>
            <div className="flex-1 min-w-0 pb-6">
              <p className="text-lg font-bold text-gray-900">{trip.from_region.name_uz}</p>
              {fromSub && <p className="text-sm text-gray-500 mt-0.5">{fromSub}</p>}
            </div>
          </div>

          {/* Yo'ldagi to'xtashlar */}
          {trip.waypoints.map((wp) => (
            <div key={wp.id} className="flex gap-3">
              <div className="w-12 shrink-0 pt-1 text-sm font-semibold text-gray-400 tabular-nums">
                {wp.arrival_time ? fmtTime(wp.arrival_time) : ""}
              </div>
              <div className="w-3 shrink-0 flex flex-col items-center pt-2">
                <span className="w-2.5 h-2.5 rounded-full border-2 border-gray-300 bg-white shrink-0" />
                <span className="w-0.5 flex-1 bg-gray-900 my-1" />
              </div>
              <div className="flex-1 min-w-0 pb-6">
                <p className="text-base font-semibold text-gray-700">{wp.region.name_uz}</p>
                {wp.price_from_start > 0 && (
                  <p className="text-sm text-gray-500 mt-0.5">
                    {formatPrice(wp.price_from_start)} so&apos;m
                  </p>
                )}
              </div>
            </div>
          ))}

          {/* Yetib borish */}
          <div className="flex gap-3">
            <div className="w-12 shrink-0" />
            <div className="w-3 shrink-0 flex justify-center pt-2">
              <span className="w-3 h-3 rounded-full border-[3px] border-gray-900 shrink-0" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-lg font-bold text-gray-900">{trip.to_region.name_uz}</p>
              {toSub && <p className="text-sm text-gray-500 mt-0.5">{toSub}</p>}
            </div>
          </div>
        </div>

        <Band />

        {/* ── Joy soni + narx ── */}
        <div className="px-4 sm:px-6 py-5">
          {isOwner ? (
            // Haydovchi o'z safarini ko'rmoqda — band qilish yo'q (backend ham
            // rad etadi), narx va bo'sh o'rin faqat ma'lumot uchun
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-base font-semibold text-gray-900">Bir joy narxi</p>
                <p className="text-sm text-gray-400 mt-0.5">
                  {trip.available_seats} ta joy bo&apos;sh — {trip.total_seats} tadan
                </p>
              </div>
              <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">
                {formatPrice(trip.price_per_seat)}{" "}
                <span className="text-sm font-medium text-gray-400">so&apos;m</span>
              </p>
            </div>
          ) : isActive ? (
            <>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-base font-semibold text-gray-900">Joy soni</p>
                  <p className="text-sm text-gray-400 mt-0.5">
                    {trip.available_seats} ta joy bo&apos;sh
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSeats(Math.max(1, seats - 1))}
                    disabled={seats <= 1}
                    className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center text-lg font-bold text-gray-600 hover:border-gray-400 disabled:opacity-40 disabled:hover:border-gray-200 transition-colors"
                    aria-label="Kamaytirish"
                  >−</button>
                  <span className="w-8 text-center text-lg font-bold text-gray-900 tabular-nums">
                    {seats}
                  </span>
                  <button
                    onClick={() => setSeats(Math.min(trip.available_seats, seats + 1))}
                    disabled={seats >= trip.available_seats}
                    className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center text-lg font-bold text-gray-600 hover:border-gray-400 disabled:opacity-40 disabled:hover:border-gray-200 transition-colors"
                    aria-label="Ko'paytirish"
                  >+</button>
                </div>
              </div>

              <div className="flex items-end justify-between gap-4 mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Users size={15} className="text-gray-400" />
                  {formatPrice(trip.price_per_seat)} so&apos;m × {seats}
                </div>
                <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">
                  {formatPrice(totalPrice)}{" "}
                  <span className="text-sm font-medium text-gray-400">so&apos;m</span>
                </p>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-between gap-4">
              <p className="text-base font-semibold text-gray-700">
                {trip.status === "full" ? "Joylar tugadi" : "Safar yakunlandi"}
              </p>
              <p className="text-lg font-bold text-gray-400 tabular-nums">
                {formatPrice(trip.price_per_seat)} so&apos;m
              </p>
            </div>
          )}
        </div>

        <Band />

        {/* ── Haydovchi ── */}
        <div className="px-4 sm:px-6 py-5">
          <div className="flex items-center gap-3">
            <Avatar src={trip.driver.profile_photo} name={trip.driver.full_name} size="lg" />
            <div className="flex-1 min-w-0">
              <p className="text-lg font-bold text-gray-900 truncate">{trip.driver.full_name}</p>
              <Stars
                rating={trip.driver.rating_avg}
                showValue
                count={trip.driver.rating_count}
                className="mt-1"
              />
            </div>
            <Badge variant="success" dot>Tasdiqlangan</Badge>
          </div>

          <div className="mt-5 space-y-3.5">
            <div className="flex items-start gap-3 text-sm text-gray-600">
              <Shield size={19} className="text-green-500 shrink-0" />
              <span>Tasdiqlangan profil — {trip.driver.total_trips} ta safar</span>
            </div>
            {!isOwner && (
              <div className="flex items-start gap-3 text-sm text-gray-600">
                <CalendarClock size={19} className="text-gray-400 shrink-0" />
                <span>Joy darrov band bo&apos;ladi — haydovchining javobini kutish shart emas</span>
              </div>
            )}
            <div className="flex items-start gap-3 text-sm text-gray-600">
              <Wallet size={19} className="text-gray-400 shrink-0" />
              <span>
                {{
                  cash: "Naqd pul", click: "Click", payme: "Payme",
                  any: "Naqd, Click yoki Payme",
                }[trip.payment_type]}
              </span>
            </div>
            {!isOwner && (
              <>
                <div className="flex items-start gap-3 text-sm text-gray-600">
                  <Phone size={19} className="text-gray-400 shrink-0" />
                  <span>Haydovchining telefon raqami band qilganingizdan keyin ochiladi</span>
                </div>
                <div className="flex items-start gap-3 text-sm text-gray-600">
                  <CheckCircle size={19} className="text-green-500 shrink-0" />
                  <span>Bepul bekor qilish — jo&apos;nashdan 24 soat oldin</span>
                </div>
              </>
            )}
          </div>
        </div>

        <Band />

        {/* ── Shartlar ── */}
        <div className="px-4 sm:px-6 py-5">
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full text-sm">
              <Luggage size={14} />
              {{
                small: "Kichik yuk", medium: "O'rtacha yuk", large: "Katta yuk",
              }[trip.luggage_size]}
            </span>
            {!trip.smoking_allowed && (
              <span className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full text-sm">
                <CigaretteOff size={14} />Chekilmaydi
              </span>
            )}
            {trip.pets_allowed && (
              <span className="inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 px-3 py-1.5 rounded-full text-sm">
                <PawPrint size={14} />Hayvon mumkin
              </span>
            )}
            {trip.women_only && (
              <span className="inline-flex items-center gap-1.5 bg-pink-50 text-pink-600 px-3 py-1.5 rounded-full text-sm">
                Faqat ayollar
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full text-sm">
              {{
                silent: "Jim boradi", normal: "Oddiy suhbat", talkative: "Suhbatdosh",
              }[trip.driver.talk_level]}
            </span>
          </div>

          {trip.description && (
            <p className="text-sm text-gray-600 leading-relaxed mt-4 pt-4 border-t border-gray-100">
              {trip.description}
            </p>
          )}
        </div>

        {/* ── Pastdagi harakat paneli ── */}
        <div className="sticky bottom-[72px] md:bottom-4 z-30 px-4 sm:px-6 py-3 bg-white border-t border-gray-100 sm:rounded-b-2xl">
          {isOwner ? (
            <Link href="/driver" className="block">
              <Button fullWidth className="!rounded-full">
                Safarni panelda boshqarish
                <ChevronRight size={16} />
              </Button>
            </Link>
          ) : isActive ? (
            <div className="flex gap-3">
              <Link
                href={mounted && isAuthenticated() ? `/messages/new?driver=${trip.driver.id}` : "/login"}
                className="flex-1"
              >
                <Button variant="outline" fullWidth className="!rounded-full">
                  <MessageCircle size={16} />
                  Yozish
                </Button>
              </Link>
              <Button onClick={startBooking} className="flex-[1.4] !rounded-full">
                Band qilish
              </Button>
            </div>
          ) : (
            <Link href="/trips" className="block">
              <Button variant="outline" fullWidth className="!rounded-full">
                Boshqa safarlarni qidirish
                <ChevronRight size={16} />
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Booking modal */}
      <WomenOnlyGate
        open={genderModal}
        onClose={() => setGenderModal(false)}
        onAllowed={() => setBookingModal(true)}
      />

      <PhoneVerifyModal
        open={verifyModal}
        onClose={() => setVerifyModal(false)}
        onVerified={() => setBookingModal(true)}
        reason="Joy band qilish uchun telefon raqamingiz tasdiqlangan bo'lishi kerak — haydovchi siz bilan bog'lana olishi uchun."
      />

      <Modal open={bookingModal} onClose={() => setBookingModal(false)} title="Band qilishni tasdiqlash">
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
                {formatPrice(totalPrice)} so&apos;m
              </span>
            </div>
          </div>

          {/* Olib ketish joyi — haydovchi shu yerga keladi */}
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
              Haydovchi sizni qayerdan oladi?
            </label>
            <input
              value={pickup}
              onChange={(e) => setPickup(e.target.value)}
              placeholder="Masalan: Chilonzor 19-kvartal, 42-uy"
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-primary-400"
            />
            <button
              type="button"
              onClick={useMyLocation}
              disabled={geoState === "loading"}
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-primary-600 hover:text-primary-700 disabled:opacity-60"
            >
              <MapPin size={13} />
              {coords
                ? "Joylashuv qo'shildi ✓"
                : geoState === "loading"
                  ? "Aniqlanmoqda…"
                  : "Aniq joylashuvimni qo'shish"}
            </button>
            {geoState === "error" && geoError && (
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{geoError}</p>
            )}
            {coords && (
              <p className="text-xs text-gray-400 mt-1">
                Haydovchi buni xaritada ochib ko&apos;ra oladi.
              </p>
            )}
          </div>

          {/* To'lov usuli */}
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
              To&apos;lov usuli
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
