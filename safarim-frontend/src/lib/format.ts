// Narx: "120 000" — `Intl.NumberFormat("uz-UZ")` brauzerga qarab vergul
// qo'yib yuboradi, shuning uchun uch xonali guruhlarni o'zimiz ajratamiz.
// Ajratgich — uzilmaydigan probel: raqam satr oxirida bo'linib ketmasin.
const NBSP = " ";

export function formatPrice(n: number): string {
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
}
