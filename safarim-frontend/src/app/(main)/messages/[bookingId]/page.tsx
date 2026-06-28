"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Send, Wifi, WifiOff, Loader2, Circle } from "lucide-react";
import { clsx } from "clsx";
import Avatar from "@/components/ui/Avatar";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import api from "@/lib/api";
import type { MessageResponse, BookingResponse, TripResponse } from "@/types";

// ─── Vaqt formati ─────────────────────────────────────────────────────────────

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString("uz-UZ", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (d.toDateString() === today.toDateString()) return "Bugun";
  if (d.toDateString() === yesterday.toDateString()) return "Kecha";
  return d.toLocaleDateString("uz-UZ", { day: "numeric", month: "long" });
}

// ─── Bitta xabar ─────────────────────────────────────────────────────────────

interface MsgBubbleProps {
  msg: MessageResponse;
  isMe: boolean;
  showAvatar: boolean;   // birinchi xabar guruhida avatar ko'rinadi
  showDate: boolean;     // sana ajratuvchi
  dateLabel: string;
}

function MsgBubble({ msg, isMe, showAvatar, showDate, dateLabel }: MsgBubbleProps) {
  return (
    <>
      {showDate && (
        <div className="flex justify-center my-3">
          <span className="text-xs text-gray-400 bg-gray-50 rounded-full px-3 py-1">
            {dateLabel}
          </span>
        </div>
      )}

      <div className={clsx("flex gap-2 items-end", isMe ? "flex-row-reverse" : "flex-row")}>
        {/* Avatar — faqat boshqa odam, va faqat guruhning oxirgi xabarida */}
        <div className="w-7 shrink-0">
          {!isMe && showAvatar ? (
            <Avatar src={msg.sender.profile_photo} name={msg.sender.full_name} size="sm" />
          ) : null}
        </div>

        {/* Bubble */}
        <div
          className={clsx(
            "max-w-[72%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed",
            isMe
              ? "bg-primary-500 text-white rounded-br-sm"
              : "bg-white border border-gray-100 text-gray-900 rounded-bl-sm shadow-sm"
          )}
        >
          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
          <div
            className={clsx(
              "flex items-center gap-1 mt-1 text-[10px]",
              isMe ? "justify-end text-primary-200" : "justify-end text-gray-400"
            )}
          >
            <span>{fmtTime(msg.created_at)}</span>
            {isMe && (
              <span title={msg.is_read ? "O'qildi" : "Yetkazildi"}>
                {msg.is_read ? (
                  // Double check
                  <svg width="14" height="9" viewBox="0 0 14 9" fill="currentColor">
                    <path d="M1 4.5L4.5 8L13 1M5 4.5L8.5 8" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  // Single check
                  <svg width="10" height="9" viewBox="0 0 10 9" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 4.5L4 7.5L9 1" />
                  </svg>
                )}
              </span>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

// ─── Asosiy sahifa ────────────────────────────────────────────────────────────

export default function ChatPage() {
  const { bookingId } = useParams<{ bookingId: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const qc = useQueryClient();

  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [input, setInput] = useState("");
  const [partnerOnline, setPartnerOnline] = useState(false);
  const [sending, setSending] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  // ── Booking ma'lumotlari (header uchun) ──
  const { data: booking } = useQuery<BookingResponse>({
    queryKey: ["booking", bookingId],
    queryFn: async () => {
      const { data } = await api.get(`/bookings/${bookingId}`);
      return data;
    },
  });

  // ── Trip ma'lumotlari ──
  const { data: trip } = useQuery<TripResponse>({
    queryKey: ["trip", booking?.trip_id],
    queryFn: async () => {
      const { data } = await api.get(`/trips/${booking!.trip_id}`);
      return data;
    },
    enabled: !!booking?.trip_id,
  });

  // ── Chat tarixi ──
  const { isLoading: historyLoading } = useQuery<MessageResponse[]>({
    queryKey: ["messages", bookingId],
    queryFn: async () => {
      const { data } = await api.get(`/messages/${bookingId}`);
      return data;
    },
    onSuccess: (data: MessageResponse[]) => {
      setMessages(data);
    },
  } as any);

  // ── O'qilgan deb belgilash ──
  useEffect(() => {
    if (!bookingId) return;
    api.put(`/messages/${bookingId}/read`).catch(() => {});
    qc.invalidateQueries({ queryKey: ["unread-count"] });
  }, [bookingId, qc]);

  // ── WebSocket ──
  const handleNewMessage = useCallback((msg: MessageResponse) => {
    setMessages((prev) => {
      if (prev.find((m) => m.id === msg.id)) return prev; // dublikat yo'q
      return [...prev, msg];
    });
    // Boshqa odam xabarini o'qilgan deb belgilash
    if (msg.sender.id !== user?.id) {
      api.put(`/messages/${bookingId}/read`).catch(() => {});
    }
  }, [user?.id, bookingId]);

  const handleOnlineChange = useCallback((userId: string, online: boolean) => {
    if (userId !== user?.id) setPartnerOnline(online);
  }, [user?.id]);

  const { status: wsStatus, send } = useChat({
    bookingId,
    onMessage: handleNewMessage,
    onOnlineChange: handleOnlineChange,
  });

  // ── Auto-scroll ──
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Xabar yuborish ──
  async function handleSend() {
    const text = input.trim();
    if (!text || wsStatus !== "open") return;

    setSending(true);
    const ok = send(text);
    if (ok) {
      setInput("");
      inputRef.current?.focus();
    }
    setSending(false);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // ── Kimga yozmoqdamiz? ──
  const isDriver   = trip?.driver?.id === user?.id;
  const partnerName = isDriver
    ? (booking?.passenger?.full_name ?? "Yo'lovchi")
    : (trip?.driver?.full_name ?? "Haydovchi");
  const partnerPhoto = isDriver
    ? (booking?.passenger?.profile_photo ?? null)
    : (trip?.driver?.profile_photo ?? null);

  // ── Xabarlarni guruhlash (sana + avatar) ──
  function buildRows() {
    const rows: Array<{
      msg: MessageResponse;
      isMe: boolean;
      showAvatar: boolean;
      showDate: boolean;
      dateLabel: string;
    }> = [];

    let lastDate = "";
    let lastSender = "";

    for (let i = 0; i < messages.length; i++) {
      const msg  = messages[i];
      const next = messages[i + 1];
      const isMe = msg.sender.id === user?.id;

      const dateLabel = fmtDate(msg.created_at);
      const showDate  = dateLabel !== lastDate;

      // Avatar: boshqa odam, va keyingi xabar boshqa sender yoki yo'q
      const showAvatar =
        !isMe && (next?.sender?.id !== msg.sender.id || showDate);

      rows.push({ msg, isMe, showAvatar, showDate, dateLabel });
      lastDate   = dateLabel;
      lastSender = msg.sender.id;
    }
    return rows;
  }

  const rows = buildRows();

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-2xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-100 shrink-0">
        <button
          onClick={() => router.back()}
          className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <ArrowLeft size={18} />
        </button>

        <div className="relative">
          <Avatar src={partnerPhoto} name={partnerName} size="md" />
          {partnerOnline && (
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 rounded-full border-2 border-white" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">{partnerName}</p>
          {trip && (
            <p className="text-xs text-gray-400 truncate">
              {trip.from_region.name_uz} → {trip.to_region.name_uz} · {trip.departure_date}
            </p>
          )}
        </div>

        {/* WS holat ko'rsatkichi */}
        <div className="shrink-0">
          {wsStatus === "open" ? (
            <Wifi size={16} className="text-green-400" />
          ) : wsStatus === "connecting" ? (
            <Loader2 size={16} className="text-gray-400 animate-spin" />
          ) : (
            <WifiOff size={16} className="text-red-400" />
          )}
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1 bg-gray-50">
        {historyLoading ? (
          <div className="flex flex-col gap-3 animate-pulse">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className={clsx("flex gap-2", i % 2 === 0 ? "flex-row-reverse" : "flex-row")}>
                <div className="w-7 h-7 rounded-full bg-gray-200 shrink-0" />
                <div className={clsx(
                  "h-10 rounded-2xl bg-gray-200",
                  i % 3 === 0 ? "w-48" : "w-32"
                )} />
              </div>
            ))}
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3">
            <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center border border-gray-100 text-3xl">
              💬
            </div>
            <p className="text-sm font-semibold text-gray-700">Chat boshlang</p>
            <p className="text-xs text-gray-400">
              {partnerName} bilan safar haqida gaplashing
            </p>
          </div>
        ) : (
          rows.map(({ msg, isMe, showAvatar, showDate, dateLabel }) => (
            <MsgBubble
              key={msg.id}
              msg={msg}
              isMe={isMe}
              showAvatar={showAvatar}
              showDate={showDate}
              dateLabel={dateLabel}
            />
          ))
        )}

        {wsStatus === "closed" && (
          <div className="flex justify-center">
            <span className="text-xs text-gray-400 bg-yellow-50 border border-yellow-100 rounded-full px-3 py-1">
              Ulanish uzildi. Qayta ulanmoqda...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 bg-white border-t border-gray-100 shrink-0">
        {booking?.status === "cancelled" ? (
          <div className="text-center text-sm text-gray-400 py-2">
            Bron bekor qilingan — chat yopilgan
          </div>
        ) : (
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Xabar yozing..."
              rows={1}
              disabled={wsStatus !== "open"}
              className={clsx(
                "flex-1 resize-none rounded-2xl border bg-gray-50 px-4 py-3 text-sm text-gray-900",
                "placeholder:text-gray-400 outline-none transition-all leading-relaxed",
                "max-h-32 overflow-y-auto",
                wsStatus === "open"
                  ? "border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-400/20"
                  : "border-gray-100 opacity-50 cursor-not-allowed"
              )}
              style={{ minHeight: "44px" }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 128) + "px";
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || wsStatus !== "open" || sending}
              className={clsx(
                "w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 transition-all",
                input.trim() && wsStatus === "open"
                  ? "bg-primary-500 hover:bg-primary-600 text-white shadow-sm"
                  : "bg-gray-100 text-gray-400 cursor-not-allowed"
              )}
            >
              <Send size={18} />
            </button>
          </div>
        )}

        <p className="text-center text-[10px] text-gray-300 mt-2">
          Enter — yuborish · Shift+Enter — yangi qator
        </p>
      </div>
    </div>
  );
}
