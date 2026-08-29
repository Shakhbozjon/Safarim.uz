"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Phone, Lock, Eye, EyeOff, ShieldCheck, AlertCircle } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { saveTokens, formatPhone, getApiError } from "@/lib/auth";

type Step = "phone" | "code";

const RESEND_SEC = 60;

/**
 * Parolni tiklash — tizimga kirmasdan.
 *
 * Kod foydalanuvchining O'Z Telegramiga boradi (raqamini Telegram orqali
 * tasdiqlagan bo'lsa). Tasdiqlamagan bo'lsa kod unga yetib bormaydi — Eskiz SMS
 * sozlanmagan — shuning uchun bu holat ochiq aytiladi va admin bilan bog'lanish
 * taklif qilinadi. Jim qolib "kod yuborildi" deyish odamni bekorga kutdirardi.
 */
export default function ForgotPasswordPage() {
  const router = useRouter();

  const [step, setStep]         = useState<Step>("phone");
  const [phone, setPhone]       = useState("");
  const [code, setCode]         = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [showPass, setShowPass] = useState(false);

  const [channel, setChannel]   = useState("");
  const [busy, setBusy]         = useState(false);
  const [countdown, setCount]   = useState(0);
  const [errors, setErrors]     = useState<Record<string, string>>({});

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const startCountdown = () => {
    setCount(RESEND_SEC);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCount((c) => {
        if (c <= 1) { clearInterval(timerRef.current!); return 0; }
        return c - 1;
      });
    }, 1000);
  };

  async function sendCode(resend = false) {
    if (resend && countdown > 0) return;
    if (phone.replace(/\D/g, "").length < 9) {
      setErrors({ phone: "Telefon raqamni to'liq kiriting" });
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      const { data } = await api.post("/auth/send-otp", {
        phone: formatPhone(phone),
        purpose: "password_reset",
      });
      setChannel(data.channel);
      setStep("code");
      startCountdown();
    } catch (err: any) {
      setErrors({ general: getApiError(err) });
    } finally {
      setBusy(false);
    }
  }

  async function submitReset() {
    const errs: Record<string, string> = {};
    if (code.length !== 6) errs.code = "6 ta raqam kiriting";
    if (password.length < 6) errs.password = "Kamida 6 ta belgi bo'lishi kerak";
    if (password !== confirm) errs.confirm = "Parollar mos kelmadi";
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setErrors({});
    setBusy(true);
    try {
      const { data } = await api.post("/auth/reset-password", {
        phone: formatPhone(phone),
        otp_code: code,
        new_password: password,
      });
      saveTokens(data);           // tiklangach darrov kiritamiz
      const { data: me } = await api.get("/auth/me");
      router.push(me.is_driver ? "/driver" : "/my-trips");
    } catch (err: any) {
      setErrors({ general: getApiError(err) });
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Parolni tiklash</h1>
      <p className="text-sm text-gray-500 mb-7">
        {step === "phone"
          ? "Raqamingizni kiriting — tasdiqlash kodi Telegramingizga yuboriladi."
          : "Telegramga kelgan kodni kiriting va yangi parol o'ylab toping."}
      </p>

      {step === "phone" ? (
        <div className="space-y-4">
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
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            error={errors.phone}
          />

          {errors.general && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
              {errors.general}
            </div>
          )}

          <Button fullWidth size="lg" loading={busy} onClick={() => sendCode()}>
            Kod yuborish
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {channel === "telegram" ? (
            <div className="bg-primary-50 text-primary-700 text-sm rounded-xl px-4 py-3 flex gap-2">
              <ShieldCheck size={16} className="shrink-0 mt-0.5" />
              <span>Kod Telegramingizga yuborildi.</span>
            </div>
          ) : (
            <div className="bg-amber-50 text-amber-800 text-sm rounded-xl px-4 py-3 flex gap-2">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>
                Bu raqam Telegram orqali tasdiqlanmagani uchun kod sizga yetib
                bormaydi. Administrator bilan bog&apos;laning.
              </span>
            </div>
          )}

          <Input
            label="Tasdiqlash kodi"
            inputMode="numeric"
            placeholder="123456"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            error={errors.code}
          />

          <Input
            label="Yangi parol"
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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={errors.password}
          />

          <Input
            label="Parolni takrorlang"
            type={showPass ? "text" : "password"}
            placeholder="Yana bir marta"
            prefix={<Lock size={15} />}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            error={errors.confirm}
          />

          {errors.general && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
              {errors.general}
            </div>
          )}

          <Button fullWidth size="lg" loading={busy} onClick={submitReset}>
            Parolni o&apos;zgartirish
          </Button>

          <button
            type="button"
            onClick={() => sendCode(true)}
            disabled={countdown > 0 || busy}
            className="w-full text-sm text-gray-500 hover:text-gray-700 disabled:opacity-60"
          >
            {countdown > 0 ? `Qayta yuborish — ${countdown}s` : "Kodni qayta yuborish"}
          </button>
        </div>
      )}

      <p className="text-sm text-gray-500 mt-6 text-center">
        <Link href="/login" className="text-primary-600 font-medium hover:underline">
          Kirish sahifasiga qaytish
        </Link>
      </p>
    </>
  );
}
