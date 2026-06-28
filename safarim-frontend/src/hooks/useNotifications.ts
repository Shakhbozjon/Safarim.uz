"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { NotificationResponse } from "@/types";

// ─── Unread count (Navbar uchun) ──────────────────────────────────────────────

export function useUnreadCount() {
  const { data } = useQuery<{ count: number }>({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.get("/notifications/unread-count").then((r) => r.data),
    enabled: isAuthenticated(),
    refetchInterval: 30_000,   // 30 soniyada bir yangilanadi
    staleTime: 15_000,
  });
  return data?.count ?? 0;
}

// ─── To'liq ro'yxat (sahifa uchun) ───────────────────────────────────────────

export function useNotifications() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<NotificationResponse[]>({
    queryKey: ["notifications"],
    queryFn: () => api.get("/notifications").then((r) => r.data),
    enabled: isAuthenticated(),
    staleTime: 10_000,
  });

  const readAllMut = useMutation({
    mutationFn: () => api.put("/notifications/read-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  const readOneMut = useMutation({
    mutationFn: (id: string) => api.put(`/notifications/${id}/read`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  return {
    notifications: data ?? [],
    isLoading,
    readAll: readAllMut.mutate,
    readOne: readOneMut.mutate,
  };
}
