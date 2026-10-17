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
  MainButton: {
    setText(text: string): void;
    show(): void;
    hide(): void;
    onClick(cb: () => void): void;
    offClick(cb: () => void): void;
  };
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
}

/**
 * Mini App ichida ochilganmi — `/tg` kirgizgach shu tabda eslab qolinadi.
 * Telegram skripti faqat `/tg` da yuklanadi; sahifa to'liq qayta yuklansa
 * obyekt yo'qoladi, lekin ko'rinish (sarlavhasiz) saqlanib qolishi kerak.
 */
const TG_FLAG = "tg_app";

export function markTelegramApp() {
  try {
    sessionStorage.setItem(TG_FLAG, "1");
  } catch {
    /* storage yopiq — faqat shu sahifa davomida */
  }
}

export function isTelegramApp(): boolean {
  if (getWebApp()) return true;
  try {
    return typeof window !== "undefined" && sessionStorage.getItem(TG_FLAG) === "1";
  } catch {
    return false;
  }
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
