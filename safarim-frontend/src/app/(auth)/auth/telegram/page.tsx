"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { saveTokens, getApiError } from "@/lib/auth";

/**
 * Botdagi «Saytga kirish» havolasi shu yerga olib keladi: `/auth/telegram?t=<token>`.
 *
 * Botda ro'yxatdan o'tgan odamning paroli yo'q — token bir martalik va
 * 5 daqiqalik. Sahifaning o'zi (serverda) hech narsa qilmaydi: tokenni
 * brauzerdagi skript POST bilan almashtiradi. Shunda Telegram havolani
 * oldindan ko'rish uchun ochsa ham token sarflanib ketmaydi.
 */
/** Faqat sayt ichidagi yo'l — `//begona.sayt` yoki `https://...` ga yo'naltirib bo'lmasin */
function safeNext(raw: string | null): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) return null;
  return raw;
}

function TelegramLogin() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState("");
  // Token faqat BIR marta ishlaydi — React dev rejimida effekt ikki marta
  // chaqirilsa ham so'rov bitta ketsin
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const token = params.get("t");
    if (!token) {
      setError("Havola noto'liq. Botdagi «Saytga kirish» tugmasini qayta bosing.");
      return;
    }

    (async () => {
      try {
        const { data: tokens } = await api.post("/auth/telegram-login", { token });
        saveTokens(tokens);
        // Bot «Safar qidirish» yoki joy band qilishdan kelgan bo'lsa — o'sha sahifaga
        const next = safeNext(params.get("next"));
        if (next) {
          router.replace(next);
          return;
        }
        const { data: me } = await api.get("/auth/me");
        router.replace(me.is_driver ? "/driver" : "/my-trips");
      } catch (err: any) {
        setError(getApiError(err));
      }
    })();
  }, [params, router]);

  if (error) {
    return (
      <div className="text-center space-y-4">
        <h1 className="text-xl font-bold text-gray-900">Kirib bo&apos;lmadi</h1>
        <p className="text-sm text-gray-500">{error}</p>
        <p className="text-sm text-gray-500">
          Telegram botda <b>«🌐 Saytga kirish»</b> tugmasini qayta bosing — yangi havola keladi.
        </p>
        <Link href="/login" className="inline-block text-sm font-semibold text-primary-600 hover:underline">
          Parol bilan kirish →
        </Link>
      </div>
    );
  }

  return (
    <div className="text-center space-y-3 py-6">
      <div className="mx-auto w-8 h-8 border-2 border-primary-200 border-t-primary-500 rounded-full animate-spin" />
      <p className="text-sm text-gray-500">Kirilmoqda…</p>
    </div>
  );
}

export default function TelegramLoginPage() {
  return (
    <Suspense fallback={null}>
      <TelegramLogin />
    </Suspense>
  );
}
