import axios, { AxiosError } from "axios";
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./tokens";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Har so'rovga token qo'shish
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 bo'lsa token yangilash
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as any;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = getRefreshToken();
      if (refresh) {
        try {
          const { data } = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
            { refresh_token: refresh }
          );
          // Backend refresh'da yangi refresh token ham beradi (eskisi bekor
          // qilinishi mumkin) — ikkalasini ham saqlaymiz
          saveTokens(data);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          clearTokens();
          // ⚠️ Ilgari bu yerda "/auth/login" turardi — bunday sahifa yo'q
          // (Next'ning (auth) guruhi manzilga chiqmaydi), ya'ni sessiyasi
          // tugagan odam inglizcha 404 sahifasiga tushardi.
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
