"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Car,
  ClipboardList,
  Clock,
  RefreshCw,
  Scale,
  Table2,
  Wallet,
} from "lucide-react";
import api from "@/lib/api";
import { formatPrice } from "@/lib/format";
import type { AdminStats } from "@/types";
import StatTile from "@/components/admin/StatTile";
import TrendChart, { type SeriesDef } from "@/components/admin/TrendChart";

const PERIODS = [
  { days: 7, label: "7 kun" },
  { days: 30, label: "30 kun" },
  { days: 90, label: "90 kun" },
];

// Ranglar CVD (rang ko'rmaslik) tekshiruvidan o'tgan uchlik; har chiziq
// oxirida matnli yorliq ham turadi — rang yagona belgi bo'lib qolmasin.
const SERIES: SeriesDef[] = [
  { key: "users", label: "Ro'yxatdan o'tish", color: "#2a78d6" },
  { key: "trips", label: "Safarlar", color: "#eb6834" },
  { key: "bookings", label: "Band qilishlar", color: "#1baf7a" },
];

async function fetchStats(days: number): Promise<AdminStats> {
  const { data } = await api.get("/admin/stats", { params: { days } });
  return data;
}

/** Ish navbati kartasi — bosilganda tegishli sahifaga olib boradi */
function QueueCard({
  label, value, href, tone, icon: Icon, suffix,
}: {
  label: string;
  value: number | undefined;
  href?: string;
  tone: "urgent" | "warn" | "calm";
  icon: React.ElementType;
  suffix?: string;
}) {
  const active = (value ?? 0) > 0;
  const styles = {
    urgent: "border-rose-100 bg-rose-50 text-rose-700",
    warn: "border-amber-100 bg-amber-50 text-amber-800",
    calm: "border-gray-100 bg-white text-gray-700",
  }[active ? tone : "calm"];

  const inner = (
    <div className={clsx("flex h-full items-start gap-2.5 rounded-2xl border p-4", styles)}>
      <Icon size={17} className="mt-0.5 shrink-0 opacity-80" />
      <div className="min-w-0 flex-1">
        <p className="text-[19px] font-bold leading-none tabular-nums">
          {value === undefined ? "—" : `${value.toLocaleString("ru-RU").replace(/ /g, " ")}${suffix ?? ""}`}
        </p>
        {/* Yorliq qisqartirilmaydi — ikki qatorga tushsa ham to'liq o'qilsin */}
        <p className="mt-1 text-[12px] leading-snug opacity-80">{label}</p>
      </div>
      {href && active && <ArrowRight size={14} className="mt-1 shrink-0 opacity-60" />}
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

/** Foizli ko'rsatkich — chiziqcha bilan */
function RateBar({
  label, value, good = "high", hint,
}: {
  label: string;
  value: number | null | undefined;
  good?: "high" | "low";
  hint?: string;
}) {
  const v = value ?? null;
  const ok = v === null ? null : good === "high" ? v >= 60 : v <= 25;
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-[13px] text-gray-500">{label}</span>
        <span className="text-[15px] font-bold text-gray-900 tabular-nums">
          {v === null ? "—" : `${v}%`}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={clsx(
            "h-full rounded-full transition-all",
            ok === null ? "bg-gray-200" : ok ? "bg-green-500" : "bg-amber-500"
          )}
          style={{ width: `${Math.min(v ?? 0, 100)}%` }}
        />
      </div>
      {hint && <p className="mt-1 text-[11.5px] text-gray-400">{hint}</p>}
    </div>
  );
}

const ACTION_LABELS: Record<string, string> = {
  approve_driver: "Haydovchi tasdiqlandi",
  reject_driver: "Haydovchi rad etildi",
  block_user: "Foydalanuvchi bloklandi",
  unblock_user: "Blokdan chiqarildi",
  warn_driver: "Ogohlantirish berildi",
  cancel_trip: "Safar bekor qilindi",
  verify_phone: "Raqam tasdiqlandi",
  wallet_topup: "Hamyon to'ldirildi",
  commission_paid: "Komissiya to'landi",
};

export default function AdminDashboard() {
  const [days, setDays] = useState(30);
  const [showTable, setShowTable] = useState(false);

  const { data: stats, isFetching, refetch } = useQuery<AdminStats>({
    queryKey: ["admin", "stats", days],
    queryFn: () => fetchStats(days),
    refetchInterval: 60_000,
    placeholderData: (prev) => prev,
  });

  const k = stats?.kpi;
  const a = stats?.alerts;
  const q = stats?.quality;

  return (
    <div className="p-5 sm:p-8">
      {/* ── Sarlavha + davr ── */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            {stats ? `${stats.range.from} — ${stats.range.to}` : "Yuklanmoqda..."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-xl border border-gray-200 bg-white p-1">
            {PERIODS.map((p) => (
              <button
                key={p.days}
                onClick={() => setDays(p.days)}
                className={clsx(
                  "rounded-lg px-3 py-1.5 text-[13px] font-semibold transition-colors",
                  days === p.days ? "bg-primary-500 text-white" : "text-gray-500 hover:text-gray-800"
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            aria-label="Yangilash"
            className="rounded-xl border border-gray-200 bg-white p-2.5 text-gray-500 transition-colors hover:text-gray-800"
          >
            <RefreshCw size={15} className={clsx(isFetching && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* ── Ish navbati ── */}
      <section className="mb-7">
        <h2 className="mb-3 text-[13px] font-bold uppercase tracking-wider text-gray-400">
          Ish navbati
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
          <QueueCard label="Kutayotgan ariza" value={a?.pending_drivers} href="/admin/drivers" tone="warn" icon={Clock} />
          <QueueCard label="Ochiq nizo" value={a?.open_disputes} href="/admin/disputes" tone="urgent" icon={Scale} />
          <QueueCard label="Tasdiq kutmoqda" value={a?.awaiting_confirmation} tone="calm" icon={ClipboardList} />
          <QueueCard label="To'lanmagan komissiya, so'm" value={a?.unpaid_commission} href="/admin/commissions" tone="warn" icon={Wallet} />
          <QueueCard label="Bloklangan hamyon" value={a?.blocked_wallets} href="/admin/users" tone="urgent" icon={AlertTriangle} />
          <QueueCard label="Faol safar" value={a?.active_trips} tone="calm" icon={Car} />
        </div>
      </section>

      {/* ── KPI ── */}
      <section className="mb-7">
        <h2 className="mb-3 text-[13px] font-bold uppercase tracking-wider text-gray-400">
          Oxirgi {days} kun
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
          <StatTile label="Yangi foydalanuvchi" metric={k?.users} hint={k && `jami ${k.users.total}`} href="/admin/users" />
          <StatTile label="Yangi haydovchi" metric={k?.drivers} hint={k && `jami ${k.drivers.total}`} href="/admin/drivers" />
          <StatTile label="E'lon qilingan safar" metric={k?.trips} hint={k && `jami ${k.trips.total}`} />
          <StatTile label="Band qilish" metric={k?.bookings} hint={k && `jami ${k.bookings.total}`} />
          <StatTile label="Yakunlangan safar" metric={k?.completed} hint={k && `jami ${k.completed.total}`} />
          <StatTile label="Aylanma" metric={k?.gmv} money hint={k ? `komissiya ${formatPrice(k.commission.period)}` : undefined} />
        </div>
      </section>

      {/* ── Grafik + sifat ── */}
      <section className="mb-7 grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-gray-100 bg-white p-4 sm:p-5 lg:col-span-2">
          <div className="mb-1 flex items-center justify-between gap-3">
            <h3 className="text-[15px] font-bold text-gray-900">Kunlik faollik</h3>
            <button
              onClick={() => setShowTable((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-[12px] font-semibold text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-800"
            >
              {showTable ? <BarChart3 size={13} /> : <Table2 size={13} />}
              {showTable ? "Grafik" : "Jadval"}
            </button>
          </div>

          {/* Legenda — rang yagona belgi bo'lib qolmasligi uchun */}
          <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1">
            {SERIES.map((s) => (
              <span key={s.key} className="inline-flex items-center gap-1.5 text-[12px] text-gray-500">
                <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                {s.label}
              </span>
            ))}
          </div>

          {!stats ? (
            <div className="h-[240px] animate-pulse rounded-xl bg-gray-50" />
          ) : showTable ? (
            <div className="max-h-[240px] overflow-auto">
              <table className="w-full text-[13px]">
                <thead className="sticky top-0 bg-white">
                  <tr className="text-left text-[11px] uppercase tracking-wide text-gray-400">
                    <th className="py-2 font-semibold">Sana</th>
                    {SERIES.map((s) => (
                      <th key={s.key} className="py-2 text-right font-semibold">{s.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...stats.series].reverse().map((row) => (
                    <tr key={row.date} className="border-t border-gray-50">
                      <td className="py-1.5 text-gray-500">{row.date}</td>
                      <td className="py-1.5 text-right tabular-nums text-gray-800">{row.users}</td>
                      <td className="py-1.5 text-right tabular-nums text-gray-800">{row.trips}</td>
                      <td className="py-1.5 text-right tabular-nums text-gray-800">{row.bookings}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <TrendChart data={stats.series} series={SERIES} height={240} />
          )}
        </div>

        <div className="rounded-2xl border border-gray-100 bg-white p-4 sm:p-5">
          <h3 className="mb-4 text-[15px] font-bold text-gray-900">Sifat</h3>
          <div className="space-y-4">
            <RateBar
              label="Yakunlangan safarlar"
              value={q?.completion_rate}
              hint={q ? `${q.finished_bookings} ta yakuniga yetgan band qilishdan` : undefined}
            />
            <RateBar label="Bekor qilingan" value={q?.cancellation_rate} good="low" />
            <RateBar label="O'rinlar to'lgani" value={q?.seat_fill_rate} hint="e'lon qilingan o'rinlarning nechasi band bo'lgan" />
            <div className="border-t border-gray-50 pt-3">
              <p className="text-[13px] text-gray-500">O&apos;rtacha narx (bir o&apos;rin)</p>
              <p className="mt-0.5 text-[19px] font-bold text-gray-900 tabular-nums">
                {q?.avg_price ? `${formatPrice(q.avg_price)} so'm` : "—"}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Yo'nalishlar + admin harakatlari ── */}
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-gray-100 bg-white p-4 sm:p-5">
          <h3 className="mb-3 text-[15px] font-bold text-gray-900">Faol yo&apos;nalishlar</h3>
          {!stats ? (
            <div className="h-32 animate-pulse rounded-xl bg-gray-50" />
          ) : stats.top_routes.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">Bu davrda safar e&apos;lon qilinmagan</p>
          ) : (
            <table className="w-full text-[13.5px]">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-gray-400">
                  <th className="pb-2 font-semibold">Yo&apos;nalish</th>
                  <th className="pb-2 text-right font-semibold">Safar</th>
                  <th className="pb-2 text-right font-semibold">Band</th>
                </tr>
              </thead>
              <tbody>
                {stats.top_routes.map((r) => (
                  <tr key={`${r.from}-${r.to}`} className="border-t border-gray-50">
                    <td className="py-2 text-gray-800">
                      {r.from} <span className="text-gray-300">→</span> {r.to}
                    </td>
                    <td className="py-2 text-right tabular-nums text-gray-600">{r.trips}</td>
                    <td className="py-2 text-right font-semibold tabular-nums text-gray-900">{r.bookings}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="rounded-2xl border border-gray-100 bg-white p-4 sm:p-5">
          <h3 className="mb-3 text-[15px] font-bold text-gray-900">Oxirgi admin harakatlari</h3>
          {!stats ? (
            <div className="h-32 animate-pulse rounded-xl bg-gray-50" />
          ) : stats.recent_actions.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">Hali harakat qilinmagan</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {stats.recent_actions.map((act, i) => (
                <li key={i} className="flex items-start gap-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-[13.5px] font-semibold text-gray-800">
                      {ACTION_LABELS[act.action] ?? act.action}
                      {act.target && <span className="font-normal text-gray-500"> · {act.target}</span>}
                    </p>
                    <p className="truncate text-[12px] text-gray-400">{act.reason}</p>
                  </div>
                  <span className="shrink-0 text-[11.5px] text-gray-400">
                    {new Date(act.at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
