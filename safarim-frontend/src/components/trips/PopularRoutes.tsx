"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, MapPin } from "lucide-react";
import api from "@/lib/api";
import { isoOf } from "@/lib/date";
import type { PopularRoute } from "@/types";

/**
 * Ommabop yo'nalishlar — qo'lda yozilgan ro'yxat emas, bazadagi kelgusi
 * safarlar bo'yicha (`GET /trips/popular-routes`).
 *
 * Qo'lda yozilgan ro'yxatda havola bosilganda "safar topilmadi" chiqishi
 * mumkin edi. Safar bo'lmasa bu blok umuman ko'rsatilmaydi.
 */

export function routeHref(r: PopularRoute) {
  return `/trips?${new URLSearchParams({
    from_id: String(r.from_region.id),
    to_id: String(r.to_region.id),
    from_name: r.from_region.name_uz,
    to_name: r.to_region.name_uz,
    date: isoOf(new Date()),
    seats: "1",
  })}`;
}

export function usePopularRoutes(limit = 6) {
  return useQuery<PopularRoute[]>({
    queryKey: ["popular-routes", limit],
    queryFn: async () => (await api.get(`/trips/popular-routes?limit=${limit}`)).data,
    staleTime: 5 * 60 * 1000,
  });
}

interface Props {
  /** chips — qidiruv ostidagi ixcham qator; cards — safar soni bilan katakcha */
  variant?: "chips" | "cards";
  limit?: number;
  /** chips uchun: oldiga qo'yiladigan matn ("Mashhur:") */
  label?: string;
  /** cards uchun: bo'lim sarlavhasi — ro'yxat bo'sh bo'lsa u ham chiqmaydi */
  heading?: string;
  headingClassName?: string;
  /** sarlavha yonidagi havola ("Barchasini ko'rish") */
  moreHref?: string;
  className?: string;
  /**
   * Bo'lim o'ramining klassi. Berilsa blok o'zi `<section>` ichida chiqadi —
   * shunda ro'yxat bo'sh bo'lganda o'ram ham yo'qoladi. Sahifada qo'lda
   * yozilgan `<section>` ichiga qo'yilsa, safar bo'lmagan kuni o'sha
   * `<section>` bo'm-bo'sh tasma bo'lib qolardi.
   */
  sectionClassName?: string;
  /** o'ram ichidagi konteyner (sahifadagi boshqa bo'limlar bilan bir xil kenglik) */
  containerClassName?: string;
}

export default function PopularRoutes({
  variant = "chips",
  limit = 6,
  label,
  heading,
  headingClassName,
  moreHref,
  className,
  sectionClassName,
  containerClassName = "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
}: Props) {
  const { data: routes = [] } = usePopularRoutes(limit);

  if (routes.length === 0) return null;

  if (variant === "chips") {
    return (
      <div className={className ?? "flex flex-wrap gap-2 items-center"}>
        {label && <span className="text-[13px] text-gray-500">{label}</span>}
        {routes.map((r) => (
          <Link
            key={`${r.from_region.id}-${r.to_region.id}`}
            href={routeHref(r)}
            className="shrink-0 inline-flex items-center gap-1.5 bg-white border border-gray-200 rounded-full px-3.5 py-2 text-[13px] font-semibold text-gray-600 hover:border-primary-300 hover:text-primary-600 transition-colors"
          >
            <span>{r.from_region.name_uz}</span>
            <ArrowRight size={12} className="text-gray-300" />
            <span>{r.to_region.name_uz}</span>
          </Link>
        ))}
      </div>
    );
  }

  const grid = (
    <div className={className ?? "grid gap-3.5 sm:gap-5 sm:grid-cols-2 lg:grid-cols-3"}>
      {routes.map((r) => (
        <Link
          key={`${r.from_region.id}-${r.to_region.id}`}
          href={routeHref(r)}
          className="bg-white border border-gray-100 rounded-2xl p-5 transition hover:border-primary-200 hover:shadow-card-hover"
        >
          <div className="flex items-center gap-2.5 text-[16.5px] font-bold tracking-tight mb-2 flex-wrap">
            <MapPin size={15} className="text-primary-500 shrink-0" />
            <span>{r.from_region.name_uz}</span>
            <span className="text-gray-300">→</span>
            <span>{r.to_region.name_uz}</span>
          </div>
          <div className="text-[13px] text-gray-500 mb-4 tabular-nums">
            {r.trip_count} ta bo&apos;sh safar
          </div>
          <div className="text-[14px] font-bold text-primary-600">Bo&apos;sh o&apos;rin qidirish →</div>
        </Link>
      ))}
    </div>
  );

  const wrap = (content: ReactNode) =>
    sectionClassName ? (
      <section className={sectionClassName}>
        <div className={containerClassName}>{content}</div>
      </section>
    ) : (
      <>{content}</>
    );

  if (!heading) return wrap(grid);

  return wrap(
    <>
      <div className="flex items-end justify-between gap-5 flex-wrap mb-8 sm:mb-10">
        <h2 className={headingClassName ?? "text-[17px] font-bold text-gray-900"}>{heading}</h2>
        {moreHref && (
          <Link
            href={moreHref}
            className="text-[15px] font-bold text-primary-600 hover:text-primary-700 whitespace-nowrap"
          >
            Barchasini ko&apos;rish →
          </Link>
        )}
      </div>
      {grid}
    </>
  );
}
