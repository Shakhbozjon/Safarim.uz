import Cookies from "js-cookie";
import type { TokenResponse } from "@/types";

/**
 * Token cookie'lari. Alohida fayl: `api.ts` ham, `auth.ts` ham shundan
 * foydalanadi — aks holda ikkalasi bir-birini import qilib halqa hosil qilardi.
 *
 * `secure` — token faqat HTTPS ulanishda yuboriladi (lokal dev http'da
 * ishlashi uchun shartli). `sameSite: strict` — begona saytdan kelgan
 * so'rovga cookie qo'shilmaydi.
 */
const COOKIE_OPTS = {
  secure: typeof window !== "undefined" && window.location.protocol === "https:",
  sameSite: "strict" as const,
};

/**
 * Serverga "bu odam kirgan" deb aytadigan bayroq — sir emas, token emas.
 *
 * Token cookie'lari `sameSite: strict`: brauzer ularni boshqa saytdan
 * (masalan Telegramdagi havoladan) kelgan BIRINCHI so'rovda yubormaydi.
 * Shu sababli server foydalanuvchini mehmon deb ko'rib, bosh sahifani
 * sotuv matni bilan chizardi — garchi brauzerdagi JS uni kirgan deb
 * ko'rsatib turgan bo'lsa ham. Bu bayroq `lax`, ya'ni bunday o'tishlarda
 * ham keladi va faqat sahifaning qaysi ko'rinishi chizilishini hal qiladi.
 */
const SESSION_FLAG = "uz_session";

/**
 * Telegram Mini App uchun zaxira joy.
 *
 * Telegramning kompyuter va web versiyalari Mini App'ni boshqa sayt ichida
 * (iframe) ochadi — u yerda brauzer bizning cookie'larimizni «begona sayt
 * cookie'si» deb saqlamaydi va kirish har so'rovda yo'qolardi. Shuning uchun
 * Mini App ichida tokenlar `sessionStorage` ga ham yoziladi. Oddiy saytda u
 * bo'sh qoladi — o'qishda faqat cookie bo'lmaganda zaxira sifatida qaraladi.
 */
const TG_KEYS = { access: "tg_access_token", refresh: "tg_refresh_token" };

function inTelegram(): boolean {
  return typeof window !== "undefined" && !!window.Telegram?.WebApp?.initData;
}

function session(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.sessionStorage : null;
  } catch {
    return null;   // ba'zi brauzerlar iframe ichida storage'ni taqiqlaydi
  }
}

export function saveTokens(tokens: TokenResponse) {
  Cookies.set("access_token", tokens.access_token, { expires: 1, ...COOKIE_OPTS });    // 1 kun
  Cookies.set("refresh_token", tokens.refresh_token, { expires: 30, ...COOKIE_OPTS }); // 30 kun
  Cookies.set(SESSION_FLAG, "1", {
    expires: 30,
    secure: COOKIE_OPTS.secure,
    sameSite: "lax",
  });
  if (inTelegram()) {
    try {
      session()?.setItem(TG_KEYS.access, tokens.access_token);
      session()?.setItem(TG_KEYS.refresh, tokens.refresh_token);
    } catch {
      /* storage yopiq — cookie bilan qoladi */
    }
  }
}

export function clearTokens() {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
  Cookies.remove(SESSION_FLAG);
  try {
    session()?.removeItem(TG_KEYS.access);
    session()?.removeItem(TG_KEYS.refresh);
  } catch {
    /* e'tiborsiz */
  }
}

function fromSession(key: string): string | undefined {
  try {
    return session()?.getItem(key) ?? undefined;
  } catch {
    return undefined;
  }
}

export function getAccessToken(): string | undefined {
  return Cookies.get("access_token") ?? fromSession(TG_KEYS.access);
}

export function getRefreshToken(): string | undefined {
  return Cookies.get("refresh_token") ?? fromSession(TG_KEYS.refresh);
}
