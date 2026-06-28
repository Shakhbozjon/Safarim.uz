"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Phone, User, Lock, Eye, EyeOff, CheckCircle2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import OtpInput from "@/components/ui/OtpInput";
import api from "@/lib/api";
import { saveTokens, formatPhone, getApiError } from "@/lib/auth";

// ── Step 1: telefon ──
const step1Schema = z.object({
  phone: z.string().min(9, "9 raqam kiriting").max(13),
});

// ── Step 3: ism + parol ──
const step3Schema = z.object({
  full_name: z.string().min(3, "Kamida 3 ta harf"),
  password: z.string().min(6, "Kamida 6 ta belgi"),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: "Parollar mos emas",
  path: ["confirm_password"],
});

type Step1Data = z.infer<typeof step1Schema>;
type Step3Data = z.infer<typeof step3Schema>;

const STEPS = ["Telefon", "Tasdiqlash", "Ma'lumotlar"];

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [pilotOtp, setPilotOtp] = useState<string | null>(null);  // pilot rejim (SMS'siz)
  const [apiError, setApiError] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Countdown
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  // Step 1 form
  const form1 = useForm<Step1Data>({ resolver: zodResolver(step1Schema) });
  const form3 = useForm<Step3Data>({ resolver: zodResolver(step3Schema) });

  // ── Step 1: OTP yuborish ──
  async function sendOtp(data: Step1Data) {
    setApiError("");
    const formatted = formatPhone(data.phone);
    try {
      const { data } = await api.post("/auth/send-otp", { phone: formatted, purpose: "register" });
      setPilotOtp(data?.pilot_otp ?? null);
      setPhone(formatted);
      setCountdown(300); // 5 daqiqa
      setStep(2);
    } catch (err: any) {
      setApiError(getApiError(err));
    }
  }

  // ── Step 2: OTP tasdiqlash ──
  async function verifyOtp() {
    setOtpError("");
    if (otp.length < 6) {
      setOtpError("6 ta raqam kiriting");
      return;
    }
    // OTP ni step 3 da register qilganda tekshiramiz
    setStep(3);
  }

  // ── Qayta yuborish ──
  async function resendOtp() {
    try {
      const { data } = await api.post("/auth/send-otp", { phone, purpose: "register" });
      setPilotOtp(data?.pilot_otp ?? null);
      setCountdown(300);
      setOtp("");
      setOtpError("");
    } catch (err: any) {
      setOtpError(getApiError(err));
    }
  }

  // ── Step 3: Ro'yxatdan o'tish ──
  async function register(data: Step3Data) {
    setApiError("");
    try {
      const { data: tokens } = await api.post("/auth/register", {
        phone,
        otp_code: otp,
        full_name: data.full_name,
        password: data.password,
      });
      saveTokens(tokens);
      // Yangi foydalanuvchi yo'lovchi — o'z dashboardiga
      router.push("/my-trips");
    } catch (err: any) {
      const msg = getApiError(err);
      if (msg.toLowerCase().includes("otp") || msg.toLowerCase().includes("kod")) {
        setStep(2);
        setOtpError(msg);
      } else {
        setApiError(msg);
      }
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

      {/* Step indikator */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = n < step;
          const active = n === step;
          return (
            <div key={n} className="flex items-center gap-2 flex-1">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-all ${
                    done
                      ? "bg-green-100 text-green-600"
                      : active
                      ? "bg-primary-500 text-white"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  {done ? <CheckCircle2 size={16} /> : n}
                </div>
                <span className={`text-xs font-medium ${active ? "text-primary-600" : "text-gray-400"}`}>
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 mb-5 rounded ${done ? "bg-green-200" : "bg-gray-100"}`} />
              )}
            </div>
          );
        })}
      </div>

      {/* ── STEP 1: Telefon ── */}
      {step === 1 && (
        <form onSubmit={form1.handleSubmit(sendOtp)} className="space-y-4">
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
            hint="SMS kod yuboriladi"
            error={form1.formState.errors.phone?.message}
            autoFocus
            {...form1.register("phone")}
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
            loading={form1.formState.isSubmitting}
          >
            SMS kod yuborish
          </Button>
        </form>
      )}

      {/* ── STEP 2: OTP ── */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="text-center space-y-1">
            <p className="text-sm text-gray-600">
              <span className="font-semibold text-gray-900">{phone}</span>ga
              6 ta raqamli kod yuborildi
            </p>
          </div>

          {pilotOtp && (
            <div className="mb-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-center">
              <p className="text-xs text-amber-600">Pilot rejim — SMS yuborilmadi</p>
              <p className="text-2xl font-bold tracking-[0.3em] text-amber-700 tabular-nums">{pilotOtp}</p>
            </div>
          )}
          <OtpInput value={otp} onChange={setOtp} error={otpError} />

          {/* Countdown */}
          <div className="text-center">
            {countdown > 0 ? (
              <p className="text-sm text-gray-400">
                Qayta yuborish:{" "}
                <span className="text-primary-600 font-medium tabular-nums">
                  {String(Math.floor(countdown / 60)).padStart(2, "0")}:
                  {String(countdown % 60).padStart(2, "0")}
                </span>
              </p>
            ) : (
              <button
                onClick={resendOtp}
                className="text-sm text-primary-600 font-medium hover:underline"
              >
                Kodni qayta yuborish
              </button>
            )}
          </div>

          <div className="flex gap-3">
            <Button variant="outline" fullWidth onClick={() => setStep(1)}>
              Orqaga
            </Button>
            <Button fullWidth onClick={verifyOtp} disabled={otp.length < 6}>
              Tasdiqlash
            </Button>
          </div>
        </div>
      )}

      {/* ── STEP 3: Ism + Parol ── */}
      {step === 3 && (
        <form onSubmit={form3.handleSubmit(register)} className="space-y-4">
          <Input
            label="Ism familiya"
            type="text"
            placeholder="Abdullayev Abdulla"
            prefix={<User size={15} />}
            error={form3.formState.errors.full_name?.message}
            autoFocus
            {...form3.register("full_name")}
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
            error={form3.formState.errors.password?.message}
            {...form3.register("password")}
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
            error={form3.formState.errors.confirm_password?.message}
            {...form3.register("confirm_password")}
          />

          {apiError && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
              {apiError}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <Button variant="outline" fullWidth onClick={() => setStep(2)}>
              Orqaga
            </Button>
            <Button
              type="submit"
              fullWidth
              loading={form3.formState.isSubmitting}
            >
              Ro'yxatdan o'tish
            </Button>
          </div>
        </form>
      )}
    </>
  );
}
