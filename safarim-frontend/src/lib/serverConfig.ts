/**
 * Serverda (SSR) o'qiladigan ochiq sozlamalar.
 *
 * `NEXT_PUBLIC_API_URL` brauzer uchun nisbiy yo'l ("/api/v1") — server
 * komponentidan unga murojaat qilib bo'lmaydi, shuning uchun ichki manzil
 * ishlatiladi (compose tarmog'ida `http://api:8000`).
 *
 * API javob bermasa sahifa baribir chiziladi: bunday holatda komissiya bor
 * deb ko'rsatiladi — bu shartnomadagi (terms) holat, ya'ni xato tomonga
 * og'ish yo'lovchini ham, haydovchini ham chalg'itmaydi.
 */
export interface PublicConfig {
  commissionFree: boolean;
}

export async function getPublicConfig(): Promise<PublicConfig> {
  const base = process.env.INTERNAL_API_URL || "http://localhost:8000";

  try {
    const res = await fetch(`${base}/api/v1/config`, {
      cache: "no-store",
      // Osilib qolgan API bosh sahifani ushlab turmasin
      signal: AbortSignal.timeout(1500),
    });
    if (!res.ok) return { commissionFree: false };

    const data = (await res.json()) as { commission_free?: boolean };
    return { commissionFree: !!data.commission_free };
  } catch {
    return { commissionFree: false };
  }
}
