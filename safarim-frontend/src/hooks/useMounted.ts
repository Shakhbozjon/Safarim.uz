"use client";

import { useEffect, useState } from "react";

/**
 * Brauzerda birinchi render serverdagiga mos kelishi uchun.
 *
 * Sahifalar kirgan/kirmagan holatga qarab boshqa narsa chizadi, holat esa
 * cookie'da: serverda uni `js-cookie` ko'rmaydi, brauzerda esa darrov ko'radi
 * — natijada React "hydration failed" deb butun daraxtni qaytadan chizadi.
 * Shuning uchun auth'ga bog'liq shoxlar `mounted` bo'lgunicha kutadi.
 */
export function useMounted() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
