import type { MetadataRoute } from "next";

const BASE = "https://uzsafar.uz";

/**
 * Ochiq sahifalar ro'yxati. Safar sahifalari bu yerga qo'shilmaydi: ular tez
 * o'zgaradi va kirish talab qiladi — qidiruvda foydasi yo'q.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const pages = [
    { path: "/", priority: 1 },
    { path: "/trips", priority: 0.9 },
    { path: "/how-it-works", priority: 0.7 },
    { path: "/safety", priority: 0.7 },
    { path: "/about", priority: 0.5 },
    { path: "/support", priority: 0.5 },
    { path: "/terms", priority: 0.3 },
    { path: "/privacy", priority: 0.3 },
    { path: "/cookies", priority: 0.3 },
  ];
  const now = new Date();
  return pages.map((p) => ({
    url: `${BASE}${p.path}`,
    lastModified: now,
    changeFrequency: "weekly" as const,
    priority: p.priority,
  }));
}
