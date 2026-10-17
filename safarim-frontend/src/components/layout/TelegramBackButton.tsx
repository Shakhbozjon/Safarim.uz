"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getWebApp } from "@/lib/telegram";

// Bu sahifalardan orqaga yo'l yo'q — Telegramning o'z «yopish» tugmasi qoladi
const ROOTS = new Set(["/", "/tg", "/my-trips", "/driver"]);

/**
 * Mini App ichida Telegramning «← Orqaga» tugmasi sayt tarixini boshqaradi.
 * Oddiy brauzerda hech narsa qilmaydi.
 */
export default function TelegramBackButton() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const wa = getWebApp();
    if (!wa) return;
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
