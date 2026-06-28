import Link from "next/link";
import { Shield, Star, MapPin, ChevronRight, Users, Car, TrendingUp, UserPlus, FileText, CheckCircle } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import SearchBar from "@/components/trips/SearchBar";
import Button from "@/components/ui/Button";

const POPULAR_ROUTES = [
  { from: "Toshkent", to: "Samarqand", duration: "3s 30d", price: 45_000, tripsPerDay: 24 },
  { from: "Toshkent", to: "Namangan",  duration: "4s 20d", price: 55_000, tripsPerDay: 18 },
  { from: "Toshkent", to: "Buxoro",    duration: "5s 10d", price: 65_000, tripsPerDay: 12 },
  { from: "Samarqand", to: "Buxoro",   duration: "2s 15d", price: 30_000, tripsPerDay: 10 },
  { from: "Toshkent", to: "Farg'ona",  duration: "4s 50d", price: 60_000, tripsPerDay: 16 },
  { from: "Toshkent", to: "Nukus",     duration: "9s",     price: 120_000, tripsPerDay: 6 },
];

const STEPS = [
  {
    icon: MapPin,
    title: "Safar toping",
    desc: "Kerakli shahar va sanani kiriting. Yuzlab safarlar ichidan eng qulayin tanlang.",
    color: "bg-blue-50 text-blue-600",
  },
  {
    icon: Users,
    title: "Joy band qiling",
    desc: "Haydovchi va safar ma'lumotlarini ko'rib, xavfsiz to'lov orqali joy band qiling.",
    color: "bg-primary-50 text-primary-600",
  },
  {
    icon: Car,
    title: "Safaringizni boshlang",
    desc: "Haydovchi bilan bog'laning va yo'lga chiqing. Arzon va qulay safar sizni kutadi!",
    color: "bg-green-50 text-green-600",
  },
];

const TESTIMONIALS = [
  {
    name: "Nodira Karimova",
    city: "Toshkent",
    text: "Har hafta Samarqandga boradigan bo'ldim. Safarim.uz orqali har doim qulay joy topaman va narxi juda qulay!",
    rating: 5,
    initials: "NK",
    color: "bg-violet-500",
  },
  {
    name: "Jasur Rahimov",
    city: "Samarqand",
    desc: "Haydovchi",
    text: "Toshkentga har kuni ketaman. Safarim.uz orqali yo'lovchi topaman va yoqilg'i xarajatimni qoplayman.",
    rating: 5,
    initials: "JR",
    color: "bg-blue-500",
  },
  {
    name: "Malika Yusupova",
    city: "Farg'ona",
    text: "Xavfsiz va qulay. Haydovchilar tasdiqlangan, reyting tizimi bor. Ishonch bilan foydalanaman.",
    rating: 5,
    initials: "MY",
    color: "bg-pink-500",
  },
];

function formatPrice(n: number) {
  return new Intl.NumberFormat("uz-UZ").format(n);
}

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar transparent />

      {/* ═══ HERO ═══════════════════════════════════════════════════════ */}
      <section className="gradient-hero pt-24 pb-16 sm:pt-32 sm:pb-24 relative overflow-hidden">
        {/* Decorative blobs */}
        <div className="absolute -top-20 -right-20 w-96 h-96 bg-primary-100/60 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-10 -left-10 w-72 h-72 bg-primary-50/80 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 bg-white/80 backdrop-blur-sm text-primary-700 text-sm font-medium px-4 py-2 rounded-full border border-primary-100 mb-6 shadow-sm">
            <TrendingUp size={14} />
            O'zbekistondagi #1 carpooling platformasi
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-gray-900 leading-tight tracking-tight mb-5 text-balance">
            O'zbekiston bo'ylab{" "}
            <span className="text-primary-500">qulay safar</span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
            Haydovchi va yo'lovchilarni birlashtiruvchi platforma. Yoqilg'i xarajatini bo'ling, arzon boring.
          </p>

          <div className="max-w-5xl mx-auto">
            <SearchBar />
          </div>

          {/* Quick routes */}
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            {["Toshkent → Samarqand", "Toshkent → Namangan", "Toshkent → Buxoro"].map((route) => (
              <Link
                key={route}
                href={`/trips?from=${route.split(" → ")[0]}&to=${route.split(" → ")[1]}`}
                className="text-sm text-gray-500 hover:text-primary-600 bg-white/70 hover:bg-primary-50 border border-gray-200 hover:border-primary-200 px-4 py-2 rounded-full transition-colors"
              >
                {route}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ STATS ═══════════════════════════════════════════════════════ */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "50,000+", label: "Foydalanuvchi" },
              { value: "120,000+", label: "Muvaffaqiyatli safar" },
              { value: "14", label: "Viloyat qamrovi" },
              { value: "4.8 ★", label: "O'rtacha reyting" },
            ].map(({ value, label }) => (
              <div key={label} className="text-center">
                <p className="text-3xl font-bold text-gray-900 tabular-nums">{value}</p>
                <p className="text-sm text-gray-500 mt-1">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS ═══════════════════════════════════════════════ */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
              Qanday ishlaydi?
            </h2>
            <p className="text-gray-500 text-lg max-w-lg mx-auto">
              3 ta oddiy qadam bilan safaringizni boshlang
            </p>
          </div>

          <div className="grid sm:grid-cols-3 gap-8">
            {STEPS.map(({ icon: Icon, title, desc, color }, i) => (
              <div key={i} className="bg-white rounded-2xl p-8 border border-gray-100 hover:shadow-card-hover transition-shadow text-center relative">
                <div className={`w-14 h-14 rounded-2xl ${color} flex items-center justify-center mx-auto mb-5`}>
                  <Icon size={26} />
                </div>
                <div className="absolute -top-3 -right-3 w-7 h-7 bg-white border border-gray-100 rounded-xl flex items-center justify-center text-xs font-bold text-gray-400 shadow-sm">
                  {i + 1}
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ POPULAR ROUTES ═══════════════════════════════════════════ */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-end justify-between mb-10">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Mashhur yo'nalishlar</h2>
              <p className="text-gray-500">Eng ko'p qidirilgan marshrutlar</p>
            </div>
            <Link href="/trips" className="hidden sm:flex items-center gap-1 text-primary-600 text-sm font-medium hover:gap-2 transition-all">
              Barchasi <ChevronRight size={16} />
            </Link>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {POPULAR_ROUTES.map((route) => (
              <Link
                key={`${route.from}-${route.to}`}
                href={`/trips?from=${route.from}&to=${route.to}`}
                className="group flex items-center justify-between bg-gray-50 hover:bg-primary-50 border border-gray-100 hover:border-primary-200 rounded-2xl px-5 py-4 transition-all duration-200"
              >
                <div>
                  <div className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-1">
                    <span>{route.from}</span>
                    <ChevronRight size={14} className="text-gray-400 group-hover:text-primary-500 transition-colors" />
                    <span>{route.to}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span>{route.duration}</span>
                    <span>·</span>
                    <span>Kuniga {route.tripsPerDay} ta safar</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-base font-bold text-gray-900 tabular-nums">
                    {formatPrice(route.price)} so'm
                  </p>
                  <p className="text-xs text-gray-400">dan boshlab</p>
                </div>
              </Link>
            ))}
          </div>

          <div className="mt-6 text-center sm:hidden">
            <Link href="/trips">
              <Button variant="outline">Barcha safarlarni ko'rish</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ═══ SAFETY ═══════════════════════════════════════════════════ */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 text-sm font-medium px-4 py-2 rounded-full mb-6">
                <Shield size={14} />
                Xavfsizlik prioritet
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-5 leading-tight">
                Ishonchli va <br />xavfsiz safar
              </h2>
              <p className="text-gray-500 text-lg leading-relaxed mb-8">
                Har bir haydovchi tekshirilgan va tasdiqlanadi. Sizning xavfsizligingiz biz uchun eng muhim.
              </p>
              <div className="space-y-4">
                {[
                  { icon: Shield, title: "Tasdiqlangan haydovchilar", desc: "Barcha haydovchilar hujjat tekshiruv va reyting tizimidan o'tadi" },
                  { icon: Star, title: "Reyting va sharhlar", desc: "Har bir safardan keyin yo'lovchi va haydovchi bir-birini baholaydi" },
                  { icon: Users, title: "Telefon raqam himoyasi", desc: "Raqamlar faqat bron tasdiqlangandan keyin ko'rinadi" },
                ].map(({ icon: Icon, title, desc }) => (
                  <div key={title} className="flex gap-4">
                    <div className="w-10 h-10 bg-white rounded-xl border border-gray-100 flex items-center justify-center shrink-0 shadow-sm">
                      <Icon size={18} className="text-primary-500" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{title}</p>
                      <p className="text-sm text-gray-500 mt-0.5">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Illustration card */}
            <div className="relative hidden md:block">
              <div className="bg-white rounded-3xl border border-gray-100 shadow-card-lg p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">JR</div>
                  <div>
                    <p className="font-semibold text-gray-900">Jasur Rahimov</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      {[1,2,3,4,5].map(i => <Star key={i} size={12} className="fill-yellow-400 text-yellow-400" />)}
                      <span className="text-xs text-gray-400 ml-1">4.9 (127 sharh)</span>
                    </div>
                  </div>
                  <div className="ml-auto">
                    <span className="bg-green-50 text-green-700 text-xs font-medium px-3 py-1 rounded-full">Tasdiqlangan ✓</span>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-3 p-3.5 bg-gray-50 rounded-xl">
                    <div className="route-dot-from" />
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Toshkent</p>
                      <p className="text-xs text-gray-400">08:00</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-3.5 bg-gray-50 rounded-xl">
                    <div className="route-dot-to" />
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Samarqand</p>
                      <p className="text-xs text-gray-400">11:30</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-5 pt-4 border-t border-gray-50">
                  <div>
                    <p className="text-xs text-gray-400">Narx</p>
                    <p className="text-lg font-bold text-gray-900">45,000 so'm</p>
                  </div>
                  <Button size="sm">Joy band qilish</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ DRIVER CTA ═══════════════════════════════════════════════ */}
      <section className="py-20 bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          {/* ── Sarlavha ── */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-primary-500/10 text-primary-400 text-sm font-medium px-4 py-2 rounded-full mb-4">
              <Car size={14} />
              Haydovchilar uchun
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">
              Haydovchi bo'lish — 4 ta qadam
            </h2>
            <p className="text-gray-400 text-lg max-w-xl mx-auto">
              Ariza yuboring, hujjatlaringizni tasdiqlating va safardan pul ishlashni boshlang
            </p>
          </div>

          {/* ── 4 qadam ── */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
            {[
              {
                icon: UserPlus,
                step: "1",
                title: "Ro'yxatdan o'ting",
                desc: "Telefon raqamingiz bilan bir daqiqada ro'yxatdan o'ting",
              },
              {
                icon: Car,
                step: "2",
                title: "Avtomobil ma'lumotlari",
                desc: "Mashina modeli, yili, rangi va o'rindiqlar sonini kiriting",
              },
              {
                icon: FileText,
                step: "3",
                title: "Hujjat yuklang",
                desc: "Haydovchilik guvohnomasi va texnik pasport rasmini yuklang",
              },
              {
                icon: CheckCircle,
                step: "4",
                title: "Tasdiqlashni kuting",
                desc: "Admin 1–2 ish kuni ichida arizangizni ko'rib, tasdiqlaydi",
              },
            ].map(({ icon: Icon, step, title, desc }) => (
              <div key={step} className="relative bg-gray-800 rounded-2xl p-6 border border-gray-700 hover:border-primary-500/40 transition-colors">
                <span className="absolute top-4 right-5 text-5xl font-black text-gray-700 leading-none select-none">
                  {step}
                </span>
                <div className="w-11 h-11 bg-primary-500/15 rounded-xl flex items-center justify-center mb-4">
                  <Icon size={22} className="text-primary-400" />
                </div>
                <h3 className="text-base font-semibold text-white mb-1.5">{title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>

          {/* ── Marketing qism ── */}
          <div className="grid md:grid-cols-2 gap-12 items-center pt-4 border-t border-gray-800">
            <div>
              <h3 className="text-2xl sm:text-3xl font-bold text-white mb-4 leading-tight">
                Yo'lingizda pul ishlang
              </h3>
              <p className="text-gray-400 leading-relaxed mb-7">
                Har kuni bir yo'nalishda borasizmi? Yo'lovchi olib boring, yoqilg'i xarajatini bo'ling va qo'shimcha daromad oling.
              </p>
              <div className="grid grid-cols-3 gap-5 mb-8">
                {[
                  { value: "0%",   label: "Ro'yxatdan o'tish to'lovi" },
                  { value: "2–5%", label: "Faqat muvaffaqiyatli brondan" },
                  { value: "1–2",  label: "Ish kuni ichida tasdiqlanadi" },
                ].map(({ value, label }) => (
                  <div key={label}>
                    <p className="text-2xl font-bold text-primary-400 tabular-nums">{value}</p>
                    <p className="text-xs text-gray-500 mt-1 leading-tight">{label}</p>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/profile/driver-apply">
                  <Button size="lg">Hoziroq ariza yuboring</Button>
                </Link>
                <Link href="/register">
                  <Button variant="outline" size="lg" className="border-gray-600 text-gray-300 hover:bg-gray-800">
                    Avval ro'yxatdan o'ting
                  </Button>
                </Link>
              </div>
            </div>

            <div className="hidden md:grid grid-cols-2 gap-4">
              {[
                { title: "Toshkent → Samarqand", earning: "+36,000 so'm", trips: "Kuniga 1 ta safar" },
                { title: "Toshkent → Namangan",  earning: "+44,000 so'm", trips: "Kuniga 1 ta safar" },
                { title: "Samarqand → Buxoro",   earning: "+24,000 so'm", trips: "Kuniga 1 ta safar" },
                { title: "Toshkent → Farg'ona",  earning: "+48,000 so'm", trips: "Kuniga 1 ta safar" },
              ].map(({ title, earning, trips }) => (
                <div key={title} className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
                  <p className="text-sm text-gray-400 mb-2">{title}</p>
                  <p className="text-xl font-bold text-green-400 tabular-nums">{earning}</p>
                  <p className="text-xs text-gray-500 mt-1">{trips}</p>
                </div>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* ═══ TESTIMONIALS ═══════════════════════════════════════════ */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Foydalanuvchilar nima deydi?</h2>
            <p className="text-gray-500">Minglab mamnun foydalanuvchilarimizdan ba'zilari</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {TESTIMONIALS.map(({ name, city, text, rating, initials, color }) => (
              <div key={name} className="bg-gray-50 rounded-2xl p-6 border border-gray-100">
                <div className="flex mb-4">
                  {Array.from({ length: rating }).map((_, i) => (
                    <Star key={i} size={14} className="fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-gray-700 text-sm leading-relaxed mb-5">"{text}"</p>
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-full ${color} flex items-center justify-center text-white text-xs font-bold`}>
                    {initials}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{name}</p>
                    <p className="text-xs text-gray-400">{city}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ FINAL CTA ═══════════════════════════════════════════════ */}
      <section className="py-20 bg-primary-500">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Bugunoq safar boshlang
          </h2>
          <p className="text-primary-100 text-lg mb-8">
            Ro'yxatdan o'tish bepul. Birinchi safaringizni toping.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/trips">
              <Button
                size="lg"
                className="bg-white text-primary-600 hover:bg-primary-50 focus:ring-white"
              >
                Safar qidirish
              </Button>
            </Link>
            <Link href="/register">
              <Button
                variant="outline"
                size="lg"
                className="border-white/50 text-white hover:bg-white/10"
              >
                Ro'yxatdan o'tish
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
