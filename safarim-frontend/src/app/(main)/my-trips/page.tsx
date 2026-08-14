"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Clock, CheckCircle, XCircle, AlertCircle, Star, Car,
  Phone, MessageCircle, User as UserIcon, Mail, MapPin,
  CreditCard, ArrowUpRight, RotateCcw, ShieldCheck,
} from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import SearchBar from "@/components/trips/SearchBar";
import { BookingCardSkeleton } from "@/components/ui/Skeleton";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import type { BookingResponse, BookingStatus, ReviewResponse } from "@/types";
import { clsx } from "clsx";


const STATUS_CONFIG: Record<BookingStatus, { label: string; cls: string }> = {
  confirmed:             { label: "Tasdiqlangan",     cls: "bg-green-100 text-green-700" },
  pending:               { label: "Kutilmoqda",       cls: "bg-yellow-100 text-yellow-700" },
  awaiting_confirmation: { label: "Tasdiq kutilmoqda", cls: "bg-amber-100 text-amber-700" },
  disputed:              { label: "Nizo",             cls: "bg-purple-100 text-purple-700" },
  completed:             { label: "Tugadi",           cls: "bg-gray-100 text-gray-600" },
  cancelled:             { label: "Bekor qilingan",   cls: "bg-red-100 text-red-600" },
  no_show:               { label: "Kelmadi",          cls: "bg-red-100 text-red-600" },
};

function formatPrice(n: number) {
  return new Intl.NumberFormat("uz-UZ").format(n);
}
function formatShort(n: number) {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (abs >= 1_000) return Math.round(n / 1_000) + "K";
  return String(n);
}
function fmtTime(t?: string) {
  return t?.slice(0, 5) ?? "";
}
function fmtDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("uz-UZ", { day: "numeric", month: "short" });
}
const METHOD_LABEL: Record<string, string> = { cash: "Naqd", click: "Click", payme: "Payme" };

export default function MyTripsPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [cancelModal, setCancelModal] = useState<string | null>(null);
  const [reviewModal, setReviewModal] = useState<string | null>(null);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewText, setReviewText] = useState("");
  const [cancelError, setCancelError] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [showAllPast, setShowAllPast] = useState(false);

  const { data: bookings = [], isLoading } = useQuery<BookingResponse[]>({
    queryKey: ["my-bookings"],
    queryFn: async () => (await api.get("/bookings/my")).data,
  });

  const { data: myReviews = [] } = useQuery<ReviewResponse[]>({
    queryKey: ["my-reviews"],
    queryFn: async () => (await api.get("/reviews/my")).data,
  });

  const cancelMutation = useMutation({
    mutationFn: async (id: string) => { await api.post(`/bookings/${id}/cancel`); },
    onSuccess: () => { setCancelModal(null); qc.invalidateQueries({ queryKey: ["my-bookings"] }); },
    onError: (err: any) => setCancelError(getApiError(err)),
  });

  const confirmMutation = useMutation({
    mutationFn: async ({ id, confirmed }: { id: string; confirmed: boolean }) => {
      await api.post(`/bookings/${id}/confirm`, { confirmed });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-bookings"] }),
  });

  const reviewMutation = useMutation({
    mutationFn: async ({ id, rating, comment }: { id: string; rating: number; comment: string }) => {
      await api.post(`/reviews/${id}`, { rating, comment: comment || null });
    },
    onSuccess: () => {
      setReviewModal(null); setReviewText(""); setReviewRating(5);
      qc.invalidateQueries({ queryKey: ["my-bookings"] });
      qc.invalidateQueries({ queryKey: ["my-reviews"] });
    },
    onError: (err: any) => setReviewError(getApiError(err)),
  });

  // ─── Hisob-kitob ─────────────────────────────────────────────────────────
  const thisYear = new Date().getFullYear();
  const active = bookings.filter(b => b.status === "confirmed" || b.status === "pending");
  const completed = bookings.filter(b => b.status === "completed");
  // Safar o'tdi — yo'lovchidan tasdiq kutilmoqda
  const needConfirm = bookings.filter(b => b.needs_my_confirmation);

  const reviewedIds = new Set(myReviews.map(r => r.booking_id));

  const jamiSafarlar = completed.filter(b => new Date(b.completed_at ?? b.created_at).getFullYear() === thisYear).length;
  const jamiTolov = completed.reduce((s, b) => s + b.total_price, 0);

  // Sevimli yo'nalish
  const routeCounts: Record<string, number> = {};
  bookings.forEach(b => {
    if (b.trip) {
      const key = `${b.trip.from_region.name_uz}–${b.trip.to_region.name_uz}`;
      routeCounts[key] = (routeCounts[key] ?? 0) + 1;
    }
  });
  const favRoute = Object.entries(routeCounts).sort((a, b) => b[1] - a[1])[0];

  // To'lovlar tarixi (bekor qilinganlar qaytarma sifatida)
  const payments = bookings
    .filter(b => b.status !== "pending")
    .map(b => {
      const refunded = (b.status === "cancelled" || b.status === "no_show") && (b.refund_amount ?? 0) > 0;
      return {
        id: b.id,
        route: b.trip ? `${b.trip.from_region.name_uz} → ${b.trip.to_region.name_uz}` : "Safar",
        date: b.cancelled_at ?? b.completed_at ?? b.created_at,
        method: METHOD_LABEL[b.payment_method] ?? b.payment_method,
        amount: refunded ? (b.refund_amount ?? 0) : -b.total_price,
        refunded,
      };
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const reviewById = (bookingId: string) => myReviews.find(r => r.booking_id === bookingId);

  // Bitta buyurtma kartasi (faol va o'tgan safarlar uchun bir xil)
  const renderBookingCard = (b: BookingResponse) => {
    const st = STATUS_CONFIG[b.status];
    const driver = b.trip?.driver;
    const isCompleted = b.status === "completed";
    const reviewed = reviewedIds.has(b.id);
    const rev = reviewById(b.id);
    const canCall = !!b.driver_phone && (b.status === "confirmed" || b.status === "completed");
    const canChat = b.status === "confirmed" || b.status === "pending";
    const canCancel = b.status === "confirmed" || b.status === "pending";
    return (
      <div key={b.id} className="border border-gray-100 rounded-2xl p-4">
        {/* Haydovchi + holat */}
        <div className="flex items-center gap-3 mb-3">
          <Avatar src={driver?.profile_photo ?? null} name={driver?.full_name ?? "Haydovchi"} size="md" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">{driver?.full_name ?? "Haydovchi"}</p>
            {driver && driver.rating_count > 0 ? (
              <span className="flex items-center gap-1 mt-0.5 text-xs">
                <Star size={11} className="fill-yellow-400 text-yellow-400" />
                <span className="font-medium text-gray-700">{driver.rating_avg.toFixed(1)}</span>
                <span className="text-gray-400">({driver.rating_count})</span>
              </span>
            ) : (
              <p className="text-xs text-gray-400 mt-0.5">Yangi haydovchi</p>
            )}
          </div>
          <span className={clsx("text-[11px] font-semibold px-2.5 py-1 rounded-full shrink-0", st.cls)}>{st.label}</span>
        </div>

        {/* Marshrut (vertikal) */}
        <div className="flex gap-3">
          <div className="flex flex-col items-center pt-1.5 shrink-0">
            <span className="w-2.5 h-2.5 rounded-full border-2 border-primary-500 bg-white" />
            <span className="w-0.5 flex-1 min-h-[20px] bg-gray-200 my-1" />
            <span className="w-2.5 h-2.5 rounded-full bg-primary-500" />
          </div>
          <div className="flex-1 min-w-0 flex flex-col gap-2.5">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[15px] font-bold text-gray-900 truncate">{b.trip?.from_region.name_uz ?? "—"}</p>
              <p className="text-xs font-semibold text-gray-500 shrink-0">{fmtTime(b.trip?.departure_time)}</p>
            </div>
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[15px] font-bold text-gray-900 truncate">{b.trip?.to_region.name_uz ?? "—"}</p>
              <p className="text-xs text-gray-400 shrink-0">{fmtDate(b.trip?.departure_date)}</p>
            </div>
          </div>
        </div>

        {/* Narx + amallar */}
        <div className="flex items-center justify-between gap-3 mt-4 pt-3 border-t border-gray-50">
          <p className="text-base font-extrabold text-accent-700 tabular-nums leading-none">
            {formatPrice(b.total_price)} <span className="text-xs font-semibold text-gray-400">so'm</span>
          </p>
          <div className="flex gap-2">
            {canChat && (
              <Link href={`/messages/${b.id}`} title="Chat" className="w-9 h-9 rounded-xl bg-primary-50 hover:bg-primary-100 flex items-center justify-center text-primary-600 transition-colors">
                <MessageCircle size={16} />
              </Link>
            )}
            {canCall && (
              <a href={`tel:${b.driver_phone}`} title="Qo'ng'iroq" className="w-9 h-9 rounded-xl bg-green-50 hover:bg-green-100 flex items-center justify-center text-green-600 transition-colors">
                <Phone size={16} />
              </a>
            )}
            {canCancel && (
              <button onClick={() => { setCancelError(""); setCancelModal(b.id); }} title="Bekor qilish" className="w-9 h-9 rounded-xl bg-red-50 hover:bg-red-100 flex items-center justify-center text-red-500 transition-colors">
                <XCircle size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Baho — safar yakunlangач ochiladi */}
        {isCompleted && !reviewed && (
          <div className="mt-3 pt-3 border-t border-gray-50 text-center">
            <p className="text-xs font-semibold text-gray-600 mb-2.5">Safar qanday o'tdi? Haydovchiga baho bering</p>
            <Button size="sm" fullWidth className="gap-1.5" onClick={() => { setReviewError(""); setReviewRating(5); setReviewModal(b.id); }}>
              <Star size={14} />Baho berish
            </Button>
          </div>
        )}
        {isCompleted && reviewed && rev && (
          <div className="mt-3 pt-3 border-t border-gray-50 flex items-center justify-center gap-1.5 text-xs text-green-600">
            <CheckCircle size={14} />
            Siz baho berdingiz:
            <span className="flex">
              {Array.from({ length: rev.rating }).map((_, i) => <Star key={i} size={12} className="fill-yellow-400 text-yellow-400" />)}
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-5">

      {/* ── Sarlavha ─────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <Avatar src={user?.profile_photo ?? null} name={user?.full_name ?? "Foydalanuvchi"} size="lg" />
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-gray-900 truncate">{user?.full_name ?? "—"}</h1>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1 text-xs text-gray-500">
              {user?.is_phone_verified && (
                <span className="flex items-center gap-1 text-green-600 bg-green-50 px-2 py-0.5 rounded-full font-medium">
                  <ShieldCheck size={11} />
                  Telefon tasdiqlangan
                </span>
              )}
              <span className="text-gray-400">·</span>
              <span>{completed.length} ta safar</span>
              {!user?.is_blocked && (
                <span className="text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full font-medium">Faol</span>
              )}
            </div>
          </div>
        </div>
        <Link href="/trips" className="shrink-0">
          <Button variant="outline" className="gap-1.5 w-full sm:w-auto">Safar qidirish</Button>
        </Link>
      </div>

      {/* ── Safar tasdiqi (yo'lovchidan) ─────────────────────────────────── */}
      {needConfirm.map((b) => {
        const deniedByDriver = b.driver_confirmed === "no";
        return (
          <div
            key={`confirm-${b.id}`}
            className={clsx(
              "rounded-2xl border-2 p-4",
              deniedByDriver ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200"
            )}
          >
            <div className="flex items-start gap-3">
              <div className={clsx(
                "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
                deniedByDriver ? "bg-red-100" : "bg-amber-100"
              )}>
                <AlertCircle size={20} className={deniedByDriver ? "text-red-600" : "text-amber-600"} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-gray-900">
                  {deniedByDriver
                    ? "Haydovchi bu safar bo'lmadi dedi"
                    : "Safaringiz bo'ldimi?"}
                </p>
                <p className="text-xs text-gray-600 mt-0.5">
                  {b.trip ? `${b.trip.from_region.name_uz} → ${b.trip.to_region.name_uz}` : "Safar"}
                  {" · "}{fmtDate(b.trip?.departure_date)} {fmtTime(b.trip?.departure_time)}
                </p>
                {deniedByDriver && (
                  <p className="text-xs text-red-600 mt-1.5">
                    Agar safar bo'lgan bo'lsa, «Ha, bo'ldi» bosing — bu adolatni tiklaydi.
                  </p>
                )}
                <div className="flex gap-2 mt-3">
                  <Button
                    size="sm"
                    className="flex-1"
                    loading={confirmMutation.isPending && confirmMutation.variables?.id === b.id && confirmMutation.variables?.confirmed === true}
                    onClick={() => confirmMutation.mutate({ id: b.id, confirmed: true })}
                  >
                    Ha, bo'ldi
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 border-gray-300 text-gray-600"
                    loading={confirmMutation.isPending && confirmMutation.variables?.id === b.id && confirmMutation.variables?.confirmed === false}
                    onClick={() => confirmMutation.mutate({ id: b.id, confirmed: false })}
                  >
                    Yo'q, bo'lmadi
                  </Button>
                </div>
              </div>
            </div>
          </div>
        );
      })}

      {/* ── Tezkor qidiruv ───────────────────────────────────────────────── */}
      <SearchBar compact />

      {/* ── Faol safarlar (yangi/joriy buyurtmalar — eng tepada) ─────────── */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-gray-900">Faol safarlar</h2>
          {active.length > 0 && (
            <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-0.5 rounded-full">{active.length} ta</span>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-3">{[1, 2].map(i => <BookingCardSkeleton key={i} />)}</div>
        ) : active.length > 0 ? (
          <div className="space-y-3">{active.map(renderBookingCard)}</div>
        ) : bookings.length === 0 ? (
          <div className="py-10 text-center">
            <Car size={32} className="text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-500 mb-4">Hali safar band qilmagansiz</p>
            <Link href="/trips"><Button size="sm">Safar qidirish</Button></Link>
          </div>
        ) : (
          <p className="text-sm text-gray-400 py-8 text-center">Hozircha faol safaringiz yo'q — yangi buyurtma shu yerda chiqadi</p>
        )}
      </div>

      {/* ── 4 statistika ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs text-gray-400 mb-1">Jami safarlar</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">{completed.length}</p>
          <p className="text-xs text-gray-400 mt-1.5">{jamiSafarlar} bu yil</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs text-gray-400 mb-1">Jami to'lov</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums leading-none">{formatShort(jamiTolov)}</p>
          <p className="text-xs text-gray-400 mt-1.5">so'm</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs text-gray-400 mb-1">Sevimli yo'nalish</p>
          {favRoute ? (
            <>
              <p className="text-sm font-bold text-gray-900 leading-tight mt-1">{favRoute[0]}</p>
              <p className="text-xs text-gray-400 mt-1">{favRoute[1]} marta</p>
            </>
          ) : (
            <p className="text-sm text-gray-400 mt-2">Hali yo'q</p>
          )}
        </div>
      </div>

      {/* ── 2 ustun ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">

        {/* ══ CHAP ══ */}
        <div className="space-y-5">

          {/* O'tgan safarlar (tugaganlar — baho bilan) */}
          {completed.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold text-gray-900">O'tgan safarlar</h2>
                <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{completed.length} ta</span>
              </div>
              <div className="divide-y divide-gray-50">
                {(showAllPast ? completed : completed.slice(0, 3)).map((b) => {
                  const driver = b.trip?.driver;
                  const reviewed = reviewedIds.has(b.id);
                  const rev = reviewById(b.id);
                  return (
                    <div key={b.id} className="flex items-center gap-3 py-3">
                      <Avatar src={driver?.profile_photo ?? null} name={driver?.full_name ?? "Haydovchi"} size="sm" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {b.trip ? `${b.trip.from_region.name_uz} → ${b.trip.to_region.name_uz}` : "Safar"}
                        </p>
                        <p className="text-xs text-gray-400 truncate">
                          {driver?.full_name ?? "Haydovchi"} · {fmtDate(b.trip?.departure_date)} · {formatPrice(b.total_price)} so'm
                        </p>
                      </div>
                      {reviewed && rev ? (
                        <span className="flex items-center gap-0.5 text-xs font-medium text-yellow-500 shrink-0">
                          <Star size={12} className="fill-yellow-400 text-yellow-400" />{rev.rating}
                        </span>
                      ) : (
                        <Button size="sm" className="text-xs px-3 shrink-0" onClick={() => { setReviewError(""); setReviewRating(5); setReviewModal(b.id); }}>
                          Baho ber
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
              {completed.length > 3 && (
                <button
                  onClick={() => setShowAllPast(v => !v)}
                  className="w-full mt-3 py-2.5 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  {showAllPast ? "Kamroq ko'rsatish" : `Barchasini ko'rish (${completed.length})`}
                </button>
              )}
            </div>
          )}

          {/* Profil ma'lumotlari */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <h2 className="font-bold text-gray-900 mb-4">Profil ma'lumotlari</h2>
            <div className="space-y-3">
              {[
                { icon: UserIcon, label: "Ism familiya", value: user?.full_name, verified: false },
                { icon: Phone, label: "Telefon", value: user?.phone, verified: user?.is_phone_verified },
                { icon: Mail, label: "Email", value: user?.email || "—", verified: false },
              ].map(({ icon: Icon, label, value, verified }) => (
                <div key={label} className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-sm text-gray-500">
                    <Icon size={14} className="text-gray-400" />
                    {label}
                  </span>
                  <span className="flex items-center gap-1.5 text-sm font-medium text-gray-900 truncate">
                    {value}
                    {verified && (
                      <span className="text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">Tasdiqlangan</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-4">
              <Link href="/profile/edit" className="flex-1">
                <Button size="sm" variant="outline" fullWidth>Tahrirlash</Button>
              </Link>
              <Link href="/profile/security" className="flex-1">
                <Button size="sm" variant="outline" fullWidth>Parol</Button>
              </Link>
            </div>
          </div>
        </div>

        {/* ══ O'NG ══ */}
        <div className="space-y-5">

          {/* To'lovlar tarixi */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <h2 className="font-bold text-gray-900 mb-4">To'lovlar tarixi</h2>
            {payments.length === 0 ? (
              <p className="text-sm text-gray-400 py-6 text-center">Hali to'lov yo'q</p>
            ) : (
              <div className="space-y-3">
                {payments.slice(0, 6).map((p) => (
                  <div key={p.id} className="flex items-center gap-3">
                    <div className={clsx(
                      "w-9 h-9 rounded-lg flex items-center justify-center shrink-0",
                      p.refunded ? "bg-teal-50" : "bg-gray-50"
                    )}>
                      {p.refunded ? <RotateCcw size={15} className="text-teal-500" /> : <CreditCard size={15} className="text-gray-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{p.route}</p>
                      <p className="text-xs text-gray-400">
                        {fmtDate(p.date)} · {p.refunded ? "Bekor qilish" : `${p.method} orqali`}
                      </p>
                    </div>
                    <p className={clsx("text-sm font-bold tabular-nums shrink-0", p.amount > 0 ? "text-green-600" : "text-gray-900")}>
                      {p.amount > 0 ? "+" : ""}{formatPrice(p.amount)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Cancel modal ─────────────────────────────────────────────────── */}
      <Modal open={!!cancelModal} onClose={() => setCancelModal(null)} title="Band qilishni bekor qilish">
        <div className="space-y-4">
          <div className="bg-yellow-50 rounded-xl p-4 text-sm text-yellow-800">
            <AlertCircle size={15} className="inline mr-1.5 mb-0.5" />
            Safardan 24 soat oldin bekor qilsangiz, to'liq qaytariladi. Undan keyin — 50%.
          </div>
          {cancelError && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">{cancelError}</div>
          )}
          <div className="flex gap-3">
            <Button variant="outline" fullWidth onClick={() => setCancelModal(null)}>Yo'q, qoldiraman</Button>
            <Button fullWidth className="bg-red-500 hover:bg-red-600" loading={cancelMutation.isPending}
              onClick={() => cancelModal && cancelMutation.mutate(cancelModal)}>
              Ha, bekor qilish
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Review modal ─────────────────────────────────────────────────── */}
      <Modal open={!!reviewModal} onClose={() => setReviewModal(null)} title="Haydovchini baholash">
        <div className="space-y-4">
          <div className="flex justify-center gap-2 py-2">
            {[1, 2, 3, 4, 5].map((s) => (
              <button key={s} type="button" onClick={() => setReviewRating(s)}>
                <Star size={32} className={clsx("transition-colors", s <= reviewRating ? "fill-yellow-400 text-yellow-400" : "fill-gray-100 text-gray-300")} />
              </button>
            ))}
          </div>
          <textarea
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            rows={3}
            placeholder="Safaringiz haqida yozing (ixtiyoriy)..."
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
          />
          {reviewError && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">{reviewError}</div>
          )}
          <Button fullWidth loading={reviewMutation.isPending}
            onClick={() => reviewModal && reviewMutation.mutate({ id: reviewModal, rating: reviewRating, comment: reviewText })}>
            Baholashni yuborish
          </Button>
        </div>
      </Modal>
    </div>
  );
}
