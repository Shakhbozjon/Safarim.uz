import { clsx } from "clsx";

type BadgeVariant = "default" | "success" | "warning" | "error" | "info" | "orange";
type BadgeSize = "sm" | "md";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  className?: string;
}

export default function Badge({
  children,
  variant = "default",
  size = "md",
  dot = false,
  className,
}: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 font-medium rounded-full",
        size === "sm" ? "px-2.5 py-0.5 text-xs" : "px-3 py-1 text-xs",
        variant === "default" && "bg-gray-100 text-gray-700",
        variant === "success" && "bg-green-50 text-green-700",
        variant === "warning" && "bg-yellow-50 text-yellow-700",
        variant === "error" && "bg-red-50 text-red-700",
        variant === "info" && "bg-blue-50 text-blue-700",
        variant === "orange" && "bg-primary-50 text-primary-700",
        className
      )}
    >
      {dot && (
        <span
          className={clsx(
            "w-1.5 h-1.5 rounded-full shrink-0",
            variant === "default" && "bg-gray-500",
            variant === "success" && "bg-green-500",
            variant === "warning" && "bg-yellow-500",
            variant === "error" && "bg-red-500",
            variant === "info" && "bg-blue-500",
            variant === "orange" && "bg-primary-500"
          )}
        />
      )}
      {children}
    </span>
  );
}
