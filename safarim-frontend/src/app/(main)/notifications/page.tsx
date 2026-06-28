"use client";

import Link from "next/link";
import { Bell, CheckCheck, BookOpen, Car, Star, Info } from "lucide-react";
import { clsx } from "clsx";
import { useNotifications } from "@/hooks/useNotifications";
import type { NotificationResponse, NotificationRefType } from "@/types";

// ─── Ref type → icon ─────────────────────────────────────────────────────────

function RefIcon({ type }: { type: NotificationRefType | null }) {
  const cls = "shrink-0 mt-0.5";
  if (type === "booking") return <BookOpen size={16} className={clsx(cls, "text-blue-500")} />;
  if (type === "trip")    return <Car size={16} className={clsx(cls, "text-green-500")} />;
  if (type === "review")  return <Star size={16} className={clsx(cls, "text-yellow-500")} />;
  return <Info size={16} className={clsx(cls, "text-gray-400")} />;
}

// ─── Ref → link ──────────────────────────────────────────────────────────────

function refLink(notif: NotificationResponse): string | null {
  if (notif.ref_type === "booking" && notif.ref_id) return `/my-trips`;
  if (notif.ref_type === "trip" && notif.ref_id)    return `/trips/${notif.ref_id}`;
  return null;
}

// ─── Vaqt formati ─────────────────────────────────────────────────────────────

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "Hozirgina";
  if (m < 60) return `${m} daqiqa oldin`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} soat oldin`;
  const d = Math.floor(h / 24);
  if (d < 7)  return `${d} kun oldin`;
  return new Date(iso).toLocaleDateString("uz-UZ", { day: "2-digit", month: "short" });
}

// ─── Bitta card ───────────────────────────────────────────────────────────────

function NotifCard({
  notif,
  onRead,
}: {
  notif: NotificationResponse;
  onRead: (id: string) => void;
}) {
  const href = refLink(notif);

  const inner = (
    <div
      className={clsx(
        "flex items-start gap-3 px-5 py-4 transition-colors",
        !notif.is_read ? "bg-blue-50/60 hover:bg-blue-50" : "hover:bg-gray-50"
      )}
      onClick={() => !notif.is_read && onRead(notif.id)}
    >
      {/* Icon */}
      <div
        className={clsx(
          "w-9 h-9 rounded-xl flex items-center justify-center shrink-0",
          !notif.is_read ? "bg-blue-100" : "bg-gray-100"
        )}
      >
        <RefIcon type={notif.ref_type} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className={clsx(
              "text-sm leading-snug",
              !notif.is_read ? "font-semibold text-gray-900" : "font-medium text-gray-700"
            )}
          >
            {notif.title}
          </p>
          {!notif.is_read && (
            <span className="w-2 h-2 bg-blue-500 rounded-full shrink-0 mt-1.5" />
          )}
        </div>
        <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{notif.body}</p>
        <p className="text-xs text-gray-400 mt-1">{timeAgo(notif.created_at)}</p>
      </div>
    </div>
  );

  return href ? (
    <Link href={href} className="block cursor-pointer">{inner}</Link>
  ) : (
    <div className="cursor-default">{inner}</div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const { notifications, isLoading, readAll, readOne } = useNotifications();
  const unread = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="max-w-xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Bildirishnomalar</h1>
          {unread > 0 && (
            <p className="text-sm text-gray-400 mt-0.5">{unread} ta o'qilmagan</p>
          )}
        </div>
        {unread > 0 && (
          <button
            onClick={() => readAll()}
            className="flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            <CheckCheck size={15} />
            Hammasini o'qildi
          </button>
        )}
      </div>

      {/* List */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {isLoading && (
          <div className="divide-y divide-gray-50">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-start gap-3 px-5 py-4 animate-pulse">
                <div className="w-9 h-9 bg-gray-100 rounded-xl shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-100 rounded w-3/4" />
                  <div className="h-3 bg-gray-100 rounded w-full" />
                  <div className="h-3 bg-gray-100 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && notifications.length === 0 && (
          <div className="py-16 flex flex-col items-center text-center">
            <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mb-3">
              <Bell size={24} className="text-gray-300" />
            </div>
            <p className="text-gray-500 font-medium">Hali bildirishnoma yo'q</p>
            <p className="text-sm text-gray-400 mt-1">
              Bron yoki safar yangiliklari shu yerda ko'rinadi
            </p>
          </div>
        )}

        {!isLoading && notifications.length > 0 && (
          <div className="divide-y divide-gray-50">
            {notifications.map((n) => (
              <NotifCard key={n.id} notif={n} onRead={readOne} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
