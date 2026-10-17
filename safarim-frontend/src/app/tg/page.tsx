"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Script from "next/script";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { saveTokens, getApiError } from "@/lib/auth";
import { getWebApp } from "@/lib/telegram";

/**
 * Telegram Mini App kirish nuqtasi: botdagi «📱 UzSafar ilovasi» shu yerni ochadi.
 *
 * Mini App — alohida ilova emas, sayt o'zi (telefonga moslangan): bu sahifa
 * faqat Telegram imzosi bo'yicha avtomatik kirgizadi va foydalanuvchini
 * saytning tegishli sahifasiga o'tkazadi. Shuning uchun saytga qo'shilgan
 * har bir funksiya Mini App'da ham darrov bo'ladi.
 */

type State = "loading" | "outside" | "unregistered" | "error";

/** `startapp=trip_<32 hex>` → `/trips/<uuid>` — guruhdagi e'londan to'g'ri safarga */
function pathFromStartParam(param: string | undefined): string | null {
  const m = /^trip_([0-9a-f]{32})$/.exec(param || "");
  if (!m) return null;
  const h = m[1];
  return `/trips/${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

export default function TelegramMiniApp() {
  const router = useRouter();
  const [state, setState] = useState<State>("loading");
  const [error, setError] = useState("");
  const [bot, setBot] = useState("");
  const started = useRef(false);

  const start = useCallback(async () => {
    if (started.current) return;
    const wa = getWebApp();
    if (!wa) {
      // Skript yuklandi, lekin imzolangan ma'lumot yo'q — oddiy brauzerda ochilgan
      if (typeof window !== "undefined" && window.Telegram?.WebApp) setState("outside");
      return;
    }
    started.current = true;
    wa.ready();
    wa.expand();

    try {
      const { data } = await api.post("/auth/telegram-webapp", { init_data: wa.initData });
      if (!data.registered) {
        setBot(data.bot_username || "");
        setState("unregistered");
        return;
      }
      saveTokens({ access_token: data.access_token, refresh_token: data.refresh_token, token_type: "bearer" });
      const target = pathFromStartParam(data.start_param || wa.initDataUnsafe.start_param);
      if (target) {
        router.replace(target);
        return;
      }
      const { data: me } = await api.get("/auth/me");
      router.replace(me.is_driver ? "/driver" : "/my-trips");
    } catch (err: any) {
      setError(getApiError(err));
      setState("error");
    }
  }, [router]);

  // Skript keshdan oldinroq yuklangan bo'lishi mumkin — onLoad kelmay qoladi
  useEffect(() => {
    start();
    const t = setTimeout(() => {
      if (!started.current && !getWebApp()) setState("outside");
    }, 4000);
    return () => clearTimeout(t);
  }, [start]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50">
      <Script src="https://telegram.org/js/telegram-web-app.js" strategy="afterInteractive" onLoad={start} />

      <div className="w-full max-w-sm text-center space-y-4">
        {state === "loading" && (
          <>
            <div className="mx-auto w-8 h-8 border-2 border-primary-200 border-t-primary-500 rounded-full animate-spin" />
            <p className="text-sm text-gray-500">UzSafar ochilmoqda…</p>
          </>
        )}

        {state === "unregistered" && (
          <>
            <h1 className="text-xl font-bold text-gray-900">Avval ro&apos;yxatdan o&apos;ting</h1>
            <p className="text-sm text-gray-500">
              Bot ichida bir daqiqa: raqamni ulashasiz va ismingizni yozasiz. Keyin ilovani qayta oching.
            </p>
            <button
              type="button"
              onClick={() => {
                const wa = getWebApp();
                if (wa && bot) {
                  wa.openTelegramLink(`https://t.me/${bot}?start=royxat`);
                  wa.close();
                }
              }}
              className="w-full rounded-xl bg-[#229ED9] hover:bg-[#1c8cc2] text-white font-semibold py-3 transition-colors"
            >
              Ro&apos;yxatdan o&apos;tish
            </button>
          </>
        )}

        {state === "outside" && (
          <>
            <h1 className="text-xl font-bold text-gray-900">Bu sahifa Telegram ichida ochiladi</h1>
            <p className="text-sm text-gray-500">Saytdan foydalanish uchun bosh sahifaga o&apos;ting.</p>
            <a href="/" className="inline-block text-sm font-semibold text-primary-600 hover:underline">
              uzsafar.uz →
            </a>
          </>
        )}

        {state === "error" && (
          <>
            <h1 className="text-xl font-bold text-gray-900">Kirib bo&apos;lmadi</h1>
            <p className="text-sm text-gray-500">{error}</p>
          </>
        )}
      </div>
    </div>
  );
}
