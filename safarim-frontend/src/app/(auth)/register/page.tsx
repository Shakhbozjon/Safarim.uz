"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Phone, User, Lock, Eye, EyeOff, Car } from "lucide-react";
import { clsx } from "clsx";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { saveTokens, formatPhone, getApiError } from "@/lib/auth";

const onlyDigits = (s: string) => s.replace(/\D/g, "");

/** "901234567" → "+998 90 123-45-67". To'liq bo'lmasa null.
 *
 *  Raqamni guruhlab qaytarib ko'rsatish xatoni bir qarashda ko'rsatadi —
 *  shu sabab "takrorlang" maydoni olib tashlandi: qayta terish ham xatoni
 *  takrorlashi mumkin, ko'z bilan tekshirish esa arzonroq va ishonchliroq. */
function prettyPhone(raw: string): string | null {
  const d = onlyDigits(raw).replace(/^998/, "");
  if (d.length !== 9) return null;
  return `+998 ${d.slice(0, 2)} ${d.slice(2, 5)}-${d.slice(5, 7)}-${d.slice(7, 9)}`;
}

const schema = z.object({
  phone: z.string().min(9, "9 raqam kiriting").max(13),
  full_name: z.string().min(3, "Kamida 3 ta harf"),
  password: z.string().min(6, "Kamida 6 ta belgi"),
  confirm_password: z.string(),
})
  .refine((d) => d.password === d.confirm_password, {
    message: "Parollar mos emas",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

type Role = "passenger" | "driver";

/** Kim bo'lib ro'yxatdan o'tyapti. Yo'lovchi oldindan tanlangan — ko'pchilik shu.
 *
 *  Tanlov formaning TEPASIDA: haydovchi saytga aynan shu niyat bilan keladi
 *  (reklama unga qaratilgan), shuning uchun buni formani to'ldirib bo'lgandan
 *  keyin emas, boshida ko'rishi kerak. */
const ROLES: { value: Role; label: string; icon: typeof User }[] = [
  { value: "passenger", label: "Yo'lovchiman", icon: User },
  { value: "driver",    label: "Haydovchiman", icon: Car },
];

export default function RegisterPage() {
  const router = useRouter();

  const [role, setRole] = useState<Role>("passenger");
  const [apiError, setApiError] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const form = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setApiError("");
    try {
      const { data: tokens } = await api.post("/auth/register", {
        phone: formatPhone(data.phone),
        full_name: data.full_name,
        password: data.password,
      });
      saveTokens(tokens);
      // Haydovchi bo'lishni tanlagan bo'lsa — to'g'ridan-to'g'ri ariza formasiga
      // (mashina + hujjatlar → tekshiruv). Aks holda yo'lovchi dashboardiga.
      // Ilgari hamma /my-trips ga tushardi va haydovchi o'zi qidirib topishi
      // kerak edi — funnel aynan shu joyda uzilardi.
      router.push(role === "driver" ? "/profile/driver-apply" : "/my-trips");
    } catch (err: any) {
      setApiError(getApiError(err));
    }
  }

  return (
    <>
      {/* Sarlavha */}
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Ro'yxatdan o'tish</h1>
      <p className="text-sm text-gray-500 mb-6">
        Hisobingiz bormi?{" "}
        <Link href="/login" className="text-primary-600 font-medium hover:underline">
          Kirish
        </Link>
      </p>

      {/* ── Kim bo'lib ro'yxatdan o'tyapti ── */}
      <div className="flex gap-1.5 bg-gray-100 rounded-2xl p-1.5 mb-4">
        {ROLES.map(({ value, label, icon: Icon }) => {
          const active = role === value;
          return (
            <button
              key={value}
              type="button"
              onClick={() => setRole(value)}
              aria-pressed={active}
              className={clsx(
                "flex-1 rounded-xl py-2.5 text-sm font-semibold transition-colors",
                "inline-flex items-center justify-center gap-1.5",
                active
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              )}
            >
              <Icon size={15} />
              {label}
            </button>
          );
        })}
      </div>

      {role === "driver" && (
        <p className="text-xs text-gray-500 mb-5 leading-relaxed">
          Hisob yaratilgach mashina ma&apos;lumotlarini kiritasiz va darrov safar
          e&apos;lon qila olasiz. Hujjat yuklash majburiy emas.
        </p>
      )}

      {/* ── Ro'yxat formasi ── */}
      <>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Telefon raqam"
              type="tel"
              placeholder="901234567"
              prefix={
                <span className="flex items-center gap-1.5 text-gray-500">
                  <Phone size={15} />
                  <span className="text-sm font-medium">+998</span>
                </span>
              }
              hint="Safardoshingiz shu raqam orqali bog'lanadi"
              error={form.formState.errors.phone?.message}
              autoFocus
              {...form.register("phone")}
            />

            {prettyPhone(form.watch("phone") ?? "") && (
              <div className="bg-gray-50 border border-gray-100 rounded-xl px-4 py-3">
                <p className="text-[13px] text-gray-500">Kiritilgan raqam</p>
                <p className="text-lg font-bold text-gray-900 tabular-nums tracking-wide">
                  {prettyPhone(form.watch("phone") ?? "")}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Tekshiring — keyin shu raqam bilan kirasiz.
                </p>
              </div>
            )}

            <Input
              label="Ism familiya"
              type="text"
              placeholder="Abdullayev Abdulla"
              prefix={<User size={15} />}
              error={form.formState.errors.full_name?.message}
              {...form.register("full_name")}
            />

            <Input
              label="Parol"
              type={showPass ? "text" : "password"}
              placeholder="Kamida 6 ta belgi"
              prefix={<Lock size={15} />}
              suffix={
                <button
                  type="button"
                  onClick={() => setShowPass((p) => !p)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
              error={form.formState.errors.password?.message}
              {...form.register("password")}
            />

            <Input
              label="Parolni tasdiqlash"
              type={showConfirm ? "text" : "password"}
              placeholder="Parolni qayta kiriting"
              prefix={<Lock size={15} />}
              suffix={
                <button
                  type="button"
                  onClick={() => setShowConfirm((p) => !p)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
              error={form.formState.errors.confirm_password?.message}
              {...form.register("confirm_password")}
            />

            {apiError && (
              <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
                {apiError}
              </div>
            )}

            <Button
              type="submit"
              fullWidth
              size="lg"
              loading={form.formState.isSubmitting}
            >
              {role === "driver" ? "Davom etish — hujjatlar" : "Ro'yxatdan o'tish"}
            </Button>
          </form>
      </>
    </>
  );
}
