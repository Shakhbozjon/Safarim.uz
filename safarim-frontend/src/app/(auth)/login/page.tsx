"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Phone, Lock, Send } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { saveTokens, formatPhone, getApiError } from "@/lib/auth";
import { normalizePhoneInput, isCompletePhone, PHONE_ERROR } from "@/lib/phone";

const schema = z.object({
  phone: z.string().refine(isCompletePhone, PHONE_ERROR),
  password: z.string().min(1, "Parolni kiriting"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next");
  const [showPass, setShowPass] = useState(false);
  const [apiError, setApiError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });
  const phoneField = register("phone");

  const [tgLoading, setTgLoading] = useState(false);
  const [tgError, setTgError] = useState("");

  async function openTelegram() {
    setTgError("");
    setTgLoading(true);
    try {
      const { data } = await api.get("/auth/telegram-entry", {
        params: nextUrl ? { next: nextUrl } : {},
      });
      window.location.href = data.url;
    } catch (err: any) {
      setTgError(getApiError(err));
      setTgLoading(false);
    }
  }

  async function onSubmit(data: FormData) {
    setApiError("");
    try {
      const { data: tokens } = await api.post("/auth/login", {
        phone: formatPhone(data.phone),
        password: data.password,
      });
      saveTokens(tokens);
      // ?next= bo'lsa shu sahifaga, haydovchi bo'lsa /driver, yo'lovchi /my-trips
      if (nextUrl) {
        router.push(nextUrl);
        return;
      }
      const { data: me } = await api.get("/auth/me");
      router.push(me.is_driver ? "/driver" : "/my-trips");
    } catch (err: any) {
      setApiError(getApiError(err));
    }
  }

  return (
    <>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Kirish</h1>
      <p className="text-sm text-gray-500 mb-7">
        Hisobingiz yo'qmi?{" "}
        <Link href="/register" className="text-primary-600 font-medium hover:underline">
          Ro'yxatdan o'ting
        </Link>
      </p>

      {/* Botda ro'yxatdan o'tganning paroli yo'q — u shu yo'l bilan kiradi.
          Bot kirish havolasini yuboradi, havola esa shu sahifaga (next) qaytaradi. */}
      <button
        type="button"
        onClick={openTelegram}
        disabled={tgLoading}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#229ED9] hover:bg-[#1c8cc2] text-white font-semibold py-3 transition-colors disabled:opacity-60"
      >
        <Send size={17} />
        {tgLoading ? "Ochilmoqda…" : "Telegram orqali kirish"}
      </button>
      {tgError && <p className="text-xs text-red-600 mt-2 text-center">{tgError}</p>}

      <div className="flex items-center gap-3 my-5 text-xs text-gray-400">
        <span className="flex-1 h-px bg-gray-200" />
        yoki parol bilan
        <span className="flex-1 h-px bg-gray-200" />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Telefon raqam"
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          placeholder="901234567"
          prefix={
            <span className="flex items-center gap-1.5 text-gray-500">
              <Phone size={15} />
              <span className="text-sm font-medium">+998</span>
            </span>
          }
          error={errors.phone?.message}
          {...phoneField}
          onChange={(e) => {
            e.target.value = normalizePhoneInput(e.target.value);
            phoneField.onChange(e);
          }}
        />

        <Input
          label="Parol"
          type={showPass ? "text" : "password"}
          placeholder="Parolingizni kiriting"
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
          error={errors.password?.message}
          {...register("password")}
        />

        {apiError && (
          <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
            {apiError}
          </div>
        )}

        <Button type="submit" fullWidth size="lg" loading={isSubmitting} className="mt-2">
          Kirish
        </Button>

        <p className="text-center">
          <Link
            href="/forgot-password"
            className="text-sm text-gray-500 hover:text-primary-600 hover:underline"
          >
            Parolni unutdingizmi?
          </Link>
        </p>
      </form>
    </>
  );
}
