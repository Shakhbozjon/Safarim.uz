"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Lock, Eye, EyeOff, CheckCircle, Phone, RefreshCw } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";

type Step = "send_otp" | "verify";

const OTP_RESEND_SEC = 60;

export default function SecurityPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const [step, setStep]           = useState<Step>("send_otp");
  const [otp, setOtp]             = useState("");
  const [newPassword, setNewPass] = useState("");
  const [confirmPass, setConfirm] = useState("");
  const [showNew, setShowNew]     = useState(false);
  const [showConfirm, setShowCf]  = useState(false);

  const [sending, setSending]     = useState(false);
  const [saving, setSaving]       = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [errors, setErrors]       = useState<Record<string, string>>({});
  const [success, setSuccess]     = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const startCountdown = () => {
    setCountdown(OTP_RESEND_SEC);
    timerRef.current = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { clearInterval(timerRef.current!); return 0; }
        return c - 1;
      });
    }, 1000);
  };

  const handleSendOtp = async () => {
    if (!user) return;
    setSending(true);
    setErrors({});
    try {
      await api.post("/auth/send-otp", { phone: user.phone, purpose: "password_reset" });
      setStep("verify");
      startCountdown();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setErrors({ general: typeof detail === "string" ? detail : "Kod yuborishda xato" });
    } finally {
      setSending(false);
    }
  };

  const handleResend = async () => {
    if (countdown > 0 || !user) return;
    setSending(true);
    setErrors({});
    try {
      await api.post("/auth/send-otp", { phone: user.phone, purpose: "password_reset" });
      startCountdown();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setErrors({ general: typeof detail === "string" ? detail : "Kod yuborishda xato" });
    } finally {
      setSending(false);
    }
  };

  const validate = () => {
    const errs: Record<string, string> = {};
    if (otp.length !== 6) errs.otp = "6 ta raqam kiriting";
    if (newPassword.length < 6) errs.new_password = "Kamida 6 ta belgi bo'lishi kerak";
    if (newPassword !== confirmPass) errs.confirm = "Parollar mos kelmadi";
    return errs;
  };

  const handleChangePassword = async () => {
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setSaving(true);
    try {
      await api.post("/users/me/change-password", {
        otp_code: otp,
        new_password: newPassword,
      });
      setSuccess(true);
      setTimeout(() => router.push("/profile"), 1800);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setErrors({ general: typeof detail === "string" ? detail : "Xato yuz berdi" });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto px-4 py-6">
        <div className="h-8 w-40 bg-gray-100 rounded-xl animate-pulse mb-6" />
        <div className="h-48 bg-gray-100 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.back()}
          className="w-9 h-9 rounded-xl bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
        >
          <ChevronLeft size={18} className="text-gray-600" />
        </button>
        <h1 className="text-lg font-bold text-gray-900">Parolni o'zgartirish</h1>
      </div>

      {/* Step 1 — OTP yuborish */}
      {step === "send_otp" && (
        <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-5">
          <div className="flex flex-col items-center text-center gap-3">
            <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center">
              <Lock size={28} className="text-primary-500" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900">Telefon orqali tasdiqlash</h2>
              <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                Quyidagi raqamga bir martalik kod yuboriladi:
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-gray-50 rounded-xl px-4 py-3">
            <Phone size={16} className="text-gray-400 shrink-0" />
            <span className="text-sm font-semibold text-gray-800 tracking-wider">{user.phone}</span>
          </div>

          {errors.general && (
            <p className="text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3 text-center">
              {errors.general}
            </p>
          )}

          <Button fullWidth size="lg" onClick={handleSendOtp} loading={sending}>
            Kod yuborish
          </Button>
        </div>
      )}

      {/* Step 2 — OTP + yangi parol */}
      {step === "verify" && !success && (
        <div className="space-y-4">
          {/* OTP */}
          <div className="bg-white rounded-2xl border border-gray-100 p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Tasdiqlash kodi
            </p>
            <Input
              placeholder="6 ta raqamli kod"
              value={otp}
              onChange={(e) => { setOtp(e.target.value.replace(/\D/g, "").slice(0, 6)); setErrors({}); }}
              inputMode="numeric"
              error={errors.otp}
              hint={`Kod ${user.phone} raqamiga yuborildi`}
            />

            {/* Qayta yuborish */}
            <div className="flex items-center justify-end mt-2">
              {countdown > 0 ? (
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <RefreshCw size={11} />
                  {countdown}s da qayta yuborish
                </span>
              ) : (
                <button
                  onClick={handleResend}
                  disabled={sending}
                  className="text-xs text-primary-600 font-medium hover:text-primary-700 flex items-center gap-1 disabled:opacity-50"
                >
                  <RefreshCw size={11} />
                  Qayta yuborish
                </button>
              )}
            </div>
          </div>

          {/* Yangi parol */}
          <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Yangi parol</p>
            <Input
              type={showNew ? "text" : "password"}
              placeholder="Kamida 6 ta belgi"
              value={newPassword}
              onChange={(e) => { setNewPass(e.target.value); setErrors({}); }}
              error={errors.new_password}
              suffix={
                <button type="button" onClick={() => setShowNew((v) => !v)} tabIndex={-1}>
                  {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
            />
            <Input
              type={showConfirm ? "text" : "password"}
              placeholder="Parolni tasdiqlang"
              value={confirmPass}
              onChange={(e) => { setConfirm(e.target.value); setErrors({}); }}
              error={errors.confirm}
              suffix={
                <button type="button" onClick={() => setShowCf((v) => !v)} tabIndex={-1}>
                  {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
            />
          </div>

          {errors.general && (
            <p className="text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3 text-center">
              {errors.general}
            </p>
          )}

          <Button fullWidth size="lg" onClick={handleChangePassword} loading={saving}>
            Parolni o'zgartirish
          </Button>
        </div>
      )}

      {/* Muvaffaqiyat */}
      {success && (
        <div className="bg-white rounded-2xl border border-gray-100 p-8 flex flex-col items-center text-center gap-4">
          <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center">
            <CheckCircle size={32} className="text-green-500" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900">Parol o'zgartirildi</h2>
            <p className="text-sm text-gray-500 mt-1">Profilga qaytarilmoqdasiz...</p>
          </div>
        </div>
      )}
    </div>
  );
}
