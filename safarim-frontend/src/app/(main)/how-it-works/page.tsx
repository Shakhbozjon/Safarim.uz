import Link from "next/link";

export const metadata = { title: "Qanday ishlaydi — Safarim.uz" };

const PASSENGER = [
  { n: 1, title: "Safar toping", desc: "Qayerdan, qayerga va sanani kiriting. Mavjud safarlar ro'yxatidan eng qulayini tanlang." },
  { n: 2, title: "Joy band qiling", desc: "Haydovchi profili, reytingi va narxini ko'rib, bir tugma bilan joy band qiling." },
  { n: 3, title: "Bog'laning", desc: "Bron tasdiqlangач haydovchining telefon raqami ochiladi — vaqt va uchrashuv joyini kelishing." },
  { n: 4, title: "Yo'lga chiqing", desc: "Safar davomida haydovchiga naqd to'lang. Yetib borgач, safarni tasdiqlang va baho bering." },
];

const DRIVER = [
  { n: 1, title: "Ro'yxatdan o'ting", desc: "Telefon raqamingiz bilan bir daqiqada hisob yarating." },
  { n: 2, title: "Ariza yuboring", desc: "Avtomobil ma'lumotlari va haydovchilik guvohnomasi rasmini yuklang." },
  { n: 3, title: "Tasdiqlashni kuting", desc: "Admin 1–3 ish kuni ichida hujjatlaringizni tekshirib tasdiqlaydi." },
  { n: 4, title: "Safar e'lon qiling", desc: "Yo'nalish, vaqt, narx va bo'sh o'rinlarni kiriting — yo'lovchilar sizni topadi." },
];

const H2 = "text-[clamp(22px,3.4vw,30px)] font-extrabold tracking-tight text-gray-900";

function Steps({ items }: { items: { n: number; title: string; desc: string }[] }) {
  return (
    <div className="grid gap-4 sm:gap-5 sm:grid-cols-2">
      {items.map((s) => (
        <div key={s.n} className="bg-white border border-gray-100 rounded-[18px] p-6 sm:p-7">
          <div
            className="w-11 h-11 rounded-[12px] flex items-center justify-center font-extrabold text-lg text-primary-700 mb-4"
            style={{ background: "linear-gradient(145deg,#eef3fc,#dde6fa)" }}
          >{s.n}</div>
          <h3 className="text-[18px] font-bold tracking-tight text-gray-900 mb-1.5">{s.title}</h3>
          <p className="text-[15px] text-gray-500 leading-relaxed">{s.desc}</p>
        </div>
      ))}
    </div>
  );
}

export default function HowItWorksPage() {
  return (
    <div>
      {/* HERO */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-20 pb-6 sm:pb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-primary-50 text-primary-700 text-[12.5px] font-bold px-3.5 py-1.5 rounded-full mb-5">
          Qanday ishlaydi
        </div>
        <h1 className="text-[clamp(30px,4.8vw,44px)] font-extrabold tracking-[-0.035em] text-gray-900 mb-4 text-balance">
          Bir necha qadamda yo'lga chiqing
        </h1>
        <p className="text-[clamp(16px,1.6vw,17.5px)] leading-relaxed text-gray-500 max-w-[560px] mx-auto">
          Safarim.uz yo'lovchi va haydovchini oddiy, tez va xavfsiz tarzda bog'laydi. Quyida
          ikkala tomon uchun jarayon ko'rsatilган.
        </p>
      </section>

      {/* PASSENGERS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        <h2 className={H2 + " mb-6 sm:mb-8"}>Yo'lovchilar uchun</h2>
        <Steps items={PASSENGER} />
      </section>

      {/* DRIVERS */}
      <section className="bg-gray-50 border-y border-gray-100 py-14 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className={H2 + " mb-6 sm:mb-8"}>Haydovchilar uchun</h2>
          <Steps items={DRIVER} />
        </div>
      </section>

      {/* PAYMENT NOTE */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 sm:py-20">
        <div className="bg-white border border-gray-100 rounded-[18px] p-6 sm:p-8 max-w-[720px]">
          <h2 className="text-[20px] font-bold tracking-tight text-gray-900 mb-2.5">To'lov qanday amalga oshadi?</h2>
          <p className="text-[15.5px] text-gray-500 leading-relaxed">
            Hozircha to'lov <span className="font-semibold text-gray-700">naqd</span> — yo'lovchi
            safar davomida haydovchiga to'g'ridan-to'g'ri to'laydi. Platforma o'z komissiyasini
            (safar narxiga qarab 2–5%) haydovchining oldindan to'ldirilган depozitidan safar
            yakunlangач ushlaydi. Ro'yxatdan o'tish esa mutlaqo bepul.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 sm:pb-24 text-center">
        <h2 className="text-[clamp(22px,3.2vw,28px)] font-extrabold tracking-tight text-gray-900 mb-3">Tayyormisiz?</h2>
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
