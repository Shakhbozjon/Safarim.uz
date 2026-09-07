import type { MetadataRoute } from "next";

const BASE = "https://uzsafar.uz";

/**
 * Qidiruv tizimlari uchun. Shaxsiy bo'limlar (profil, xabarlar, admin)
 * indekslanmasin — qolgani ochiq.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin", "/profile", "/messages", "/my-trips", "/driver", "/notifications"],
    },
    sitemap: `${BASE}/sitemap.xml`,
  };
}
