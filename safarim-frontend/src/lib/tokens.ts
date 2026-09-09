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

export function saveTokens(tokens: TokenResponse) {
  Cookies.set("access_token", tokens.access_token, { expires: 1, ...COOKIE_OPTS });    // 1 kun
  Cookies.set("refresh_token", tokens.refresh_token, { expires: 30, ...COOKIE_OPTS }); // 30 kun
  Cookies.set(SESSION_FLAG, "1", {
    expires: 30,
    secure: COOKIE_OPTS.secure,
    sameSite: "lax",
  });
}

export function clearTokens() {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
  Cookies.remove(SESSION_FLAG);
}

export function getAccessToken(): string | undefined {
  return Cookies.get("access_token");
}

export function getRefreshToken(): string | undefined {
  return Cookies.get("refresh_token");
}
