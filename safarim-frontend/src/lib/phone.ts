/** Telefon raqam kiritishni bir joyga yig'adi.
 *
 *  Maydonda "+998" doim ko'rinib turadi, shuning uchun foydalanuvchi faqat
 *  9 ta raqam yozishi kerak. Lekin amalda u kodni ham yozadi, Android'da
 *  avtoto'ldirish "+998 99 123 45 67" ko'rinishida bo'sh joylar bilan
 *  qo'yadi, kimdir "0" yoki "8" bilan boshlaydi. Ilgari bularning hammasi
 *  "noto'g'ri raqam" degan xatoga olib kelardi — endi kiritish paytida
 *  o'zi tozalanadi. */

/** Kiritilgan matnni 9 xonali mahalliy raqamga keltiradi: "+998 99 123 45 67",
 *  "0991234567", "8991234567" → "991234567". To'liq bo'lmasa — bor qismini
 *  qaytaradi (kiritish davom etayotgan bo'lishi mumkin). */
export function normalizePhoneInput(raw: string): string {
  let digits = raw.replace(/\D/g, "");

  // Kod/shahar prefiksi faqat raqam 9 tadan oshganda olib tashlanadi:
  // "998123456" ning o'zi ham haqiqiy mahalliy raqam (99 kodi), uni
  // kesib yuborish mumkin emas.
  if (digits.length > 9) {
    if (digits.startsWith("998")) digits = digits.slice(3);
    else if (digits.startsWith("0") || digits.startsWith("8")) digits = digits.slice(1);
  }

  return digits.slice(0, 9);
}

/** Raqam to'liq (9 xonali) kiritilganmi. */
export function isCompletePhone(raw: string): boolean {
  return normalizePhoneInput(raw).length === 9;
}

/** "901234567" → "+998901234567" (backend kutadigan format). */
export function toE164(raw: string): string {
  return `+998${normalizePhoneInput(raw)}`;
}

/** "901234567" → "+998 90 123-45-67". To'liq bo'lmasa null. */
export function prettyPhone(raw: string): string | null {
  const d = normalizePhoneInput(raw);
  if (d.length !== 9) return null;
  return `+998 ${d.slice(0, 2)} ${d.slice(2, 5)}-${d.slice(5, 7)}-${d.slice(7, 9)}`;
}

export const PHONE_ERROR = "Telefon raqamni to'liq kiriting — 9 ta raqam";
