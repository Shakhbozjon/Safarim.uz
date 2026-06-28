"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Region } from "@/types";

export function useRegions() {
  return useQuery<Region[]>({
    queryKey: ["regions"],
    queryFn: async () => {
      const { data } = await api.get("/locations/regions");
      return data;
    },
    staleTime: 24 * 60 * 60 * 1000, // 1 kun — viloyatlar o'zgarmaydi
    gcTime: 24 * 60 * 60 * 1000,
  });
}

/** ID bo'yicha viloyat nomi (name_uz) */
export function regionName(regions: Region[] | undefined, id: number): string {
  return regions?.find((r) => r.id === id)?.name_uz ?? String(id);
}

/** Nom bo'yicha viloyat ID si */
export function regionIdByName(regions: Region[] | undefined, name: string): number | null {
  const r = regions?.find(
    (r) => r.name_uz.toLowerCase() === name.toLowerCase()
  );
  return r?.id ?? null;
}
