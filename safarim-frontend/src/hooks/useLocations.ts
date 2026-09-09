"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { District, Region } from "@/types";

export interface RegionWithDistricts extends Region {
  districts: District[];
}

/**
 * Barcha viloyat va tumanlar — BITTA so'rovda (`/locations/regions/all`).
 *
 * Qidiruv uchun hammasi bir vaqtda kerak: odam «Quva» deb yozganda qaysi
 * viloyatda ekanini bilmasligi mumkin. Ro'yxat o'zgarmaydi, shuning uchun
 * bir kun keshlanadi va ilova davomida qayta so'ralmaydi.
 */
export function useAllLocations() {
  return useQuery<RegionWithDistricts[]>({
    queryKey: ["locations", "all"],
    queryFn: async () => {
      const { data } = await api.get("/locations/regions/all");
      return data;
    },
    staleTime: 24 * 60 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
  });
}

/**
 * Qidiruv uchun matnni soddalashtiradi.
 *
 * O'zbek yozuvida bir tovush bir necha xil yoziladi: «Farg'ona», «Fargʻona»,
 * «Fargona», «Farg`ona». Odam qaysi belgini terishini bilib bo'lmaydi —
 * shuning uchun apostroflar butunlay olib tashlanadi va solishtirish
 * kichik harfda bo'ladi. «sh»/«ch» kabi qo'shimchalarga tegilmaydi.
 */
export function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[’'`ʻʼ‘´]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
