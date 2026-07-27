import { clsx } from "clsx";

/**
 * Safarim.uz logotipi — carpooling belgisi (bog'lovchi S-egri + yashil nuqta)
 * gradient ko'k/indigo kvadratda. Navbar va Footer'da ishlatiladi.
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
  const radius = Math.round(size * 0.29);
  const icon = Math.round(size * 0.6);

  return (
    <span className={clsx("flex items-center gap-2.5 shrink-0", className)}>
      <span
        className="flex items-center justify-center shrink-0"
        style={{
          width: size,
          height: size,
          borderRadius: radius,
          background: "linear-gradient(145deg, #4c6ef0, #2b3a9e)",
          boxShadow: "0 4px 12px -3px rgb(59 91 219 / 0.5)",
        }}
      >
        <svg width={icon} height={icon} viewBox="0 0 48 48" fill="none" aria-hidden="true">
          <path
            d="M33 13C33 6.5 15 6.5 15 15C15 23 33 25 33 33C33 41 15 41 15 35"
            stroke="white"
            strokeWidth="4.6"
            strokeLinecap="round"
            fill="none"
          />
          <circle cx="33" cy="13" r="4.2" fill="white" />
          <circle cx="15" cy="35" r="4.2" fill="#5fe0a0" />
        </svg>
      </span>
      {showText && (
        <span className={clsx("font-extrabold tracking-tight text-gray-900", textSize)}>
          Safarim<span className="text-accent-500">.uz</span>
        </span>
      )}
    </span>
  );
}
