import Link from "next/link";
import { cookies } from "next/headers";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import MemberStrip from "@/components/layout/MemberStrip";
import HeroSearchCard from "@/components/trips/HeroSearchCard";
import PopularRoutes from "@/components/trips/PopularRoutes";
import { getPublicConfig } from "@/lib/serverConfig";

// Halol faktlar (yolg'on vanity-raqamlar emas) — yangi platforma uchun rost qiymatlar.
// Komissiya raqami serverdagi bayroqdan keladi: bepul davr tugaganda sahifa
// o'zi 2–5% ga qaytadi, hech kim qo'lda tuzatishni eslab qolishi shart emas.
const stats = (commissionFree: boolean) => [
  { value: "14", label: "Viloyat qamrovi" },
  { value: "0%", label: "Ro'yxatdan o'tish to'lovi" },
  commissionFree
    ? { value: "0%", label: "Hozircha komissiya yo'q" }
    : { value: "2–5%", label: "Past komissiya" },
  { value: "Tasdiqlangan", label: "Haydovchilar" },
];

const STEPS = [
  { n: 1, title: "Safar toping", desc: "Shahar va sanani kiriting. Sizga mos safarni tanlang." },
  { n: 2, title: "Joy band qiling", desc: "Haydovchi profili va reytingini ko'rib, xavfsiz joy band qiling." },
  { n: 3, title: "Yo'lga chiqing", desc: "Haydovchi bilan bog'laning va safarni boshlang — arzon, tez va qulay." },
];

const SAFETY = [
  { title: "Tasdiqlangan haydovchilar", desc: "Barcha haydovchilar hujjat tekshiruvi va reyting tizimidan o'tadi." },
  { title: "Reyting va sharhlar", desc: "Har safardan keyin yo'lovchi va haydovchi bir-birini baholaydi." },
  { title: "Raqam himoyasi", desc: "Telefon raqamlar faqat band qilish tasdiqlangandan keyin ko'rinadi." },
];

const earnings = (commissionFree: boolean) => [
  { value: "0%", label: "Ro'yxatdan o'tish to'lovi" },
  commissionFree
    ? { value: "0%", label: "Ishga tushirish davri — komissiya yo'q" }
    : { value: "2–5%", label: "Faqat muvaffaqiyatli band qilishdan" },
  { value: "1–2 kun", label: "Ariza tasdiqlash muddati" },
];

const H2 = "text-[clamp(26px,4vw,38px)] font-extrabold tracking-tight text-gray-900";
const EYEBROW = "text-[12.5px] font-bold uppercase tracking-[0.08em] text-primary-600 mb-3";

export default async function HomePage() {
  // Sahifa hamma uchun bir xil. Tokenni serverda o'qiymiz: kirgan
  // foydalanuvchiga mehmonga atalgan chaqiriqlar ko'rsatilmaydi va tepada
  // shaxsiy qator (salomlashuv + yaqin safar) chiqadi.
  const signedIn = !!cookies().get("access_token");

  const { commissionFree } = await getPublicConfig();
  const STATS = stats(commissionFree);
  const EARNINGS = earnings(commissionFree);

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <Navbar transparent={!signedIn} />
      {signedIn && <MemberStrip />}

      {/* ═══ HERO ═══ */}
      <section className="relative overflow-hidden gradient-hero">
        {/* Mehmonda navbar shaffof — geroy uning tagidan boshlanadi, shuning
            uchun katta yuqori padding. Kirgan foydalanuvchida navbar o'z
            joyini egallaydi, padding kichik bo'lmasa bo'sh chiziq qoladi. */}
        <div
          className={`relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-14 sm:pb-20 grid gap-8 lg:gap-14 items-center lg:grid-cols-2 ${
            signedIn ? "pt-8 sm:pt-12" : "pt-28 sm:pt-32"
          }`}
        >
          {/* Left */}
          <div className="min-w-0">
            <h1 className="text-[clamp(30px,5.6vw,54px)] leading-[1.08] font-extrabold tracking-[-0.035em] text-gray-900 mb-3.5 text-balance">
              Haydovchini<br />o&apos;zingiz tanlaysiz
            </h1>
            {/* Yo'nalish nomi ataylab yozilmagan: sayt 14 viloyatni qamraydi va
                boshqa yo'nalishdan kirgan odam o'zini chetda his qilmasin */}
            <p className="text-[clamp(15.5px,1.6vw,18px)] leading-relaxed text-gray-500 mb-7 max-w-[460px]">
              Qayerdan qayerga — o&apos;zingiz belgilaysiz. Har bir e&apos;londa{" "}
              <b className="font-semibold text-gray-700">
                haydovchining ismi, reytingi, mashinasi va narxi
              </b>{" "}
              ko&apos;rinadi, yoqqanini tanlab joy band qilasiz. Jo&apos;nash vaqti oldindan aniq.
            </p>

            <HeroSearchCard />

            <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3.5 text-[12.5px] font-semibold text-gray-500">
              <span className="inline-flex items-center gap-1.5">
                <i className="w-[5px] h-[5px] rounded-full bg-green-500" />
                Hujjatlari tekshirilgan haydovchilar
              </span>
              <span className="inline-flex items-center gap-1.5">
                <i className="w-[5px] h-[5px] rounded-full bg-green-500" />
                Narx oldindan aniq
              </span>
            </div>

            <PopularRoutes
              variant="chips"
              limit={3}
              label="Mashhur:"
              className="flex flex-wrap gap-2 mt-4 items-center"
            />
          </div>

          {/* Right — floating trip card */}
          <div className="hidden lg:flex justify-center min-w-0">
            <div className="w-full max-w-[420px] relative">
              <div
                className="rounded-[22px] p-7 text-white"
                style={{
                  background: "linear-gradient(158deg,#3f60df,#232f83)",
                  boxShadow: "0 30px 64px -28px rgb(35 48 129 / 0.7)",
                }}
              >
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-[42px] h-[42px] rounded-full bg-white/20 flex items-center justify-center font-extrabold text-sm shrink-0">JR</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[15px] font-bold">Jasur Rahimov</div>
                    <div className="text-[12.5px] opacity-75">4.9 ★ · 127 sharh</div>
                  </div>
                  <span className="text-[11.5px] bg-accent-500 px-2.5 py-1 rounded-full font-bold shrink-0">Tasdiqlangan</span>
                </div>

                <div className="flex items-center gap-3.5 py-5 border-y border-white/20">
                  <div className="flex-1 min-w-0">
                    <div className="text-[22px] font-extrabold tracking-tight">Toshkent</div>
                    <div className="text-[13px] opacity-75">08:00</div>
                  </div>
                  <div className="flex flex-col items-center gap-1 opacity-75 shrink-0">
                    <div className="text-[11px]">3s 30d</div>
                    <div className="w-9 h-px bg-white/50" />
                  </div>
                  <div className="flex-1 min-w-0 text-right">
                    <div className="text-[22px] font-extrabold tracking-tight">Samarqand</div>
                    <div className="text-[13px] opacity-75">11:30</div>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3.5 flex-wrap pt-5">
                  <div>
                    <div className="text-[11.5px] opacity-70 uppercase tracking-wide">Bir o'rin</div>
                    <div className="text-[24px] font-extrabold tracking-tight">45 000 so'm</div>
                  </div>
                  <Link href="/trips" className="bg-white text-primary-700 px-5 py-3 rounded-[11px] font-bold text-[14.5px] shrink-0 hover:bg-gray-50 transition-colors">
                    Joy band qilish
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ STATS ═══ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="border border-gray-100 bg-white rounded-[18px] p-6 sm:p-9 grid grid-cols-2 md:grid-cols-4 gap-6 shadow-card">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-[clamp(26px,3.4vw,34px)] font-extrabold tracking-tight text-primary-500">{s.value}</div>
              <div className="text-[13.5px] text-gray-500 mt-1.5">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ HOW IT WORKS ═══ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 w-full">
        <div className="text-center mb-10 sm:mb-14">
          <div className={EYEBROW}>Qanday ishlaydi</div>
          <h2 className={H2 + " mb-2.5 text-balance"}>3 ta qadamda yo'lga chiqing</h2>
          <p className="text-gray-500 text-base max-w-[440px] mx-auto">Ro'yxatdan o'tishdan safar boshlanishiga qadar bir necha daqiqa</p>
        </div>
        <div className="grid gap-4 sm:gap-6 md:grid-cols-3">
          {STEPS.map((st) => (
            <div key={st.n} className="bg-white border border-gray-100 rounded-[18px] p-7 sm:p-8 transition hover:-translate-y-1 hover:border-primary-200 hover:shadow-card-hover">
              <div
                className="w-[46px] h-[46px] rounded-[13px] flex items-center justify-center font-extrabold text-lg text-primary-700 mb-5"
                style={{ background: "linear-gradient(145deg,#eef3fc,#dde6fa)" }}
              >{st.n}</div>
              <h3 className="text-[19px] font-bold tracking-tight text-gray-900 mb-2">{st.title}</h3>
              <p className="text-[15px] text-gray-500 leading-relaxed">{st.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ ROUTES ═══ */}
      {/* O'ram komponentning o'zida: safar bo'lmagan kuni butun bo'lim
          yo'qoladi. Ilgari bu yerda bo'm-bo'sh kulrang tasma qolardi. */}
      <PopularRoutes
        variant="cards"
        limit={6}
        heading="Mashhur marshrutlar"
        headingClassName={H2}
        moreHref="/trips"
        sectionClassName="bg-gray-50 border-y border-gray-100 py-16 sm:py-24 w-full"
      />

      {/* ═══ SAFETY ═══ */}
      {/* Tepa padding yo'q: oraliqni yuqoridagi bo'lim beradi. Ikkalasida
          ham bo'lsa — marshrutlar tasmasi chiqmagan kuni 128px bo'shliq
          qolardi (pastdagi «Haydovchilar uchun» bloki ham shu sababdan
          faqat `pb`). */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 sm:pb-24 w-full">
        <div className="grid gap-10 lg:gap-14 md:grid-cols-2">
          <div>
            <div className="inline-flex items-center gap-2 bg-accent-50 text-accent-700 text-[12.5px] font-bold px-3.5 py-1.5 rounded-full mb-4">
              Xavfsizlik birinchi o'rinda
            </div>
            <h2 className={H2 + " mb-3.5 text-balance"}>Har bir safar nazorat ostida</h2>
            <p className="text-base text-gray-500 leading-relaxed max-w-[420px]">
              Haydovchi hujjatlari tekshiriladi, profillar tasdiqlanadi va har bir safar reyting bilan baholanadi.
            </p>
          </div>
          <div className="flex flex-col">
            {SAFETY.map((sf) => (
              <div key={sf.title} className="py-5 border-t border-gray-100">
                <h3 className="text-[17.5px] font-bold tracking-tight text-gray-900 mb-2">{sf.title}</h3>
                <p className="text-[15px] text-gray-500 leading-relaxed">{sf.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ DRIVER CTA ═══ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 sm:pb-24 w-full">
        <div
          className="rounded-[24px] p-7 sm:p-14 text-white grid gap-8 lg:gap-12 items-center md:grid-cols-2"
          style={{
            background: "linear-gradient(150deg,#25306e,#3b5bdb)",
            boxShadow: "0 30px 64px -32px rgb(35 48 129 / 0.6)",
          }}
        >
          <div>
            <div className="text-[12.5px] font-bold uppercase tracking-[0.08em] opacity-75 mb-3.5">Haydovchilar uchun</div>
            <h2 className="text-[clamp(24px,3.4vw,34px)] font-extrabold tracking-tight mb-3.5 text-balance">Yo'lingizda pul ishlang</h2>
            <p className="text-base opacity-85 leading-relaxed mb-7 max-w-[420px]">
              Har kuni bir yo'nalishda borasizmi? Yo'lovchi olib boring va qo'shimcha daromad oling.
            </p>
            <div className="flex gap-2.5 flex-wrap">
              <Link href="/profile/driver-apply" className="bg-white text-primary-700 px-6 py-3.5 rounded-[11px] font-bold text-[15px] hover:bg-gray-50 transition-colors">
                Ariza yuborish
              </Link>
              <Link href="/profile/driver-apply" className="bg-white/10 border border-white/25 text-white px-6 py-3.5 rounded-[11px] font-bold text-[15px] hover:bg-white/20 transition-colors">
                Batafsil
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3.5">
            {EARNINGS.map((e) => (
              <div key={e.label} className="bg-white/10 border border-white/15 rounded-[15px] p-4 sm:p-5">
                <div className="text-[clamp(20px,2.6vw,27px)] font-extrabold tracking-tight">{e.value}</div>
                <div className="text-[12px] sm:text-[12.5px] opacity-80 mt-1.5 leading-snug">{e.label}</div>
              </div>
            ))}
          </div>
          {commissionFree && (
            // Kelajakdagi komissiyani oldindan aytib qo'yamiz — bepul davr
            // tugaganda haydovchi uchun kutilmagan bo'lmasin.
            <p className="text-[12.5px] opacity-70 mt-3.5">
              Bepul davr tugagach komissiya 2–5% bo'ladi: 200 000 so&apos;mgacha
              band qilishdan 2%, undan yuqorisidan 5%.
            </p>
          )}
        </div>
      </section>

      {/* ═══ FINAL CTA ═══ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-22 text-center w-full">
        <h2 className="text-[clamp(24px,3.6vw,34px)] font-extrabold tracking-tight text-gray-900 mb-3 text-balance">Bugunoq safarni boshlang</h2>
        <p className="text-gray-500 text-base mb-7">
          {signedIn
            ? "Qayerdan qayerga ketishingizni tanlang — bo'sh o'rinlar kutmoqda."
            : "Ro'yxatdan o'tish bepul — bir daqiqada birinchi safaringizni toping."}
        </p>
        <div className="flex gap-2.5 justify-center flex-wrap">
          <Link href="/trips" className="bg-primary-500 hover:bg-primary-600 text-white px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] shadow-primary-glow transition-colors">
            Safar qidirish
          </Link>
          <Link href="/profile/driver-apply" className="bg-white text-gray-900 border border-gray-200 px-7 py-[15px] rounded-[11px] font-bold text-[15.5px] hover:bg-gray-50 transition-colors">
            Haydovchi bo'lish
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
