"use client";

import { useState } from "react";

export type GeoState = "idle" | "loading" | "error";

export interface Coords {
  lat: number;
  lng: number;
}

/**
 * Olib ketish joyini aniqlash — brauzerning o'z geolokatsiyasi, xarita
 * provayderi kerak emas.
 *
 * Ikki narsani hisobga oladi:
 * 1. Xatoning SABABI aytiladi — "olib bo'lmadi" degan umumiy matn bilan
 *    foydalanuvchi nima qilishini bilmaydi (ruxsat rad etilganmi, uzoq
 *    kutildimi).
 * 2. iOS'da `enableHighAccuracy` yopiq joyda tez-tez taymautga uchraydi,
 *    shuning uchun taymautda bir marta qo'pol (tarmoq bo'yicha) aniqlash
 *    bilan qayta urinamiz.
 */
export function useGeolocation() {
  const [coords, setCoords] = useState<Coords | null>(null);
  const [state, setState] = useState<GeoState>("idle");
  const [error, setError] = useState("");

  function reset() {
    setCoords(null);
    setState("idle");
    setError("");
  }

  function request() {
    if (!navigator.geolocation) {
      setState("error");
      setError("Brauzeringiz joylashuvni bermaydi — manzilni yozib qo'ying.");
      return;
    }
    setState("loading");

    const ok = (pos: GeolocationPosition) => {
      setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      setState("idle");
      setError("");
    };

    const fail = (err: GeolocationPositionError) => {
      setState("error");
      setError(
        err.code === err.PERMISSION_DENIED
          ? "Joylashuvga ruxsat berilmadi. iPhone: Sozlamalar → Maxfiylik → Joylashuv → Safari. Ruxsatsiz ham bo'ladi — manzilni yozing."
          : err.code === err.TIMEOUT
            ? "Joylashuv aniqlanmadi — yana urinib ko'ring yoki manzilni yozing."
            : "Joylashuvni olib bo'lmadi — manzilni yozib qo'ying, yetarli.",
      );
    };

    navigator.geolocation.getCurrentPosition(
      ok,
      (err) => {
        if (err.code === err.TIMEOUT) {
          navigator.geolocation.getCurrentPosition(ok, fail, {
            enableHighAccuracy: false,
            timeout: 15000,
            maximumAge: 300000,
          });
        } else {
          fail(err);
        }
      },
      { enableHighAccuracy: true, timeout: 12000 },
    );
  }

  return { coords, state, error, request, reset };
}
