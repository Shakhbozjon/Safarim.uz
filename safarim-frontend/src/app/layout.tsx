import type { Metadata, Viewport } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-manrope",
});

const SITE_URL = "https://uzsafar.uz";
const TITLE = "UzSafar — O'zbekiston bo'ylab arzon safar";
const DESCRIPTION =
  "Haydovchini o'zingiz tanlaysiz: ismi, reytingi, mashinasi va narxi oldindan ko'rinadi. 14 viloyat bo'ylab hamroh safar.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: TITLE,
  description: DESCRIPTION,
  // Havola Telegram yoki ijtimoiy tarmoqqa tashlanganda ko'rinadigan karta.
  // Busiz havola quruq matn bo'lib chiqardi — O'zbekistonda tarqatishning
  // asosiy yo'li Telegram bo'lgani uchun bu sezilarli farq.
  openGraph: {
    type: "website",
    locale: "uz_UZ",
    url: SITE_URL,
    siteName: "UzSafar",
    title: TITLE,
    description: DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
  alternates: { canonical: SITE_URL },
};

export const viewport: Viewport = {
  themeColor: "#3b5bdb",
};

// Bu auth-gated interaktiv app — statik prerender o'rniga dinamik (SSR) render.
// useSearchParams / client-only logikadagi prerender xatolarini bartaraf etadi.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz">
      <body className={`${manrope.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
