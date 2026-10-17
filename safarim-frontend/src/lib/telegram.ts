/**
 * Telegram Mini App — `telegram-web-app.js` beradigan obyektning kerakli qismi.
 *
 * Skript faqat `/tg` sahifasida yuklanadi. Undan keyin sayt ichida
 * (client-side) yurilganda obyekt saqlanib qoladi; to'liq qayta yuklanishda
 * yo'qoladi — shuning uchun hamma joyda «bo'lmasligi mumkin» deb ishlatiladi.
 */
export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { start_param?: string; user?: { id: number; first_name?: string } };
  ready(): void;
  expand(): void;
  close(): void;
  openTelegramLink(url: string): void;
  BackButton: {
    show(): void;
    hide(): void;
    onClick(cb: () => void): void;
    offClick(cb: () => void): void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

/** Mini App ichidamizmi (va Telegram imzolangan ma'lumot berganmi) */
export function getWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  const wa = window.Telegram?.WebApp;
  return wa && wa.initData ? wa : null;
}
