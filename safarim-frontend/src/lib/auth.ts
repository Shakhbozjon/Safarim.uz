import Cookies from "js-cookie";
import api from "./api";
import type { User } from "@/types";
import { toE164 } from "./phone";

// Token cookie'lari `tokens.ts` da — import halqasi bo'lmasin uchun
export { saveTokens, clearTokens, getAccessToken } from "./tokens";

export function isAuthenticated(): boolean {
  return !!Cookies.get("access_token");
}

export async function getMe(): Promise<User> {
  const { data } = await api.get("/auth/me");
  return data;
}

export function formatPhone(raw: string): string {
  // 901234567 → +998901234567. Kod, bo'sh joy, "0"/"8" prefiksi — hammasi
  // `normalizePhoneInput` da tozalanadi (qarang: lib/phone.ts).
  return toE164(raw);
}

export function getApiError(error: any): string {
  const detail = error?.response?.data?.detail;
  if (!detail) return "Xatolik yuz berdi. Qaytadan urinib ko'ring.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => d.msg).join(", ");
  return "Xatolik yuz berdi.";
}
