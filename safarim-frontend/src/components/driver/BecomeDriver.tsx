"use client";

/**
 * "Haydovchi bo'ling" onboarding ekrani (BlaBlaCar uslubi).
 *
 * /create-trip sahifasiga haydovchi bo'lmagan foydalanuvchi kirganda
 * forma o'rniga shu ekran ko'rsatiladi — foydalanuvchi hech qachon
 * "403 ruxsat yo'q" xatosiga urilmaydi, doim keyingi qadam ko'rinadi.
 */
import Link from "next/link";
import {
  Car, Wallet, Users, ShieldCheck, Clock, XCircle, ChevronRight,
} from "lucide-react";
import Button from "@/components/ui/Button";
import type { User } from "@/types";

const BENEFITS = [
  { icon: Wallet, title: "Qo'shimcha daromad", desc: "Bo'sh o'rindiqlar yo'l xarajatingizni qoplaydi" },
  { icon: Users, title: "Yo'lovchini o'zingiz tanlaysiz", desc: "Bron so'rovlarini ko'rib, qabul qilasiz" },
  { icon: ShieldCheck, title: "Tekshirilgan platforma", desc: "Barcha haydovchilar hujjat orqali tasdiqlanadi" },
];

const STEPS = [
  "Arizani to'ldiring — mashina ma'lumotlari va guvohnoma (3 daqiqa)",
  "Tekshiruvdan o'ting — 1-3 ish kuni ichida javob beramiz",
  "Safar e'lon qiling va yo'lovchi qabul qilib boshlang",
];

interface Props {
  user: User | null | undefined;
  /** /drivers/me/status javobi; ariza topshirilmagan bo'lsa undefined */
  applicationStatus?: "pending" | "approved" | "rejected";
}

export default function BecomeDriver({ user, applicationStatus }: Props) {
  // ── Ariza ko'rib chiqilmoqda ──
  if (user && applicationStatus === "pending") {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="w-20 h-20 bg-yellow-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
          <Clock size={40} className="text-yellow-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Arizangiz ko'rib chiqilmoqda</h1>
        <p className="text-gray-500 mb-8">
          Hujjatlaringiz tekshirilmoqda. 1-3 ish kuni ichida javob beramiz —
          natija bildirishnoma orqali keladi.
        </p>
        <Link href="/profile/driver-status">
          <Button fullWidth variant="outline">Ariza holatini ko'rish</Button>
        </Link>
      </div>
    );
  }

  // ── Ariza rad etilgan ──
  if (user && applicationStatus === "rejected") {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="w-20 h-20 bg-red-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
          <XCircle size={40} className="text-red-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Ariza rad etildi</h1>
        <p className="text-gray-500 mb-8">
          Afsuski, arizangiz tasdiqlanmadi. Sababini ko'rib, hujjatlarni
          to'g'rilab qaytadan topshirishingiz mumkin.
        </p>
        <div className="space-y-3">
          <Link href="/profile/driver-apply">
            <Button fullWidth size="lg">Qaytadan ariza topshirish</Button>
          </Link>
          <Link href="/profile/driver-status">
            <Button fullWidth variant="outline">Sababini ko'rish</Button>
          </Link>
        </div>
      </div>
    );
  }

  // ── Hali ariza topshirmagan (yoki umuman kirmagan) ──
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="w-20 h-20 bg-primary-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
          <Car size={40} className="text-primary-500" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
          Haydovchi bo'ling va daromad qiling
        </h1>
        <p className="text-gray-500 max-w-md mx-auto leading-relaxed">
          Baribir ketayotgan yo'lingizda bo'sh o'rindiqlaringizni to'ldiring —
          yo'l xarajatlaringiz o'zini qoplasin.
        </p>
      </div>

      {/* Afzalliklar */}
      <div className="grid sm:grid-cols-3 gap-3 mb-8">
        {BENEFITS.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-white rounded-2xl border border-gray-100 p-5">
            <div className="w-10 h-10 bg-primary-50 rounded-xl flex items-center justify-center mb-3">
              <Icon size={18} className="text-primary-500" />
            </div>
            <p className="text-sm font-semibold text-gray-900 mb-1">{title}</p>
            <p className="text-xs text-gray-400 leading-relaxed">{desc}</p>
          </div>
        ))}
      </div>

      {/* Qanday ishlaydi */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-8">
        <p className="text-sm font-semibold text-gray-900 mb-4">Qanday ishlaydi?</p>
        <div className="space-y-4">
          {STEPS.map((text, i) => (
            <div key={i} className="flex items-start gap-3.5">
              <div className="w-7 h-7 bg-primary-500 text-white rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                {i + 1}
              </div>
              <p className="text-sm text-gray-600 leading-relaxed pt-1">{text}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      {user ? (
        <Link href="/profile/driver-apply">
          <Button fullWidth size="lg" className="gap-2">
            Ariza topshirish
            <ChevronRight size={16} />
          </Button>
        </Link>
      ) : (
        <div className="space-y-3">
          <Link href="/register">
            <Button fullWidth size="lg">Ro'yxatdan o'tish</Button>
          </Link>
          <Link href="/login?next=/create-trip">
            <Button fullWidth variant="outline">Hisobim bor — kirish</Button>
          </Link>
        </div>
      )}
    </div>
  );
}
