"use client";

import Link from "next/link";
import { clsx } from "clsx";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { AdminMetric } from "@/types";
import { formatPrice } from "@/lib/format";

interface Props {
  label: string;
  metric?: AdminMetric;
  /** Pul ko'rsatkichi bo'lsa "so'm" qo'shiladi va guruhlanadi */
  money?: boolean;
  /** Ostidagi kichik izoh (masalan "jami 128 ta") */
  hint?: string;
  href?: string;
}

/**
 * Davr ko'rsatkichi: katta raqam + oldingi shuncha kun bilan solishtirish.
 *
 * Faqat "jami" raqam foydasiz edi — u har doim o'sadi va sayt sekinlashganini
 * ko'rsatmaydi. Shuning uchun asosiy raqam DAVR ichidagi qiymat, "jami" esa
 * pastda kichik izoh bo'lib qoladi.
 */
export default function StatTile({ label, metric, money, hint, href }: Props) {
  const value = metric?.period ?? 0;
  const delta = metric?.delta_pct ?? null;

  const body = (
    <div
      className={clsx(
        "rounded-2xl border border-gray-100 bg-white p-4 sm:p-5",
        href && "transition-colors hover:border-primary-200"
      )}
    >
      <p className="text-[13px] text-gray-500">{label}</p>

      {metric === undefined ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded-lg bg-gray-100" />
      ) : (
        <p className={clsx(
          "mt-1 font-bold leading-tight tracking-tight text-gray-900 tabular-nums",
          money ? "text-[21px]" : "text-[26px]"
        )}>
          {money ? formatPrice(value) : value.toLocaleString("ru-RU").replace(/ /g, " ")}
          {money && <span className="ml-1 text-sm font-semibold text-gray-400">so&apos;m</span>}
        </p>
      )}

      <div className="mt-1.5 flex items-center gap-2 text-[12px]">
        {delta === null ? (
          <span className="inline-flex items-center gap-1 text-gray-400">
            <Minus size={12} />
            avvalgi davrda yo&apos;q
          </span>
        ) : (
          <span
            className={clsx(
              "inline-flex items-center gap-0.5 font-semibold",
              delta > 0 ? "text-green-600" : delta < 0 ? "text-red-500" : "text-gray-400"
            )}
          >
            {delta > 0 ? <ArrowUpRight size={13} /> : delta < 0 ? <ArrowDownRight size={13} /> : <Minus size={12} />}
            {Math.abs(delta)}%
          </span>
        )}
        {hint && <span className="whitespace-nowrap text-gray-400">· {hint}</span>}
      </div>
    </div>
  );

  return href ? <Link href={href}>{body}</Link> : body;
}
