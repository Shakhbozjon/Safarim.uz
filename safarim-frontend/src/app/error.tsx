"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

/**
 * Kutilmagan xato ushlanadigan joy. Busiz sahifadagi har qanday xato
 * Next'ning inglizcha "Application error" ekranini chiqarardi — foydalanuvchi
 * nima qilishni bilmay qolardi.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Konsolda qoladi — Sentry ulangach o'sha ham oladi
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <AlertTriangle size={30} className="text-red-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Nimadir noto&apos;g&apos;ri ketdi</h1>
        <p className="text-[15px] text-gray-500 mb-7">
          Sahifani ochib bo&apos;lmadi. Qaytadan urinib ko&apos;ring — takrorlansa,
          bizga yozing.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-primary-500 text-white font-semibold hover:bg-primary-600 transition-colors"
          >
            Qaytadan urinish
          </button>
          <Link
            href="/support"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-gray-100 text-gray-800 font-semibold hover:bg-gray-200 transition-colors"
          >
            Bizga yozish
          </Link>
        </div>
      </div>
    </div>
  );
}
