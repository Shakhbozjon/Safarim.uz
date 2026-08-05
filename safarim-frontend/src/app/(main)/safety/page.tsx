import Link from "next/link";

export const metadata = { title: "Xavfsizlik — Safarim.uz" };

const FEATURES = [
  { title: "Tasdiqlangan haydovchilar", desc: "Har bir haydovchi haydovchilik guvohnomasi va avtomobil ma'lumotlari bo'yicha admin tekshiruvidan o'tadi." },
  { title: "Reyting va sharhlar", desc: "Har safardan keyin yo'lovchi va haydovchi bir-birini baholaydi. Past reyting profilга ta'sir qiladi." },
  { title: "Telefon raqam himoyasi", desc: "Raqamlar faqat bron tasdiqlangач ikkinchi tomonга ochiladi — ochiq ko'rinmaydi." },
  { title: "Ikki tomonlama tasdiq", desc: "Safar bo'lgani ikkala tomon tomonidan tasdiqlanadi. Kelishmovchilik bo'lsa admin hal qiladi." },
  { title: "Soxtalikка qarshi", desc: "Soxta safar belgilash aniqlansa, haydovchi ogohlantiriladi va takroriy holatда e'lonlari vaqtincha yashiriladi." },
  { title: "Nizolarni hal qilish", desc: "Har qanday nizo admin ko'rigi orqали adolatli hal qilinadi." },
];

const TIPS = [
  "Safardan oldin haydovchi profili va reytingini ko'rib chiqing.",
  "Uchrashuv joyi va vaqtни oldindan aniq kelishing.",
  "Shubhali holatда safarni bekor qiling va bizga xabar bering.",
  "Safar yakunida tasdiqlash va baho berishni unutmang.",
];

export default function SafetyPage() {
  return (
    <div>
      {/* HERO */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-20 pb-6 sm:pb-10">
        <div className="inline-flex items-center gap-2 bg-accent-50 text-accent-700 text-[12.5px] font-bold px-3.5 py-1.5 rounded-full mb-5">
          Xavfsizlik birinchi o'rinda
        </div>
        <h1 className="text-[clamp(30px,4.8vw,44px)] font-extrabold tracking-[-0.035em] text-gray-900 mb-4 text-balance max-w-[680px]">
          Har bir safar nazorat ostida
        </h1>
        <p className="text-[clamp(16px,1.6vw,17.5px)] leading-relaxed text-gray-500 max-w-[600px]">
          Sizning xavfsizligingiz — bizning ustuvor vazifamiz. Platforma tasdiqlash, reyting va
          himoya mexanizmlari bilan har bir safarni ishonchli qiladi.
        </p>
      </section>

      {/* FEATURES */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        <div className="grid gap-4 sm:gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-white border border-gray-100 rounded-[18px] p-6 sm:p-7">
              <h3 className="text-[17.5px] font-bold tracking-tight text-gray-900 mb-2">{f.title}</h3>
              <p className="text-[15px] text-gray-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* TIPS */}
      <section className="bg-gray-50 border-y border-gray-100 py-14 sm:py-20">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-[clamp(22px,3.4vw,30px)] font-extrabold tracking-tight text-gray-900 mb-6">
            Xavfsiz safar uchun maslahatlar
          </h2>
          <div className="space-y-3">
            {TIPS.map((t, i) => (
              <div key={i} className="flex gap-3 bg-white border border-gray-100 rounded-[14px] p-4">
                <span className="w-6 h-6 rounded-full bg-primary-50 text-primary-700 text-[13px] font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                <span className="text-[15px] text-gray-600 leading-relaxed">{t}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 sm:py-20 text-center">
        <p className="text-gray-500 text-base mb-6">Savol yoki muammo bo'lsa, biz bilan bog'laning: <span className="font-semibold text-gray-700">info@safarim.uz</span></p>
        <Link href="/trips" className="inline-block bg-primary-500 hover:bg-primary-600 text-white px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] shadow-primary-glow transition-colors">
          Safar qidirish
        </Link>
      </section>
    </div>
  );
}
