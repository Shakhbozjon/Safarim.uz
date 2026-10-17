"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getWebApp, isTelegramApp } from "@/lib/telegram";

// Bu sahifalardan orqaga yo'l yo'q — Telegramning o'z «yopish» tugmasi qoladi
const ROOTS = new Set(["/", "/tg", "/my-trips", "/driver"]);

// Saytning yorug' ranglari — Telegram qorong'i mavzuda bo'lsa ham uning
// tepa paneli sayt bilan bir xil oq bo'lsin (qorong'i mavzu ataylab yo'q)
const HEADER_COLOR = "#ffffff";
const BG_COLOR = "#f9fafb";

/**
 * Mini App ichida:
 *  - `<html>` ga `tg-app` klassi — sayt sarlavhasi yashiriladi (globals.css),
 *    Telegram oynasining o'zida nom allaqachon yozilgan;
 *  - Telegram «← Orqaga» tugmasi sayt tarixini boshqaradi;
 *  - har yangi sahifa tepadan boshlanadi.
 * Oddiy brauzerda hech narsa qilmaydi.
 */
export default function TelegramBackButton() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isTelegramApp()) return;
    document.documentElement.classList.add("tg-app");
    window.scrollTo(0, 0);

    const wa = getWebApp();
    if (!wa) return;
    try {
      wa.setHeaderColor(HEADER_COLOR);
      wa.setBackgroundColor(BG_COLOR);
    } catch {
      /* eski Telegram versiyalari — muhim emas */
    }

    const back = () => router.back();
    if (ROOTS.has(pathname)) {
      wa.BackButton.hide();
      return;
    }
    wa.BackButton.show();
    wa.BackButton.onClick(back);
    return () => wa.BackButton.offClick(back);
  }, [pathname, router]);

  return null;
}
