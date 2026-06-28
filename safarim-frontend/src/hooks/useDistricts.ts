"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { District } from "@/types";

export function useDistricts(regionId: number | null) {
  return useQuery<District[]>({
    queryKey: ["districts", regionId],
    queryFn: () =>
      api.get(`/locations/regions/${regionId}/districts`).then((r) => r.data),
    enabled: regionId !== null && regionId > 0,
    staleTime: 24 * 60 * 60 * 1000, // 1 kun — tumanlar o'zgarmaydi
    gcTime:    24 * 60 * 60 * 1000,
  });
}
