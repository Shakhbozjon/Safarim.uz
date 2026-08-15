"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, getMe } from "@/lib/auth";

/**
 * Kirgan foydalanuvchini bosh sahifadan o'z paneliga yo'naltiradi:
 * haydovchi → /driver, yo'lovchi → /my-trips.
 *
 * Mehmonga tegmaydi — bosh sahifa SSR bilan o'z holicha ko'rinadi (SEO saqlanadi).
 * Token yaroqsiz bo'lsa ham bosh sahifa ko'rsatiladi.
 */
export default function HomeRedirect({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // Server va mijozda bir xil boshlanadi — hydration mos keladi
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) return;
    setLeaving(true);

    let cancelled = false;
    getMe()
      .then((me) => {
        if (!cancelled) router.replace(me.is_driver ? "/driver" : "/my-trips");
      })
      .catch(() => {
        if (!cancelled) setLeaving(false);
      });

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (leaving) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <span className="w-7 h-7 rounded-full border-2 border-gray-200 border-t-primary-500 animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
