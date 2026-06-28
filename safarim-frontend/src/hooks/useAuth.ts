"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { getMe, clearTokens, isAuthenticated } from "@/lib/auth";
import type { User } from "@/types";

export function useAuth() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: user, isLoading } = useQuery<User>({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: isAuthenticated(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  function logout() {
    clearTokens();
    qc.clear();
    router.push("/login");
  }

  return { user, isLoading, logout, isAuthenticated: !!user };
}
