"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Lock, Eye, EyeOff, CheckCircle } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";

/**
 * Parolni o'zgartirish — joriy parol bilan.
 *
 * OTP ishlatilmaydi: foydalanuvchi allaqachon tizimga kirgan, shuning uchun uni
 * tasdiqlashning eng ishonchli usuli joriy parolni so'rash — u hech qanday
 * yetkazish kanaliga (SMS, Telegram) bog'liq emas va hamma uchun ishlaydi.
 * Parolini eslay olmagan odam chiqib "Parolni unutdingizmi?" orqali tiklaydi.
 */
export default function SecurityPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const [current, setCurrent]     = useState("");
  const [newPassword, setNewPass] = useState("");
  const [confirmPass, setConfirm] = useState("");
  const [showCurrent, setShowCur] = useState(false);
  const [showNew, setShowNew]     = useState(false);

  const [saving, setSaving]   = useState(false);
  const [errors, setErrors]   = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    const errs: Record<string, string> = {};
    if (!current) errs.current = "Joriy parolni kiriting";
    if (newPassword.length < 6) errs.new_password = "Kamida 6 ta belgi bo'lishi kerak";
    if (newPassword !== confirmPass) errs.confirm = "Parollar mos kelmadi";
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setErrors({});
    setSaving(true);
    try {
      await api.post("/users/me/change-password", {
        current_password: current,
        new_password: newPassword,
      });
      setSuccess(true);
      setTimeout(() => router.push("/profile"), 1800);
    } catch (err: any) {
      setErrors({ general: getApiError(err) });
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
        <h1 className="text-lg font-bold text-gray-900">Parolni o&apos;zgartirish</h1>
      </div>

      {success ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-8 flex flex-col items-center text-center gap-4">
          <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center">
            <CheckCircle size={32} className="text-green-500" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900">Parol o&apos;zgartirildi</h2>
            <p className="text-sm text-gray-500 mt-1">Profilga qaytarilmoqdasiz...</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Joriy parol
            </p>
            <Input
              type={showCurrent ? "text" : "password"}
              placeholder="Hozirgi parolingiz"
              prefix={<Lock size={15} />}
              value={current}
              onChange={(e) => { setCurrent(e.target.value); setErrors({}); }}
              error={errors.current}
              suffix={
                <button type="button" onClick={() => setShowCur((v) => !v)} tabIndex={-1}>
                  {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
            />
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Yangi parol
            </p>
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
              type={showNew ? "text" : "password"}
              placeholder="Parolni tasdiqlang"
              value={confirmPass}
              onChange={(e) => { setConfirm(e.target.value); setErrors({}); }}
              error={errors.confirm}
            />
          </div>

          {errors.general && (
            <p className="text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3 text-center">
              {errors.general}
            </p>
          )}

          <Button fullWidth size="lg" onClick={handleSubmit} loading={saving}>
            Parolni o&apos;zgartirish
          </Button>

          <p className="text-center text-sm text-gray-500">
            Joriy parolni eslay olmayapsizmi?{" "}
            <Link href="/forgot-password" className="text-primary-600 font-medium hover:underline">
              Telegram orqali tiklang
            </Link>
          </p>
        </div>
      )}
    </div>
  );
}
