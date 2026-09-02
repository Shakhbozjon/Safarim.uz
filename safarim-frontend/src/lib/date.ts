const UZ_MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];

/** Date → "2026-09-03". `toISOString()` UTC'ga o'tkazadi va mahalliy vaqtda
 *  kun siljib ketishi mumkin, shuning uchun qismlardan yig'iladi. */
export function isoOf(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "2026-09-03" → "Bugun" | "Ertaga" | "3-sentabr".
 *
 *  Sana raqam emas, odam tilida ko'rinadi — ko'p hollarda foydalanuvchi
 *  maydonga umuman tegmaydi, chunki sukut qiymati baribir bugun. */
export function dateLabel(iso: string): string {
  if (!iso) return "Bugun";
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (iso === isoOf(today)) return "Bugun";
  if (iso === isoOf(tomorrow)) return "Ertaga";
  const [, m, d] = iso.split("-").map(Number);
  return `${d}-${UZ_MONTHS[m - 1] ?? ""}`;
}
