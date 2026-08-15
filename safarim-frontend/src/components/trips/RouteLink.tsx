"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRegions } from "@/hooks/useRegions";

interface RouteLinkProps {
  fromSlug: string;
  toSlug: string;
  className?: string;
  children: React.ReactNode;
}

/** Bugungi sana "YYYY-MM-DD" (mahalliy vaqt bo'yicha) */
function todayISO() {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/**
 * Bosh sahifadagi tayyor yo'nalish havolasi ("Toshkent → Samarqand").
 *
 * Qidiruv sahifasi `from_id`/`to_id`/`date` kutadi — shuning uchun viloyat ID lari
 * slug bo'yicha topiladi. Viloyatlar yuklanmaguncha (va SSR da) oddiy `/trips`
 * qoladi: shu bilan hydration mos keladi va sana server/mijoz vaqt mintaqasi
 * farqidan buzilmaydi.
 */
export default function RouteLink({ fromSlug, toSlug, className, children }: RouteLinkProps) {
  const { data: regions } = useRegions();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  let href = "/trips";
  if (mounted && regions) {
    const from = regions.find((r) => r.slug === fromSlug);
    const to = regions.find((r) => r.slug === toSlug);
    if (from && to) {
      href = `/trips?${new URLSearchParams({
        from_id: String(from.id),
        to_id: String(to.id),
        from_name: from.name_uz,
        to_name: to.name_uz,
        date: todayISO(),
        seats: "1",
      })}`;
    }
  }

  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
