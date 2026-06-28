"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import Cookies from "js-cookie";
import type { MessageResponse, WsEvent } from "@/types";

export type ChatStatus = "connecting" | "open" | "closed" | "error";

interface UseChatOptions {
  bookingId: string;
  onMessage: (msg: MessageResponse) => void;
  onOnlineChange?: (userId: string, online: boolean) => void;
}

/** HTTP → WS URL: http://... → ws://..., https://... → wss://... */
function toWsUrl(apiUrl: string): string {
  return apiUrl.replace(/^http/, "ws");
}

export function useChat({ bookingId, onMessage, onOnlineChange }: UseChatOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted = useRef(true);

  const [status, setStatus] = useState<ChatStatus>("connecting");

  const connect = useCallback(() => {
    if (!isMounted.current) return;

    const token = Cookies.get("access_token");
    if (!token) {
      setStatus("error");
      return;
    }

    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const wsBase = toWsUrl(base);
    const url = `${wsBase}/messages/ws/${bookingId}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => {
      if (isMounted.current) setStatus("open");
    };

    ws.onmessage = (e) => {
      if (!isMounted.current) return;
      try {
        const event: WsEvent = JSON.parse(e.data);
        if (event.type === "message") {
          onMessage(event.data as MessageResponse);
        } else if (event.type === "online_status" && onOnlineChange) {
          onOnlineChange(event.data.user_id, event.data.online);
        }
        // "read" va "error" eventlarni hozircha log qilamiz
      } catch {
        // JSON parse xatolik
      }
    };

    ws.onclose = (e) => {
      if (!isMounted.current) return;
      setStatus("closed");
      // 4001 = token invalid, 4003 = forbidden — qayta ulanmaymiz
      if (e.code !== 4001 && e.code !== 4003 && e.code !== 4004) {
        reconnectTimer.current = setTimeout(() => {
          if (isMounted.current) connect();
        }, 3000);
      }
    };

    ws.onerror = () => {
      if (isMounted.current) setStatus("error");
    };
  }, [bookingId, onMessage, onOnlineChange]);

  // Xabar yuborish
  const send = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content }));
      return true;
    }
    return false;
  }, []);

  // Mount / unmount
  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status, send };
}
