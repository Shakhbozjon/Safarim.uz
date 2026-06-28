"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Users, Car, Clock, Map, BookOpen, CheckCircle, ArrowRight, Scale } from "lucide-react";
import api from "@/lib/api";
import type { AdminStats } from "@/types";

async function fetchStats(): Promise<AdminStats> {
  const { data } = await api.get("/admin/stats");
  return data;
}

interface StatCardProps {
  label: string;
  value: number | undefined;
  icon: React.ElementType;
  color: string;
  href?: string;
  badge?: number;
}

function StatCard({ label, value, icon: Icon, color, href, badge }: StatCardProps) {
  const inner = (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 flex items-start gap-4 hover:shadow-sm transition-shadow">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-2xl font-bold text-gray-900">
          {value === undefined ? <span className="inline-block w-16 h-7 bg-gray-100 animate-pulse rounded-lg" /> : value.toLocaleString()}
        </p>
        <p className="text-sm text-gray-500 mt-0.5">{label}</p>
        {badge !== undefined && badge > 0 && (
          <span className="inline-block mt-1.5 px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-semibold rounded-full">
            {badge} kutmoqda
          </span>
        )}
      </div>
      {href && <ArrowRight size={15} className="text-gray-300 shrink-0 mt-1" />}
    </div>
  );

  return href ? <Link href={href}>{inner}</Link> : <div>{inner}</div>;
}

export default function AdminDashboard() {
  const { data: stats } = useQuery<AdminStats>({
    queryKey: ["admin", "stats"],
    queryFn: fetchStats,
    refetchInterval: 30_000,
  });

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Safarim.uz — umumiy ko'rinish</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          label="Jami foydalanuvchilar"
          value={stats?.total_users}
          icon={Users}
          color="bg-blue-500"
          href="/admin/users"
        />
        <StatCard
          label="Tasdiqlangan haydovchilar"
          value={stats?.total_drivers}
          icon={Car}
          color="bg-green-500"
          href="/admin/drivers"
        />
        <StatCard
          label="Kutayotgan arizalar"
          value={stats?.pending_drivers}
          icon={Clock}
          color="bg-orange-500"
          href="/admin/drivers"
          badge={stats?.pending_drivers}
        />
        <StatCard
          label="Jami safarlar"
          value={stats?.total_trips}
          icon={Map}
          color="bg-purple-500"
        />
        <StatCard
          label="Jami bronlar"
          value={stats?.total_bookings}
          icon={BookOpen}
          color="bg-indigo-500"
        />
        <StatCard
          label="Tugatilgan bronlar"
          value={stats?.completed_bookings}
          icon={CheckCircle}
          color="bg-teal-500"
        />
        <StatCard
          label="Nizoli bronlar"
          value={stats?.disputed_bookings}
          icon={Scale}
          color="bg-rose-500"
          href="/admin/disputes"
          badge={stats?.disputed_bookings}
        />
      </div>

      {/* Quick actions */}
      {stats && stats.pending_drivers > 0 && (
        <div className="mt-8 bg-orange-50 border border-orange-100 rounded-2xl p-5 flex items-center justify-between">
          <div>
            <p className="font-semibold text-orange-900">
              {stats.pending_drivers} ta haydovchi arizasi kutmoqda
            </p>
            <p className="text-sm text-orange-700 mt-0.5">Ko'rib chiqing va tasdiqlang yoki rad eting</p>
          </div>
          <Link
            href="/admin/drivers"
            className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm font-semibold rounded-xl hover:bg-orange-600 transition-colors shrink-0"
          >
            Ko'rish
            <ArrowRight size={14} />
          </Link>
        </div>
      )}

      {stats && (stats.disputed_bookings ?? 0) > 0 && (
        <div className="mt-4 bg-rose-50 border border-rose-100 rounded-2xl p-5 flex items-center justify-between">
          <div>
            <p className="font-semibold text-rose-900">
              {stats.disputed_bookings} ta nizoli bron hal qilishni kutmoqda
            </p>
            <p className="text-sm text-rose-700 mt-0.5">Yo'lovchi va haydovchi safar haqida kelisha olmadi</p>
          </div>
          <Link
            href="/admin/disputes"
            className="flex items-center gap-2 px-4 py-2 bg-rose-500 text-white text-sm font-semibold rounded-xl hover:bg-rose-600 transition-colors shrink-0"
          >
            Hal qilish
            <ArrowRight size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}
