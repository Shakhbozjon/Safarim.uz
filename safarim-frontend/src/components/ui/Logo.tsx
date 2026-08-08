import { clsx } from "clsx";

/**
 * UzSafar logotipi — "U" yo'l belgisi (U harfi + ikki nuqtani bog'lovchi yo'l:
 * yashil boshlanish, oq manzil). Dumaloq gradient ko'k/indigo doirada.
 * Navbar va Footer'da ishlatiladi.
 */
export default function Logo({
  size = 38,
  textSize = "text-xl",
  showText = true,
  className,
}: {
  size?: number;
  textSize?: string;
  showText?: boolean;
  className?: string;
}) {
  const icon = Math.round(size * 0.6);

  return (
    <span className={clsx("flex items-center gap-2.5 shrink-0", className)}>
      <span
        className="flex items-center justify-center shrink-0"
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          background: "linear-gradient(145deg, #4c6ef0, #2b3a9e)",
          boxShadow: "0 4px 12px -3px rgb(59 91 219 / 0.5)",
        }}
      >
        <svg width={icon} height={icon} viewBox="0 0 48 48" fill="none" aria-hidden="true">
          <path
            d="M15 13 L15 27 A9 9 0 0 0 33 27 L33 13"
            stroke="white"
            strokeWidth="4.6"
            strokeLinecap="round"
            fill="none"
          />
          <circle cx="15" cy="13" r="4.2" fill="#5fe0a0" />
          <circle cx="33" cy="13" r="4.2" fill="white" />
        </svg>
      </span>
      {showText && (
        <span className={clsx("font-extrabold tracking-tight text-gray-900", textSize)}>
          UzSafar<span className="text-accent-500">.uz</span>
        </span>
      )}
    </span>
  );
}
