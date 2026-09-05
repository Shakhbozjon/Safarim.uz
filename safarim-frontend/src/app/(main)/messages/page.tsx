"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { MessageCircle, ChevronRight, ArrowRight } from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Button from "@/components/ui/Button";
import { BookingCardSkeleton } from "@/components/ui/Skeleton";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useMounted } from "@/hooks/useMounted";
import type { BookingResponse } from "@/types";
import { shortDate } from "@/lib/date";
import { clsx } from "clsx";

/** Chat qaysi holatlarda ochiq — bekor qilingan buyurtmada yozishish ma'nosiz */
const CHATTABLE = ["confirmed", "awaiting_confirmation", "disputed", "completed"];

export default function MessagesPage() {
  const mounted = useMounted();
  const { user, isLoading: authLoading } = useAuth();
  const isDriver = user?.is_driver === true;

  // Haydovchi o'z safarlariga kelgan buyurtmalarni, yo'lovchi esa o'zinikini ko'radi
  const { data: bookings = [], isLoading } = useQuery<BookingResponse[]>({
    queryKey: ["chat-bookings", isDriver],
    queryFn: async () => (await api.get(isDriver ? "/bookings/driver" : "/bookings/my")).data,
    enabled: !!user,
  });

  const { data: unreadList = [] } = useQuery<{ booking_id: string; unread_count: number }[]>({
    queryKey: ["unread-count"],
    queryFn: async () => (await api.get("/messages/unread/count")).data,
    enabled: !!user,
    refetchInterval: 30_000,
  });

  const unreadOf = (id: string) =>
    unreadList.find((u) => u.booking_id === id)?.unread_count ?? 0;

  if (!mounted || authLoading || isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 space-y-3">
        <BookingCardSkeleton />
        <BookingCardSkeleton />
      </div>
    );
  }

  const chats = bookings
    .filter((b) => CHATTABLE.includes(b.status))
    .sort((a, b) => {
      // O'qilmagani bor suhbat tepada, keyin yangi safar
      const diff = (unreadOf(b.id) > 0 ? 1 : 0) - (unreadOf(a.id) > 0 ? 1 : 0);
      if (diff !== 0) return diff;
      const da = a.trip?.departure_date ?? a.created_at;
      const db_ = b.trip?.departure_date ?? b.created_at;
      return db_.localeCompare(da);
    });

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-5">Xabarlar</h1>

      {chats.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gray-50 flex items-center justify-center mx-auto mb-4">
            <MessageCircle size={24} className="text-gray-300" />
          </div>
          <p className="text-gray-500 mb-1">Hali suhbat yo&apos;q</p>
          <p className="text-sm text-gray-400 mb-5">
            {isDriver
              ? "Safaringizga yo'lovchi band qilgach, shu yerda yozishasiz."
              : "Safar band qilgach, haydovchi bilan shu yerda yozishasiz."}
          </p>
          <Link href={isDriver ? "/driver" : "/trips"}>
            <Button variant="outline">
              {isDriver ? "Panelga o'tish" : "Safar qidirish"}
            </Button>
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 divide-y divide-gray-50 overflow-hidden">
          {chats.map((b) => {
            const other = isDriver ? b.passenger : b.trip?.driver;
            const unread = unreadOf(b.id);
            return (
              <Link
                key={b.id}
                href={`/messages/${b.id}`}
                className="flex items-center gap-3 p-4 hover:bg-gray-50/70 transition-colors"
              >
                <div className="relative shrink-0">
                  <Avatar src={other?.profile_photo ?? null} name={other?.full_name} size="md" />
                  {unread > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-red-500 rounded-full flex items-center justify-center text-white text-[10px] font-bold px-1">
                      {unread > 99 ? "99+" : unread}
                    </span>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className={clsx(
                    "truncate text-gray-900",
                    unread > 0 ? "font-bold" : "font-semibold"
                  )}>
                    {other?.full_name ?? "Foydalanuvchi"}
                  </p>
                  {b.trip && (
                    <p className="flex items-center gap-1 text-xs text-gray-500 mt-0.5 min-w-0">
                      <span className="truncate">{b.trip.from_region.name_uz}</span>
                      <ArrowRight size={11} className="text-gray-300 shrink-0" />
                      <span className="truncate">{b.trip.to_region.name_uz}</span>
                      <span className="text-gray-300 shrink-0">·</span>
                      <span className="shrink-0 tabular-nums">
                        {shortDate(b.trip.departure_date)}
                      </span>
                    </p>
                  )}
                </div>

                <ChevronRight size={16} className="text-gray-300 shrink-0" />
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
