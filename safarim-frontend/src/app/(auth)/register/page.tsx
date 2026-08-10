"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Phone, User, Lock, Eye, EyeOff, Car, Users, ChevronRight } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { saveTokens, formatPhone, getApiError } from "@/lib/auth";

const onlyDigits = (s: string) => s.replace(/\D/g, "");

const schema = z.object({
  phone: z.string().min(9, "9 raqam kiriting").max(13),
  confirm_phone: z.string(),
  full_name: z.string().min(3, "Kamida 3 ta harf"),
  password: z.string().min(6, "Kamida 6 ta belgi"),
  confirm_password: z.string(),
})
  .refine((d) => onlyDigits(d.phone) === onlyDigits(d.confirm_phone), {
    message: "Raqamlar mos emas — qayta tekshiring",
    path: ["confirm_phone"],
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Parollar mos emas",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<"passenger" | "driver" | null>(null);
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
      // (mashina + guvohnoma → tekshiruv). Aks holda yo'lovchi dashboardiga.
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

      {/* ── Rol tanlash (birinchi qadam) ── */}
      {!role && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700 mb-1">Kim sifatida ro'yxatdan o'tasiz?</p>

          <button
            type="button"
            onClick={() => setRole("passenger")}
            className="w-full flex items-center gap-4 bg-white rounded-2xl border border-gray-200 p-5 text-left hover:border-primary-300 hover:shadow-card transition-all"
          >
            <div className="w-11 h-11 bg-primary-50 rounded-xl flex items-center justify-center shrink-0">
              <Users size={20} className="text-primary-500" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-900">Yo'lovchi</p>
              <p className="text-sm text-gray-500 mt-0.5">Safar qidiring va band qiling</p>
            </div>
            <ChevronRight size={18} className="text-gray-300" />
          </button>

          <button
            type="button"
            onClick={() => setRole("driver")}
            className="w-full flex items-center gap-4 bg-white rounded-2xl border border-gray-200 p-5 text-left hover:border-primary-300 hover:shadow-card transition-all"
          >
            <div className="w-11 h-11 bg-primary-50 rounded-xl flex items-center justify-center shrink-0">
              <Car size={20} className="text-primary-500" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-900">Haydovchi</p>
              <p className="text-sm text-gray-500 mt-0.5">Safar e'lon qiling va daromad qiling</p>
            </div>
            <ChevronRight size={18} className="text-gray-300" />
          </button>

          <p className="text-xs text-gray-400 text-center pt-2 leading-relaxed">
            Haydovchi bo'lish uchun avval hisob yaratasiz, so'ng mashina
            ma'lumotlari va guvohnomangizni yuklaysiz (1–3 ish kuni tekshiruv).
          </p>
        </div>
      )}

      {/* ── Ro'yxat formasi (rol tanlangach) ── */}
      {role && (
        <>
          {/* Tanlangan rol + o'zgartirish */}
          <div className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-2.5 mb-6">
            <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
              {role === "driver"
                ? <Car size={15} className="text-primary-500" />
                : <Users size={15} className="text-primary-500" />}
              {role === "driver" ? "Haydovchi" : "Yo'lovchi"} sifatida
            </span>
            <button
              type="button"
              onClick={() => setRole(null)}
              className="text-xs text-primary-600 font-medium hover:underline"
            >
              O'zgartirish
            </button>
          </div>

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

            <Input
              label="Telefon raqamni takrorlang"
              type="tel"
              placeholder="901234567"
              prefix={
                <span className="flex items-center gap-1.5 text-gray-500">
                  <Phone size={15} />
                  <span className="text-sm font-medium">+998</span>
                </span>
              }
              hint="Xatoni oldini olish uchun raqamni qayta kiriting"
              error={form.formState.errors.confirm_phone?.message}
              onPaste={(e) => e.preventDefault()}
              {...form.register("confirm_phone")}
            />

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
              Ro'yxatdan o'tish
            </Button>
          </form>
        </>
      )}
    </>
  );
}
