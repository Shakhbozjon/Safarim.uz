"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Car, Plus, MapPin, Users, ChevronRight, ChevronDown,
  Calendar, Banknote, AlertCircle, AlertTriangle,
  ArrowDownLeft, ArrowUpRight, X, CreditCard, History,
  RefreshCw, Clock, Star, Phone, MessageCircle, TrendingUp,
  ShieldCheck, Wallet,
} from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { clsx } from "clsx";
import type { TripResponse, BookingResponse, DriverReviewsResponse, DriverProfileResponse } from "@/types";

interface EarningsRecord {
  month: string;
  total_cash_bookings: number;
  total_commission: number;
  is_paid: boolean;
}

interface WalletInfo {
  balance: number;
  min_balance: number;
  is_blocked: boolean;
  transactions: {
    id: string;
    amount: number;
    tx_type: string;
    description: string;
    balance_after: number;
    created_at: string;
  }[];
}

function formatPrice(n: number) {
  return new Intl.NumberFormat("uz-UZ").format(n);
}
function formatShort(n: number) {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (abs >= 1_000) return Math.round(n / 1_000) + "K";
  return String(n);
}
function formatDate(d: string) {
  return new Date(d).toLocaleDateString("uz-UZ", { day: "numeric", month: "short" });
}

// ─── Tranzaksiya turi ikonkasi ─────────────────────────────────────────────
function TxIcon({ type }: { type: string }) {
  const map: Record<string, { icon: typeof ArrowUpRight; bg: string; color: string }> = {
    cash_commission: { icon: ArrowDownLeft, bg: "bg-red-50",    color: "text-red-500"   },
    online_earning:  { icon: ArrowUpRight,  bg: "bg-green-50",  color: "text-green-500" },
    topup:           { icon: ArrowUpRight,  bg: "bg-blue-50",   color: "text-blue-500"  },
    withdrawal:      { icon: ArrowDownLeft, bg: "bg-orange-50", color: "text-orange-500"},
    refund:          { icon: ArrowUpRight,  bg: "bg-teal-50",   color: "text-teal-500"  },
  };
  const cfg = map[type] ?? { icon: ArrowUpRight, bg: "bg-gray-50", color: "text-gray-400" };
  const Icon = cfg.icon;
  return (
    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${cfg.bg}`}>
      <Icon size={16} className={cfg.color} />
    </div>
  );
}

const TX_LABELS: Record<string, string> = {
  cash_commission: "Naqd komissiya",
  online_earning:  "Online daromad",
  topup:           "To'ldirish",
  withdrawal:      "Yechib olish",
  refund:          "Qaytarma",
};

// ─── Bron holati yorlig'i ──────────────────────────────────────────────────
const BSTATUS: Record<string, { label: string; cls: string }> = {
  pending:               { label: "Kutilmoqda",       cls: "bg-yellow-100 text-yellow-700" },
  confirmed:             { label: "Tasdiqlangan",     cls: "bg-green-100 text-green-700" },
  awaiting_confirmation: { label: "Tasdiq kutilmoqda", cls: "bg-amber-100 text-amber-700" },
  disputed:              { label: "Nizo",             cls: "bg-purple-100 text-purple-700" },
  completed:             { label: "Bajarilgan",       cls: "bg-gray-100 text-gray-600" },
  cancelled:             { label: "Bekor qilingan",   cls: "bg-red-100 text-red-600" },
  no_show:               { label: "Kelmadi",          cls: "bg-red-100 text-red-600" },
};

// ─── Karta raqami formatlash (xxxx xxxx xxxx xxxx) ────────────────────────
function formatCard(raw: string) {
  return raw.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
}

// ─── API xato xabarini o'qish ──────────────────────────────────────────────
function extractError(err: any): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0]?.msg?.replace(/^Value error,\s*/, "") ?? "Ma'lumot noto'g'ri";
  }
  if (!err?.response) return "Internet bilan muammo. Qayta urinib ko'ring";
  return "Serverda xato yuz berdi";
}

// ─── Toggle ────────────────────────────────────────────────────────────────
function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onChange}
      className={clsx(
        "relative w-11 h-6 rounded-full transition-colors shrink-0",
        checked ? "bg-green-500" : "bg-gray-200",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <span className={clsx(
        "absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform",
        checked && "translate-x-5"
      )} />
    </button>
  );
}

export default function DriverDashboardPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();

  // Pul yechish modal holati
  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [withdrawError, setWithdrawError] = useState("");
  const [withdrawDone, setWithdrawDone] = useState(false);

  // To'ldirish modal holati
  const [topupOpen, setTopupOpen]     = useState(false);
  const [topupAmount, setTopupAmount] = useState("");
  const [topupDone, setTopupDone]     = useState(false);
  const [topupError, setTopupError]   = useState("");

  // Qayta e'lon qilish modal holati
  const [republishId, setRepublishId]     = useState<string | null>(null);
  const [republishDate, setRepublishDate] = useState("");
  const [republishError, setRepublishError] = useState("");

  // Safarlar + ochilgan safar (yo'lovchilar) + depozit tarixi
  const [showAllTrips, setShowAllTrips]  = useState(false);
  const [expandedTrip, setExpandedTrip] = useState<string | null>(null);
  const [showTx, setShowTx]             = useState(false);

  // "Kelmadi" ogohlantirish modali — soxta belgilashning oldini olish uchun
  const [noShowConfirmId, setNoShowConfirmId] = useState<string | null>(null);

  // Auth + driver guard
  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.replace("/login"); return; }
    if (!user.is_driver) { router.replace("/profile"); return; }
  }, [user, authLoading, router]);

  const { data: trips = [], isLoading: tripsLoading } = useQuery<TripResponse[]>({
    queryKey: ["driver-trips"],
    queryFn: async () => {
      const { data } = await api.get("/trips/my");
      return data;
    },
    enabled: !!user?.is_driver,
  });

  const { data: bookings = [] } = useQuery<BookingResponse[]>({
    queryKey: ["driver-bookings"],
    queryFn: async () => {
      const { data } = await api.get("/bookings/driver");
      return data;
    },
    enabled: !!user?.is_driver,
  });

  const { data: earnings = [] } = useQuery<EarningsRecord[]>({
    queryKey: ["driver-earnings"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me/earnings");
      return data;
    },
    enabled: !!user?.is_driver,
  });

  const {
    data: wallet,
    isLoading: walletLoading,
    isError: walletError,
  } = useQuery<WalletInfo>({
    queryKey: ["driver-wallet"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me/wallet");
      return data;
    },
    enabled: !!user?.is_driver,
    refetchInterval: 60_000,
  });

  const { data: reviewData } = useQuery<DriverReviewsResponse>({
    queryKey: ["driver-reviews", user?.id],
    queryFn: async () => {
      const { data } = await api.get(`/reviews/driver/${user!.id}`);
      return data;
    },
    enabled: !!user?.id && !!user?.is_driver,
  });

  const { data: profile } = useQuery<DriverProfileResponse>({
    queryKey: ["driver-profile"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me");
      return data;
    },
    enabled: !!user?.is_driver,
  });

  // Pauza (Safarlarim ko'rinsin) toggle
  const pauseMutation = useMutation({
    mutationFn: (pause: boolean) =>
      api.post(`/drivers/me/${pause ? "pause" : "resume"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["driver-profile"] }),
  });

  // Preferences toggle (chekish, hayvon, faqat ayollar)
  const prefMutation = useMutation({
    mutationFn: (body: Record<string, any>) => api.put("/drivers/me/preferences", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["driver-profile"] }),
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/bookings/${id}/complete`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["driver-bookings"] });
      queryClient.invalidateQueries({ queryKey: ["driver-trips"] });
      queryClient.invalidateQueries({ queryKey: ["driver-wallet"] });
    },
  });

  const noShowMutation = useMutation({
    mutationFn: (id: string) => api.post(`/bookings/${id}/no-show`),
    onSuccess: () => {
      setNoShowConfirmId(null);
      queryClient.invalidateQueries({ queryKey: ["driver-bookings"] });
      queryClient.invalidateQueries({ queryKey: ["driver-trips"] });
    },
  });

  const republishMutation = useMutation({
    mutationFn: ({ id, date }: { id: string; date: string }) =>
      api.post(`/trips/${id}/duplicate`, { departure_date: date }),
    onSuccess: () => {
      setRepublishId(null);
      queryClient.invalidateQueries({ queryKey: ["driver-trips"] });
    },
    onError: (err: any) => setRepublishError(extractError(err)),
  });

  function openRepublish(id: string) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setRepublishDate(tomorrow.toISOString().slice(0, 10));
    setRepublishError("");
    setRepublishId(id);
  }

  const topupPayMutation = useMutation({
    mutationFn: (body: { amount: number; method: string }) =>
      api.post<{ payment_url: string }>("/drivers/me/wallet/topup/pay", body),
    onSuccess: (res) => {
      window.open(res.data.payment_url, "_blank", "noopener,noreferrer");
      setTopupDone(true);
    },
    onError: (err: any) => {
      setTopupError(extractError(err));
    },
  });

  const withdrawMutation = useMutation({
    mutationFn: (body: { amount: number; card_number: string }) =>
      api.post("/drivers/me/wallet/withdraw", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["driver-wallet"] });
      setWithdrawDone(true);
      setWithdrawAmount("");
      setCardNumber("");
    },
    onError: (err: any) => {
      setWithdrawError(extractError(err));
    },
  });

  function handleWithdraw() {
    setWithdrawError("");
    if (!wallet) { setWithdrawError("Balans ma'lumoti yuklanmadi. Sahifani yangilang"); return; }
    const amt = parseInt(withdrawAmount.replace(/\D/g, ""), 10);
    const card = cardNumber.replace(/\s/g, "");
    if (!amt || amt < 10_000) { setWithdrawError("Minimal yechish: 10,000 so'm"); return; }
    if (amt > wallet.balance) { setWithdrawError(`Balansdan ortiq: mavjud ${formatPrice(wallet.balance)} so'm`); return; }
    if (card.length !== 16) { setWithdrawError("Karta raqami 16 ta raqam bo'lishi kerak"); return; }
    withdrawMutation.mutate({ amount: amt, card_number: card });
  }

  function openTopup() {
    setTopupDone(false);
    setTopupError("");
    setTopupAmount("");
    setTopupOpen(true);
  }

  function openWithdraw() {
    setWithdrawDone(false);
    setWithdrawError("");
    setWithdrawAmount("");
    setCardNumber("");
    setWithdrawOpen(true);
  }

  if (authLoading || !user?.is_driver) return null;

  // ─── Hisob-kitob ─────────────────────────────────────────────────────────
  const todayStr = new Date().toISOString().slice(0, 10);
  const now = new Date();

  const pendingBkgs   = bookings.filter(b => b.status === "pending");
  const completedBkgs = bookings.filter(b => b.status === "completed");

  // Safarlar guruhlari
  const upcomingTrips  = trips.filter(t => (t.status === "active" || t.status === "full") && t.departure_date >= todayStr);
  const pastTrips      = trips.filter(t => t.status === "expired" || ((t.status === "active" || t.status === "full") && t.departure_date < todayStr));
  const cancelledTrips = trips.filter(t => t.status === "cancelled");
  const hasMoreTrips   = pastTrips.length > 0 || cancelledTrips.length > 0;

  const todayTrips = upcomingTrips.filter(t => t.departure_date === todayStr);

  // Lifetime statistika
  const totalTrips      = reviewData?.total_trips ?? profile?.total_trips ?? 0;
  const totalEarnings   = completedBkgs.reduce((s, b) => s + b.driver_amount, 0);
  const ratingAvg       = reviewData?.rating_avg ?? profile?.rating_avg ?? 0;
  const ratingCount     = reviewData?.rating_count ?? profile?.rating_count ?? 0;
  const visibleReviews  = (reviewData?.reviews ?? []).slice(0, 3);
  const tripsThisMonth  = completedBkgs.filter(b => {
    const d = new Date(b.completed_at ?? b.created_at);
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  }).length;

  // Depozit (hamyon) holati
  const balance     = wallet?.balance ?? 0;
  const depositPct  = Math.max(0, Math.min(100, (balance / 100_000) * 100));
  const depositLow  = balance > 0 && balance < 20_000;

  function bookingsOfTrip(tripId: string) {
    return bookings.filter(b => b.trip_id === tripId);
  }
  function pendingCountOfTrip(tripId: string) {
    return bookings.filter(b => b.trip_id === tripId && b.status === "pending").length;
  }

  // Bitta safar qatori — bosilganda yo'lovchilar/amallar ochiladi
  const renderTrip = (trip: TripResponse) => {
    const booked = trip.total_seats - trip.available_seats;
    const pCount = pendingCountOfTrip(trip.id);
    const tripBookings = bookingsOfTrip(trip.id).filter(b => b.status !== "cancelled");
    const isOpen = expandedTrip === trip.id;
    const isExpired = trip.status === "expired";
    const isCancelled = trip.status === "cancelled";
    const seatsLeft = trip.available_seats;
    const isPast = isExpired || trip.departure_date < todayStr;
    return (
      <div key={trip.id} className="border border-gray-100 rounded-xl overflow-hidden">
        <button
          onClick={() => setExpandedTrip(isOpen ? null : trip.id)}
          className="w-full flex items-center gap-3 p-3 text-left hover:bg-gray-50/60 transition-colors"
        >
          <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center shrink-0", isPast || isCancelled ? "bg-gray-100" : "bg-primary-50")}>
            <Car size={16} className={isPast || isCancelled ? "text-gray-400" : "text-primary-500"} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">
              {trip.from_region.name_uz} → {trip.to_region.name_uz}
            </p>
            <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
              <span>{formatDate(trip.departure_date)} · {trip.departure_time.slice(0, 5)}</span>
              {!isCancelled && (
                <span className={clsx(
                  "px-1.5 py-0.5 rounded-full font-medium",
                  booked === 0 ? "bg-gray-100 text-gray-500" :
                  seatsLeft === 0 ? "bg-orange-100 text-orange-600" : "bg-blue-100 text-blue-600"
                )}>
                  {booked}/{trip.total_seats} band
                </span>
              )}
            </div>
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-bold text-gray-900 tabular-nums">{formatPrice(trip.price_per_seat)}</p>
            <p className="text-[11px] text-gray-400">
              {isCancelled ? "bekor" : isExpired ? "tugadi" : seatsLeft === 0 ? "To'ldi" : `${seatsLeft} o'rin qoldi`}
            </p>
          </div>
          {pCount > 0 && (
            <span className="text-[10px] font-semibold text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded-full shrink-0">{pCount} yangi</span>
          )}
          <ChevronDown size={16} className={clsx("text-gray-300 transition-transform shrink-0", isOpen && "rotate-180")} />
        </button>

        {isOpen && (
          <div className="border-t border-gray-50 px-3 py-3 space-y-2.5 bg-gray-50/30">
            {tripBookings.length === 0 ? (
              <p className="text-xs text-gray-400 py-1 text-center">Hali yo'lovchi yo'q</p>
            ) : (
              tripBookings.map((bkg) => {
                const st = BSTATUS[bkg.status] ?? BSTATUS.confirmed;
                return (
                  <div key={bkg.id} className="flex items-center gap-2.5">
                    <Avatar src={bkg.passenger.profile_photo} name={bkg.passenger.full_name} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-medium text-gray-900 truncate">{bkg.passenger.full_name}</span>
                        <span className={clsx("text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0", st.cls)}>{st.label}</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{bkg.seats_count} o'rin · {formatPrice(bkg.total_price)} so'm</p>
                    </div>
                    <div className="flex gap-1.5 shrink-0">
                      {bkg.passenger.phone && (bkg.status === "confirmed" || bkg.status === "completed") && (
                        <a href={`tel:${bkg.passenger.phone}`} title="Qo'ng'iroq">
                          <span className="w-8 h-8 rounded-lg bg-white border border-gray-100 hover:bg-gray-50 flex items-center justify-center text-gray-500 transition-colors"><Phone size={14} /></span>
                        </a>
                      )}
                      {bkg.status === "confirmed" && (
                        <Link href={`/messages/${bkg.id}`} title="Chat">
                          <span className="w-8 h-8 rounded-lg bg-white border border-gray-100 hover:bg-gray-50 flex items-center justify-center text-gray-500 transition-colors"><MessageCircle size={14} /></span>
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {tripBookings.filter(b => b.status === "confirmed" || b.status === "pending" || b.status === "awaiting_confirmation").map(b => (
              <div key={`act-${b.id}`} className="flex items-center justify-between gap-2 bg-white rounded-lg px-2.5 py-2 border border-gray-100">
                <span className="text-xs text-gray-600 truncate">
                  {b.passenger.full_name} — {b.status === "awaiting_confirmation" ? "safar bo'ldimi?" : "yakunlash"}
                </span>
                <div className="flex gap-1.5 shrink-0">
                  <Button size="sm" variant="outline" className="text-xs px-2.5 border-red-200 text-red-500 hover:bg-red-50"
                    onClick={() => setNoShowConfirmId(b.id)}>Kelmadi</Button>
                  <Button size="sm" className="text-xs px-2.5"
                    onClick={() => completeMutation.mutate(b.id)} loading={completeMutation.isPending}>Tugatish</Button>
                </div>
              </div>
            ))}

            <div className="flex items-center justify-between pt-1.5 border-t border-gray-100">
              <Link href={`/trips/${trip.id}`} className="text-xs text-primary-600 hover:underline flex items-center gap-0.5">
                Safar sahifasi <ChevronRight size={12} />
              </Link>
              {isPast && !isCancelled && (
                <Button size="sm" variant="outline" className="text-xs px-3 gap-1.5" onClick={() => openRepublish(trip.id)}>
                  <RefreshCw size={13} />Qayta e'lon
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const firstName = user.full_name.split(" ")[0];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-5">

      {/* ── Sarlavha ─────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <Avatar src={user.profile_photo} name={user.full_name} size="lg" />
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-gray-900 truncate">{user.full_name}</h1>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1 text-xs text-gray-500">
              {ratingCount > 0 && (
                <span className="flex items-center gap-1 font-medium text-gray-700">
                  <Star size={11} className="fill-yellow-400 text-yellow-400" />
                  {ratingAvg.toFixed(1)}
                </span>
              )}
              {profile?.status === "approved" && (
                <span className="flex items-center gap-1 text-green-600 bg-green-50 px-2 py-0.5 rounded-full font-medium">
                  <ShieldCheck size={11} />
                  Tasdiqlangan
                </span>
              )}
              {profile && (
                <span className="text-gray-400">·</span>
              )}
              {profile && (
                <span className="text-gray-500">
                  {profile.vehicle_make} {profile.vehicle_model} · {profile.vehicle_plate}
                </span>
              )}
            </div>
          </div>
        </div>
        <Link href="/create-trip" className="shrink-0">
          <Button className="gap-1.5 w-full sm:w-auto">
            <Plus size={15} />
            Safar e'lon qilish
          </Button>
        </Link>
      </div>

      {/* ── 4 statistika ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs text-gray-400 mb-1">Jami safarlar</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">{totalTrips}</p>
          {tripsThisMonth > 0 && <p className="text-xs text-green-600 mt-1.5">+{tripsThisMonth} bu oy</p>}
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs text-gray-400 mb-1">Jami daromad</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">{formatShort(totalEarnings)}</p>
          <p className="text-xs text-gray-400 mt-1.5">so'm</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs text-gray-400 mb-1">Reyting</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">
            {ratingCount > 0 ? ratingAvg.toFixed(1) : "—"}
          </p>
          <p className="text-xs text-gray-400 mt-1.5">{ratingCount} ta baho</p>
        </div>
        <div className={clsx(
          "rounded-2xl border p-4",
          wallet?.is_blocked ? "bg-red-50 border-red-200" :
          balance < 0 ? "bg-orange-50 border-orange-200" : "bg-white border-gray-100"
        )}>
          <p className="text-xs text-gray-400 mb-1">Depozit</p>
          <p className={clsx(
            "text-2xl font-bold tabular-nums leading-none",
            balance < 0 ? "text-red-600" : "text-gray-900"
          )}>
            {wallet ? formatShort(balance) : "—"}
          </p>
          <p className="text-xs text-gray-400 mt-1.5">so'm qoldi</p>
        </div>
      </div>

      {/* ── Bugungi safar eslatmasi ──────────────────────────────────────── */}
      {todayTrips.length > 0 && (
        <div className="bg-primary-50 border border-primary-200 rounded-2xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center shrink-0">
            <Clock size={18} className="text-primary-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-primary-900">Bugun safaringiz bor 🚗</p>
            <p className="text-xs text-primary-600 mt-0.5 truncate">
              {todayTrips.map(t => `${t.from_region.name_uz} → ${t.to_region.name_uz} (${t.departure_time.slice(0,5)})`).join(" · ")}
            </p>
          </div>
        </div>
      )}

      {/* ── Hamyon bloklangan ogohlantirish ──────────────────────────────── */}
      {wallet?.is_blocked && (
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-4 flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-bold text-red-800 text-sm">Depozit tugadi — yangi naqd bronlar qabul qilinmaydi</p>
            <p className="text-sm text-red-600 mt-1">
              Balans {formatPrice(wallet.min_balance)} so'mdan past. Depozitni to'ldiring.
            </p>
            <Button size="sm" className="mt-3 bg-red-500 hover:bg-red-600" onClick={openTopup}>
              Depozit to'ldirish
            </Button>
          </div>
        </div>
      )}

      {/* ── 2 ustunli grid ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">

        {/* ══ CHAP USTUN ══ */}
        <div className="space-y-5">

          {/* Kelgusi safarlar */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900">Kelgusi safarlar</h2>
              <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                {upcomingTrips.length} ta
              </span>
            </div>

            {tripsLoading ? (
              <div className="space-y-2">
                {[1, 2].map(i => <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />)}
              </div>
            ) : upcomingTrips.length === 0 && !showAllTrips ? (
              <div className="py-10 text-center">
                <Car size={32} className="text-gray-200 mx-auto mb-3" />
                <p className="text-gray-500 text-sm mb-4">Kelgusi safarlar yo'q</p>
                <Link href="/create-trip">
                  <Button size="sm"><Plus size={14} />Safar qo'shish</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {upcomingTrips.map(renderTrip)}
                {showAllTrips && pastTrips.length > 0 && (
                  <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide pt-2">O'tgan safarlar</p>
                )}
                {showAllTrips && pastTrips.map(renderTrip)}
                {showAllTrips && cancelledTrips.length > 0 && (
                  <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide pt-2">Bekor qilingan</p>
                )}
                {showAllTrips && cancelledTrips.map(renderTrip)}
              </div>
            )}

            {hasMoreTrips && (
              <button
                onClick={() => { setShowAllTrips(v => !v); setExpandedTrip(null); }}
                className="w-full mt-3 py-2.5 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors flex items-center justify-center gap-1.5"
              >
                {showAllTrips ? "Kamroq ko'rsatish" : "Barcha safarlar"}
                <ChevronDown size={14} className={clsx("transition-transform", showAllTrips && "rotate-180")} />
              </button>
            )}
          </div>

          {/* Depozit holati */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 flex items-center gap-2">
                <Wallet size={16} className="text-gray-400" />
                Depozit holati
              </h2>
              <span className={clsx(
                "text-sm font-bold tabular-nums",
                balance < 0 ? "text-red-600" : depositLow ? "text-orange-500" : "text-gray-900"
              )}>
                {wallet ? formatPrice(balance) : "—"} so'm
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-2">
              <div
                className={clsx(
                  "h-full rounded-full transition-all",
                  balance < 0 ? "bg-red-400" : depositLow ? "bg-orange-400" : "bg-green-500"
                )}
                style={{ width: `${depositPct}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-gray-400 mb-4">
              <span>0</span>
              <span>100 000 so'm</span>
            </div>

            <p className="text-xs text-gray-500 leading-relaxed mb-4">
              Naqd safarlar komissiyasi shu depozitdan chegariladi.
              {balance < 0
                ? ` Balans manfiy — ${formatPrice(wallet?.min_balance ?? -50000)} so'mga yetganda naqd bronlar bloklanadi.`
                : depositLow
                ? " Depozit kam qoldi — to'ldirib qo'ying."
                : " 20 000 so'mdan past tushsa — ogohlantirish beriladi."}
            </p>

            <div className="flex gap-2">
              <Button size="sm" className="flex-1 gap-1.5" onClick={openTopup}>
                <ArrowUpRight size={14} />
                Depozit to'ldirish
              </Button>
              <Button size="sm" variant="outline" className="flex-1 gap-1.5" onClick={() => setShowTx(v => !v)}>
                <History size={14} />
                Tarix
              </Button>
            </div>

            {/* Tranzaksiyalar tarixi (Tarix tugmasi) */}
            {showTx && wallet && (
              <div className="mt-4 border-t border-gray-50 pt-3 space-y-2">
                {wallet.transactions.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-2">Hali operatsiya yo'q</p>
                ) : (
                  wallet.transactions.slice(0, 6).map(tx => (
                    <div key={tx.id} className="flex items-center gap-2.5">
                      <TxIcon type={tx.tx_type} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{TX_LABELS[tx.tx_type] ?? tx.tx_type}</p>
                        <p className="text-[11px] text-gray-400 truncate">{tx.description}</p>
                      </div>
                      <p className={clsx("text-xs font-bold tabular-nums shrink-0", tx.amount > 0 ? "text-green-600" : "text-red-500")}>
                        {tx.amount > 0 ? "+" : ""}{formatPrice(tx.amount)}
                      </p>
                    </div>
                  ))
                )}
                <button onClick={openWithdraw} className="text-xs text-primary-600 hover:underline mt-1">
                  Pul yechib olish →
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ══ O'NG USTUN ══ */}
        <div className="space-y-5">

          {/* So'nggi baholar */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900">So'nggi baholar</h2>
              {ratingCount > 0 && <span className="text-xs text-gray-400">{ratingAvg.toFixed(1)} o'rtacha</span>}
            </div>

            {ratingCount === 0 ? (
              <div className="py-8 text-center">
                <Star size={28} className="text-gray-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">Hali baho yo'q</p>
              </div>
            ) : (
              <div className="space-y-3">
                {visibleReviews.map(r => (
                  <div key={r.id} className="flex items-start gap-2.5">
                    <Avatar src={r.reviewer.profile_photo} name={r.reviewer.full_name} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-gray-800 truncate">{r.reviewer.full_name}</span>
                        <span className="flex items-center gap-0.5 text-xs text-yellow-500 shrink-0">
                          {Array.from({ length: r.rating }).map((_, i) => (
                            <Star key={i} size={11} className="fill-yellow-400 text-yellow-400" />
                          ))}
                        </span>
                      </div>
                      {r.comment && <p className="text-xs text-gray-500 leading-snug mt-0.5">{r.comment}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sozlamalar */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <h2 className="font-bold text-gray-900 mb-4">Sozlamalar</h2>
            <div className="space-y-1">
              {[
                {
                  label: "Safarlarim ko'rinsin",
                  desc: "Yo'lovchilar ko'ra oladi",
                  checked: profile ? !profile.is_on_pause : true,
                  onChange: () => profile && pauseMutation.mutate(!profile.is_on_pause),
                },
                {
                  label: "Yuk olish",
                  desc: "Bagaj uchun joy bor",
                  checked: profile ? profile.luggage_size !== "small" : false,
                  onChange: () => profile && prefMutation.mutate({ luggage_size: profile.luggage_size === "small" ? "medium" : "small" }),
                },
                {
                  label: "Hayvon bilan",
                  desc: "Uy hayvonlariga ruxsat",
                  checked: profile?.pets_allowed ?? false,
                  onChange: () => profile && prefMutation.mutate({ pets_allowed: !profile.pets_allowed }),
                },
                {
                  label: "Faqat ayollar uchun",
                  desc: "Ayol yo'lovchilar",
                  checked: profile?.women_only ?? false,
                  onChange: () => profile && prefMutation.mutate({ women_only: !profile.women_only }),
                },
              ].map(({ label, desc, checked, onChange }) => (
                <div key={label} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800">{label}</p>
                    <p className="text-xs text-gray-400">{desc}</p>
                  </div>
                  <Toggle checked={checked} onChange={onChange} disabled={!profile || pauseMutation.isPending || prefMutation.isPending} />
                </div>
              ))}
            </div>
            {profile?.is_on_pause && (
              <p className="text-xs text-orange-600 bg-orange-50 rounded-lg px-3 py-2 mt-2">
                Siz pauzadasiz — safarlaringiz qidiruvda ko'rinmaydi.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* ── "Kelmadi" ogohlantirish modali ────────────────────────────────── */}
      {noShowConfirmId && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setNoShowConfirmId(null)} />
          <div className="relative bg-white w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-6 shadow-xl">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-11 h-11 bg-red-50 rounded-2xl flex items-center justify-center shrink-0">
                <AlertTriangle size={22} className="text-red-500" />
              </div>
              <div className="min-w-0">
                <h2 className="text-base font-bold text-gray-900">Safar bo'lmadi deb belgilaysizmi?</h2>
                <p className="text-sm text-gray-500 mt-0.5">Bu jiddiy harakat — diqqat bilan o'qing.</p>
              </div>
            </div>
            <div className="bg-red-50 border border-red-100 rounded-xl p-3 text-sm text-red-700 leading-relaxed mb-5">
              Agar yo'lovchi safar <b>bo'lganini</b> tasdiqlasa, bu <b>soxta belgilash</b> hisoblanadi:
              komissiya baribir hisoblanadi va hisobingizga jarima qayd etiladi.
              <b> 3 marta</b> takrorlansa — e'lonlaringiz vaqtincha qidiruvda ko'rinmaydi.
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setNoShowConfirmId(null)}>
                Bekor
              </Button>
              <Button
                className="flex-1 bg-red-500 hover:bg-red-600"
                loading={noShowMutation.isPending}
                onClick={() => noShowMutation.mutate(noShowConfirmId)}
              >
                Ha, safar bo'lmadi
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Qayta e'lon qilish modali ─────────────────────────────────────── */}
      {republishId && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setRepublishId(null)} />
          <div className="relative bg-white w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <RefreshCw size={18} className="text-primary-500" />
                Safarni qayta e'lon qilish
              </h2>
              <button
                onClick={() => setRepublishId(null)}
                className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
              >
                <X size={16} className="text-gray-500" />
              </button>
            </div>
            <div className="space-y-4">
              <p className="text-sm text-gray-500">
                Eski safar ma'lumotlari (yo'nalish, narx, o'rinlar) saqlanadi. Faqat yangi sanani tanlang.
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Yangi sana</label>
                <input
                  type="date"
                  value={republishDate}
                  min={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => { setRepublishDate(e.target.value); setRepublishError(""); }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>
              {republishError && (
                <p className="text-sm text-red-500 bg-red-50 rounded-xl px-3 py-2">{republishError}</p>
              )}
              <Button
                fullWidth
                size="lg"
                loading={republishMutation.isPending}
                onClick={() => {
                  if (!republishDate) { setRepublishError("Sanani tanlang"); return; }
                  republishMutation.mutate({ id: republishId, date: republishDate });
                }}
              >
                Qayta e'lon qilish
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Depozit to'ldirish modali ─────────────────────────────────────── */}
      {topupOpen && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setTopupOpen(false)} />
          <div className="relative bg-white w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-6 shadow-xl">

            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <ArrowUpRight size={18} className="text-green-500" />
                Depozitni to'ldirish
              </h2>
              <button
                onClick={() => setTopupOpen(false)}
                className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
              >
                <X size={16} className="text-gray-500" />
              </button>
            </div>

            {topupDone ? (
              <div className="flex flex-col items-center text-center py-4 gap-3">
                <div className="w-14 h-14 bg-green-50 rounded-2xl flex items-center justify-center">
                  <ArrowUpRight size={28} className="text-green-500" />
                </div>
                <p className="font-bold text-gray-900">To'lov sahifasi ochildi</p>
                <p className="text-sm text-gray-500 leading-relaxed">
                  To'lovni yakunlang. Muvaffaqiyatli to'lovdan so'ng depozitingiz avtomatik to'ldiriladi.
                </p>
                <Button
                  fullWidth
                  variant="outline"
                  onClick={() => {
                    queryClient.invalidateQueries({ queryKey: ["driver-wallet"] });
                    setTopupOpen(false);
                  }}
                  className="mt-2"
                >
                  Yopish
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-xl px-4 py-3 flex items-center justify-between">
                  <span className="text-sm text-gray-500">Hozirgi balans</span>
                  {walletLoading ? (
                    <span className="text-sm text-gray-400">Yuklanmoqda...</span>
                  ) : (
                    <span className={`text-sm font-bold ${wallet && wallet.balance < 0 ? "text-red-500" : "text-gray-900"}`}>
                      {wallet ? formatPrice(wallet.balance) : "—"} so'm
                    </span>
                  )}
                </div>

                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Miqdor (so'm)</p>
                  <div className="grid grid-cols-3 gap-2 mb-2">
                    {[50_000, 100_000, 200_000].map((preset) => (
                      <button
                        key={preset}
                        onClick={() => { setTopupAmount(preset.toLocaleString("uz-UZ")); setTopupError(""); }}
                        className={`py-2 rounded-xl text-sm font-semibold border-2 transition-all ${
                          topupAmount === preset.toLocaleString("uz-UZ")
                            ? "border-green-500 bg-green-50 text-green-700"
                            : "border-gray-100 text-gray-600 hover:border-gray-200"
                        }`}
                      >
                        {(preset / 1000).toFixed(0)}K
                      </button>
                    ))}
                  </div>
                  <Input
                    placeholder="Boshqa miqdor..."
                    value={topupAmount}
                    inputMode="numeric"
                    onChange={(e) => {
                      const raw = e.target.value.replace(/\D/g, "");
                      setTopupAmount(raw ? parseInt(raw).toLocaleString("uz-UZ") : "");
                      setTopupError("");
                    }}
                  />
                </div>

                {topupError && (
                  <p className="text-sm text-red-500 bg-red-50 rounded-xl px-3 py-2">{topupError}</p>
                )}

                <div className="space-y-2">
                  {[
                    { method: "click", label: "Click orqali to'lash", color: "bg-[#00CFFF] hover:bg-[#00b8e6] text-white" },
                    { method: "payme", label: "Payme orqali to'lash", color: "bg-[#1AC8A8] hover:bg-[#17b296] text-white" },
                  ].map(({ method, label, color }) => (
                    <button
                      key={method}
                      disabled={topupPayMutation.isPending}
                      onClick={() => {
                        const amt = parseInt(topupAmount.replace(/\D/g, ""), 10);
                        if (!amt || amt < 10_000) { setTopupError("Minimal miqdor: 10,000 so'm"); return; }
                        setTopupError("");
                        topupPayMutation.mutate({ amount: amt, method });
                      }}
                      className={`w-full py-3.5 rounded-xl font-semibold text-sm transition-all disabled:opacity-60 ${color}`}
                    >
                      {topupPayMutation.isPending ? "Yuklanmoqda..." : label}
                    </button>
                  ))}
                </div>

                <p className="text-xs text-gray-400 text-center">To'lovdan so'ng depozit avtomatik yangilanadi</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Pul yechish modali ────────────────────────────────────────────── */}
      {withdrawOpen && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setWithdrawOpen(false)} />
          <div className="relative bg-white w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <CreditCard size={18} className="text-primary-500" />
                Pul yechib olish
              </h2>
              <button
                onClick={() => setWithdrawOpen(false)}
                className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
              >
                <X size={16} className="text-gray-500" />
              </button>
            </div>

            {withdrawDone ? (
              <div className="flex flex-col items-center text-center py-6 gap-3">
                <div className="w-14 h-14 bg-green-50 rounded-2xl flex items-center justify-center">
                  <ArrowDownLeft size={26} className="text-green-500" />
                </div>
                <p className="font-bold text-gray-900">So'rov yuborildi!</p>
                <p className="text-sm text-gray-500 leading-relaxed">
                  Pul 1–3 ish kuni ichida kartangizga o'tkaziladi. Savollar bo'lsa admin bilan bog'laning.
                </p>
                <Button fullWidth onClick={() => setWithdrawOpen(false)} className="mt-2">Yaxshi</Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-xl px-4 py-3 flex items-center justify-between">
                  <span className="text-sm text-gray-500">Mavjud balans</span>
                  {walletLoading ? (
                    <span className="text-sm text-gray-400">Yuklanmoqda...</span>
                  ) : walletError ? (
                    <span className="text-sm text-red-400">Yuklanmadi</span>
                  ) : (
                    <span className={`text-sm font-bold ${wallet && wallet.balance <= 0 ? "text-red-500" : "text-gray-900"}`}>
                      {wallet ? formatPrice(wallet.balance) : "—"} so'm
                    </span>
                  )}
                </div>

                <Input
                  label="Yechish miqdori (so'm)"
                  placeholder="Masalan: 100 000"
                  value={withdrawAmount}
                  inputMode="numeric"
                  onChange={(e) => {
                    const raw = e.target.value.replace(/\D/g, "");
                    setWithdrawAmount(raw ? parseInt(raw).toLocaleString("uz-UZ") : "");
                    setWithdrawError("");
                  }}
                />

                <Input
                  label="Karta raqami"
                  placeholder="8600 0000 0000 0000"
                  value={cardNumber}
                  inputMode="numeric"
                  maxLength={19}
                  prefix={<CreditCard size={15} />}
                  onChange={(e) => {
                    setCardNumber(formatCard(e.target.value));
                    setWithdrawError("");
                  }}
                />

                {withdrawError && (
                  <p className="text-sm text-red-500 bg-red-50 rounded-xl px-3 py-2">{withdrawError}</p>
                )}

                <p className="text-xs text-gray-400 leading-relaxed">
                  So'rov 1–3 ish kuni ichida ko'rib chiqiladi. Minimal miqdor: 10,000 so'm.
                </p>

                <Button
                  fullWidth
                  size="lg"
                  onClick={handleWithdraw}
                  loading={withdrawMutation.isPending}
                  disabled={wallet?.is_blocked || walletLoading || walletError}
                >
                  {wallet?.is_blocked ? "Hamyon bloklangan" :
                   walletLoading ? "Yuklanmoqda..." :
                   walletError ? "Balans yuklanmadi" : "Yuborish"}
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
