import { clsx } from "clsx";
import { Star } from "lucide-react";

interface StarsProps {
  rating: number;
  max?: number;
  size?: number;
  showValue?: boolean;
  count?: number;
  className?: string;
}

export default function Stars({
  rating,
  max = 5,
  size = 14,
  showValue = false,
  count,
  className,
}: StarsProps) {
  return (
    <div className={clsx("inline-flex items-center gap-1", className)}>
      <div className="flex items-center gap-0.5">
        {Array.from({ length: max }).map((_, i) => (
          <Star
            key={i}
            size={size}
            className={clsx(
              i < Math.floor(rating)
                ? "fill-yellow-400 text-yellow-400"
                : i < rating
                ? "fill-yellow-200 text-yellow-400"
                : "fill-gray-100 text-gray-300"
            )}
          />
        ))}
      </div>
      {showValue && (
        <span className="text-sm font-semibold text-gray-900 leading-none tabular-nums">
          {rating.toFixed(1)}
        </span>
      )}
      {count !== undefined && (
        <span className="text-xs text-gray-400">({count})</span>
      )}
    </div>
  );
}
