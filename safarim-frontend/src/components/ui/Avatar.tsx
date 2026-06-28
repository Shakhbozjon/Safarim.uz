import { clsx } from "clsx";
import Image from "next/image";

type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

interface AvatarProps {
  src?: string | null;
  name?: string;
  size?: AvatarSize;
  online?: boolean;
  className?: string;
}

const sizeMap: Record<AvatarSize, { box: string; text: string; badge: string }> = {
  xs: { box: "w-6 h-6",  text: "text-xs",    badge: "w-2 h-2 border" },
  sm: { box: "w-8 h-8",  text: "text-xs",    badge: "w-2.5 h-2.5 border" },
  md: { box: "w-10 h-10", text: "text-sm",   badge: "w-3 h-3 border-2" },
  lg: { box: "w-14 h-14", text: "text-base", badge: "w-3.5 h-3.5 border-2" },
  xl: { box: "w-20 h-20", text: "text-xl",   badge: "w-4 h-4 border-2" },
};

const COLORS = [
  "bg-blue-500", "bg-violet-500", "bg-emerald-500", "bg-amber-500",
  "bg-pink-500",  "bg-cyan-500",   "bg-indigo-500",  "bg-teal-500",
];

function initials(name?: string) {
  if (!name) return "?";
  const parts = name.trim().split(" ");
  return parts.length === 1
    ? parts[0][0].toUpperCase()
    : (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function colorFor(name?: string) {
  if (!name) return COLORS[0];
  return COLORS[name.charCodeAt(0) % COLORS.length];
}

export default function Avatar({ src, name, size = "md", online, className }: AvatarProps) {
  const s = sizeMap[size];
  return (
    <div className={clsx("relative shrink-0", s.box, className)}>
      {src ? (
        <Image
          src={src}
          alt={name ?? "Avatar"}
          fill
          className="rounded-full object-cover"
          sizes="80px"
        />
      ) : (
        <div
          className={clsx(
            "w-full h-full rounded-full flex items-center justify-center text-white font-semibold select-none",
            s.text,
            colorFor(name)
          )}
        >
          {initials(name)}
        </div>
      )}
      {online !== undefined && (
        <span
          className={clsx(
            "absolute bottom-0 right-0 rounded-full border-white",
            s.badge,
            online ? "bg-green-500" : "bg-gray-300"
          )}
        />
      )}
    </div>
  );
}
