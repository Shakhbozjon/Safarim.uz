import Link from "next/link";

export const metadata = { title: "Blog — UzSafar" };

export default function BlogPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary-50 flex items-center justify-center mx-auto mb-6 text-3xl">
        ✍️
      </div>
      <h1 className="text-[clamp(26px,4vw,36px)] font-extrabold tracking-[-0.03em] text-gray-900 mb-3 text-balance">
        Blog tez orada
      </h1>
      <p className="text-[16px] leading-relaxed text-gray-500 max-w-[460px] mx-auto mb-8">
        Safar maslahatlari, yo'nalishlar bo'yicha qo'llanmalar va platforma yangiliklari — tez
        orada shu yerda. Hozircha safarni boshlashingiz mumkin.
      </p>
      <div className="flex gap-2.5 justify-center flex-wrap">
        <Link href="/trips" className="bg-primary-500 hover:bg-primary-600 text-white px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] shadow-primary-glow transition-colors">
          Safar qidirish
        </Link>
        <Link href="/how-it-works" className="bg-white text-gray-900 border border-gray-200 px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] hover:bg-gray-50 transition-colors">
          Qanday ishlaydi
        </Link>
      </div>
    </div>
  );
}
