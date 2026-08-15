import { clsx } from "clsx";

interface SeatIndicatorProps {
  totalSeats: number;
  availableSeats: number;
  size?: "sm" | "md";
  className?: string;
}

/**
 * Safardagi joylarni nuqtalar bilan ko'rsatadi:
 * to'ldirilgan (yashil) — bo'sh joy, kulrang — allaqachon band qilingan joy.
 * Yo'lovchi 4 joydan nechtasi band bo'lganini bir qarashda ko'radi.
 */
export default function SeatIndicator({
  totalSeats,
  availableSeats,
  size = "md",
  className,
}: SeatIndicatorProps) {
  const free = Math.max(0, Math.min(availableSeats, totalSeats));
  const booked = Math.max(0, totalSeats - free);
  const dot = size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";

  return (
    <div
      className={clsx("flex items-center gap-2 min-w-0", className)}
      title={`${totalSeats} joydan ${booked} tasi band, ${free} tasi bo'sh`}
    >
      <div className="flex items-center gap-1 shrink-0">
        {Array.from({ length: totalSeats }, (_, i) => (
          <span
            key={i}
            className={clsx(
              "rounded-full shrink-0",
              dot,
              i < free ? "bg-accent-500" : "bg-gray-300"
            )}
          />
        ))}
      </div>
      <span
        className={clsx(
          "truncate tabular-nums",
          size === "sm" ? "text-xs" : "text-sm",
          free === 0 ? "text-gray-400" : "text-gray-600"
        )}
      >
        <span className={clsx("font-semibold", free > 0 && free <= 2 && "text-primary-600")}>
          {free} bo'sh
        </span>
        {booked > 0 && <span className="text-gray-400"> · {booked} band</span>}
      </span>
    </div>
  );
}
