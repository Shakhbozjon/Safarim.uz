/**
 * Tasdiq belgisi — hujjati admin tomonidan tekshirilgan haydovchida.
 *
 * Ataylab faqat ikonka: yozuvli nishon safar kartochkasida joy egallaydi va
 * tekshirilmagan haydovchiga nisbatan salbiy yorliqqa aylanadi. Belgi bor —
 * tekshirilgan, yo'q — tekshirilmagan, boshqa hech narsa yozilmaydi.
 *
 * Matn faqat hover va skrinriderga: ko'zga ko'rinadigan yozuv yo'q.
 */
export default function VerifiedBadge({ size = 15 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className="shrink-0"
      role="img"
      aria-label="Hujjati tekshirilgan"
    >
      <title>Hujjati tekshirilgan</title>
      {/* Muhr — brend ko'ki bilan to'ldirilgan */}
      <path
        d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"
        fill="#3b5bdb"
      />
      {/* Ichidagi belgi — oq */}
      <path
        d="m9 12 2 2 4-4"
        fill="none"
        stroke="#fff"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
