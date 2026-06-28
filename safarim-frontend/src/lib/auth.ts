import Cookies from "js-cookie";
import api from "./api";
import type { TokenResponse, User } from "@/types";

export function saveTokens(tokens: TokenResponse) {
  Cookies.set("access_token", tokens.access_token, { expires: 1 });       // 1 kun
  Cookies.set("refresh_token", tokens.refresh_token, { expires: 30 });    // 30 kun
}

export function clearTokens() {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
}

export function isAuthenticated(): boolean {
  return !!Cookies.get("access_token");
}

export async function getMe(): Promise<User> {
  const { data } = await api.get("/auth/me");
  return data;
}

export function formatPhone(raw: string): string {
  // 901234567 → +998901234567
  const digits = raw.replace(/\D/g, "");
  if (digits.startsWith("998")) return `+${digits}`;
  return `+998${digits}`;
}

export function getApiError(error: any): string {
  const detail = error?.response?.data?.detail;
  if (!detail) return "Xatolik yuz berdi. Qaytadan urinib ko'ring.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => d.msg).join(", ");
  return "Xatolik yuz berdi.";
}
