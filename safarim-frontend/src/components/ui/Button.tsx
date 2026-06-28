import { clsx } from "clsx";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  fullWidth?: boolean;
}

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed",
        {
          // Variants
          "bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500 active:bg-primary-700":
            variant === "primary",
          "bg-gray-100 text-gray-800 hover:bg-gray-200 focus:ring-gray-400":
            variant === "secondary",
          "border-2 border-primary-500 text-primary-600 hover:bg-primary-50 focus:ring-primary-500":
            variant === "outline",
          "text-gray-600 hover:bg-gray-100 focus:ring-gray-400":
            variant === "ghost",
          // Sizes
          "px-3 py-1.5 text-sm gap-1.5": size === "sm",
          "px-5 py-2.5 text-sm gap-2": size === "md",
          "px-6 py-3.5 text-base gap-2": size === "lg",
          // Full width
          "w-full": fullWidth,
        },
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="animate-spin" size={16} />}
      {children}
    </button>
  );
}
