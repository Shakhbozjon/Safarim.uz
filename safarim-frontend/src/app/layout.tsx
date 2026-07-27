import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-manrope",
});

export const metadata: Metadata = {
  title: "Safarim.uz — O'zbekiston bo'ylab arzon safar",
  description: "Haydovchi va yo'lovchilarni bog'lovchi carpooling platformasi",
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
