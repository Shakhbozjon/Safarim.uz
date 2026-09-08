"use client";

import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";

/**
 * Kunlik qatorlar uchun chiziqli grafik — kutubxonasiz, oddiy SVG.
 *
 * Nega kutubxona emas: uchta chiziq uchun recharts/chart.js bundle'ga
 * yuzlab kilobayt qo'shadi va Docker build'ga yana bir bog'liqlik keladi.
 *
 * Kenglik ResizeObserver bilan o'lchanadi va SVG haqiqiy piksel o'lchamida
 * chiziladi — `viewBox` ni cho'zish matnni ham cho'zib, telefonda o'qib
 * bo'lmaydigan qilib qo'yardi.
 */

export interface SeriesDef {
  key: string;
  label: string;
  color: string;
}

interface Props<T extends object> {
  /** Har qator — bitta kun; kalitlari `series[].key` va `xKey` */
  data: readonly T[];
  series: SeriesDef[];
  /** X o'qi uchun maydon nomi (ISO sana) */
  xKey?: string;
  height?: number;
  className?: string;
}

const PAD = { top: 14, right: 74, bottom: 26, left: 34 };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  return { ref, width };
}

/** "2026-09-08" → "8-sen" */
const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];
function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${Number(d)}-${MONTHS[Number(m) - 1]}`;
}

/** O'qdagi belgilar uchun "chiroyli" qadam (1, 2, 5, 10, 20 …) */
function niceStep(max: number, targetTicks = 4): number {
  const raw = Math.max(max, 1) / targetTicks;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [1, 2, 5, 10]) {
    if (raw <= m * pow) return m * pow;
  }
  return 10 * pow;
}

export default function TrendChart<T extends object>({
  data,
  series,
  xKey = "date",
  height = 240,
  className,
}: Props<T>) {
  /** Qator maydonini o'qish — komponent har qanday qator shakli bilan ishlaydi */
  const num = (row: T, key: string) => Number((row as Record<string, unknown>)[key]) || 0;
  const str = (row: T, key: string) => String((row as Record<string, unknown>)[key] ?? "");
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const innerW = Math.max(width - PAD.left - PAD.right, 10);
  const innerH = height - PAD.top - PAD.bottom;

  const rawMax = Math.max(
    1,
    ...data.flatMap((d) => series.map((s) => num(d, s.key)))
  );
  const step = niceStep(rawMax);
  const yMax = Math.ceil(rawMax / step) * step;

  const x = (i: number) => (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW);
  const y = (v: number) => innerH - (v / yMax) * innerH;

  const ticks: number[] = [];
  for (let v = 0; v <= yMax; v += step) ticks.push(v);

  const handleMove = (clientX: number, target: SVGSVGElement) => {
    const box = target.getBoundingClientRect();
    const px = clientX - box.left - PAD.left;
    if (data.length === 0) return;
    const idx = Math.round((px / innerW) * (data.length - 1));
    setHover(Math.min(Math.max(idx, 0), data.length - 1));
  };

  const point = hover !== null ? data[hover] : null;

  return (
    <div ref={ref} className={clsx("relative w-full", className)}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Kunlik ko'rsatkichlar: ${series.map((s) => s.label).join(", ")}`}
          onMouseMove={(e) => handleMove(e.clientX, e.currentTarget)}
          onMouseLeave={() => setHover(null)}
          onTouchStart={(e) => handleMove(e.touches[0].clientX, e.currentTarget)}
          onTouchMove={(e) => handleMove(e.touches[0].clientX, e.currentTarget)}
          onTouchEnd={() => setHover(null)}
          className="touch-pan-y"
        >
          <g transform={`translate(${PAD.left},${PAD.top})`}>
            {/* To'r — orqa fonda qoladi, o'qishga xalaqit bermaydi */}
            {ticks.map((t) => (
              <g key={t}>
                <line x1={0} x2={innerW} y1={y(t)} y2={y(t)} stroke="#f1f2f4" strokeWidth={1} />
                <text x={-8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-gray-400 text-[10px]">
                  {t}
                </text>
              </g>
            ))}

            {/* Sana belgilari — boshi, o'rtasi, oxiri (siqilib ketmasin) */}
            {[0, Math.floor((data.length - 1) / 2), data.length - 1]
              .filter((i, k, arr) => i >= 0 && arr.indexOf(i) === k)
              .map((i) => (
                <text
                  key={i}
                  x={x(i)}
                  y={innerH + 17}
                  textAnchor={i === 0 ? "start" : i === data.length - 1 ? "end" : "middle"}
                  className="fill-gray-400 text-[10px]"
                >
                  {shortDate(str(data[i], xKey))}
                </text>
              ))}

            {/* Kursor chizig'i */}
            {hover !== null && (
              <line
                x1={x(hover)}
                x2={x(hover)}
                y1={0}
                y2={innerH}
                stroke="#cbd0d8"
                strokeWidth={1}
                strokeDasharray="3 3"
              />
            )}

            {/* Chiziqlar */}
            {series.map((s) => {
              const d = data
                .map((row, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(num(row, s.key))}`)
                .join(" ");
              const lastRow = data[data.length - 1];
              const lastVal = lastRow ? num(lastRow, s.key) : 0;
              return (
                <g key={s.key}>
                  <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                  {/* Oxirgi nuqtada to'g'ridan-to'g'ri yorliq: rang bilan bir
                      qatorda matn ham identifikatsiya beradi */}
                  <circle cx={x(data.length - 1)} cy={y(lastVal)} r={3.5} fill={s.color} stroke="#fff" strokeWidth={2} />
                  <text
                    x={x(data.length - 1) + 9}
                    y={y(lastVal)}
                    dy="0.32em"
                    className="fill-gray-500 text-[10px] font-semibold"
                  >
                    {s.label.split(" ")[0]}
                  </text>
                  {hover !== null && (
                    <circle
                      cx={x(hover)}
                      cy={y(num(data[hover], s.key))}
                      r={4}
                      fill={s.color}
                      stroke="#fff"
                      strokeWidth={2}
                    />
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      )}

      {/* Tooltip */}
      {point && (
        <div
          className="pointer-events-none absolute z-10 rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-lg"
          style={{
            left: Math.min(Math.max(PAD.left + x(hover!) - 60, 0), Math.max(width - 130, 0)),
            top: 4,
          }}
        >
          <p className="mb-1 text-[11px] font-semibold text-gray-500">
            {shortDate(str(point, xKey))}
          </p>
          {series.map((s) => (
            <p key={s.key} className="flex items-center gap-1.5 text-[12px] text-gray-700">
              <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
              {s.label}
              <span className="ml-auto font-semibold tabular-nums">{num(point, s.key)}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
