import Link from "next/link";

const STATS = [
  { value: "50 000+", label: "Foydalanuvchi" },
  { value: "120 000+", label: "Muvaffaqiyatli safar" },
  { value: "14", label: "Viloyat qamrovi" },
  { value: "4.8 ★", label: "O'rtacha reyting" },
];

const VALUES = [
  { title: "Xavfsizlik", desc: "Har bir haydovchi tekshiriladi, har bir safar reyting bilan nazorat qilinadi." },
  { title: "Qulaylik", desc: "Bir necha soniyada safar toping yoki e'lon joylang — murakkablik yo'q." },
  { title: "Ishonch", desc: "Shaffof narxlar, tasdiqlangan profillar va ochiq sharhlar tizimi." },
];

const H2 = "text-[clamp(24px,3.6vw,34px)] font-extrabold tracking-tight text-gray-900";

export default function AboutPage() {
  return (
    <div>
      {/* HERO */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-20 pb-8 sm:pb-12">
        <div className="max-w-[680px]">
          <div className="inline-flex items-center gap-2 bg-primary-50 text-primary-700 text-[12.5px] font-bold px-3.5 py-1.5 rounded-full mb-5">
            Biz haqimizda
          </div>
          <h1 className="text-[clamp(30px,4.8vw,44px)] font-extrabold tracking-[-0.035em] text-gray-900 mb-5 text-balance">
            Odamlarni yo'lda birlashtiramiz
          </h1>
          <p className="text-[clamp(16px,1.6vw,17.5px)] leading-relaxed text-gray-500">
            UzSafar — O'zbekiston bo'ylab har kuni minglab yo'lovchi va haydovchini bir-biriga
            bog'laydigan carpooling platformasi. Maqsadimiz oddiy: bo'sh o'rindiqlarni yo'qotmaslik,
            yo'l xarajatlarini kamaytirish va viloyatlar orasida safarni har kim uchun qulay qilish.
          </p>
        </div>
      </section>

      {/* STATS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 sm:pb-24">
        <div className="border border-gray-100 bg-white rounded-[18px] p-6 sm:p-9 grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-[clamp(24px,3.2vw,32px)] font-extrabold tracking-tight text-primary-500">{s.value}</div>
              <div className="text-[13.5px] text-gray-500 mt-1.5">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* VALUES */}
      <section className="bg-gray-50 border-t border-gray-100 py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className={H2 + " text-center mb-8 sm:mb-12"}>Qadriyatlarimiz</h2>
          <div className="grid gap-4 sm:gap-6 md:grid-cols-3">
            {VALUES.map((v) => (
              <div key={v.title} className="bg-white border border-gray-100 rounded-[18px] p-7 sm:p-8">
                <h3 className="text-[19px] font-bold tracking-tight text-gray-900 mb-2.5">{v.title}</h3>
                <p className="text-[15px] text-gray-500 leading-relaxed">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20 text-center">
        <h2 className="text-[clamp(23px,3.2vw,30px)] font-extrabold tracking-tight text-gray-900 mb-3">Bizga qo'shiling</h2>
        <p className="text-gray-500 text-base mb-7">Yo'lovchi bo'lib qidiring yoki haydovchi bo'lib daromad qiling.</p>
        <div className="flex gap-2.5 justify-center flex-wrap">
          <Link href="/trips" className="bg-primary-500 hover:bg-primary-600 text-white px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] shadow-primary-glow transition-colors">
            Safar qidirish
          </Link>
          <Link href="/create-trip" className="bg-white text-gray-900 border border-gray-200 px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] hover:bg-gray-50 transition-colors">
            Haydovchi bo'lish
          </Link>
        </div>
      </section>
    </div>
  );
}
