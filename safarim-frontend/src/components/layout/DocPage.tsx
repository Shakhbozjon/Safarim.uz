import type { ReactNode } from "react";

/** Hujjat/matn sahifаlari uchun umumiy tuzilma (Terms, Privacy, Cookies). */
export function DocPage({
  title,
  updated,
  intro,
  children,
}: {
  title: string;
  updated?: string;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <h1 className="text-[clamp(28px,4.4vw,40px)] font-extrabold tracking-[-0.03em] text-gray-900 text-balance">
        {title}
      </h1>
      {updated && (
        <p className="text-[13.5px] text-gray-400 mt-3">Oxirgi yangilanish: {updated}</p>
      )}
      {intro && (
        <p className="text-[16px] leading-relaxed text-gray-500 mt-5 max-w-[640px]">{intro}</p>
      )}
      <div className="mt-9 space-y-8">{children}</div>
    </div>
  );
}

/** Hujjat ichidagi bo'lim: sarlavha + matn/ro'yxat. */
export function DocSection({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="text-[19px] sm:text-[21px] font-bold tracking-tight text-gray-900 mb-2.5">
        {heading}
      </h2>
      <div className="text-[15.5px] leading-relaxed text-gray-600 space-y-2.5">{children}</div>
    </section>
  );
}

/** Belgilangan ro'yxat. */
export function DocList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2 pl-1">
      {items.map((it, i) => (
        <li key={i} className="flex gap-2.5">
          <span className="mt-2 w-1.5 h-1.5 rounded-full bg-primary-400 shrink-0" />
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}
