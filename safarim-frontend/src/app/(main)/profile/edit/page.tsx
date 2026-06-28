"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Camera, User, Mail, MessageCircle, CheckCircle } from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { User as UserType } from "@/types";

type TalkLevel = "silent" | "normal" | "talkative";

const TALK_OPTIONS: { value: TalkLevel; label: string; desc: string }[] = [
  { value: "silent",    label: "Jim",       desc: "Sukut saqlashni yaxshi ko'raman" },
  { value: "normal",   label: "Odatiy",    desc: "Vaziyatga qarab gaplashaman" },
  { value: "talkative", label: "Suhbatdosh", desc: "Gaplashishni yaxshi ko'raman" },
];

export default function ProfileEditPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);

  const [fullName, setFullName]   = useState(user?.full_name ?? "");
  const [email, setEmail]         = useState(user?.email ?? "");
  const [talkLevel, setTalkLevel] = useState<TalkLevel>(user?.talk_level ?? "normal");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);

  const [saving, setSaving]       = useState(false);
  const [uploading, setUploading] = useState(false);
  const [errors, setErrors]       = useState<Record<string, string>>({});
  const [success, setSuccess]     = useState(false);

  // user yuklanganida formani bir marta sinxronlashtirish
  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setEmail(user.email ?? "");
      setTalkLevel(user.talk_level);
    }
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePhotoChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }, []);

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!fullName.trim()) errs.full_name = "Ism-familiya kiritilishi shart";
    if (fullName.trim().length < 2) errs.full_name = "Kamida 2 ta harf bo'lishi kerak";
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      errs.email = "Email formati noto'g'ri";
    return errs;
  };

  const handleSave = async () => {
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setSaving(true);
    try {
      // 1. Rasm yuklash (agar yangi tanlangan bo'lsa)
      if (photoFile) {
        setUploading(true);
        const form = new FormData();
        form.append("photo", photoFile);
        await api.post("/users/me/photo", form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setUploading(false);
      }

      // 2. Profil ma'lumotlarini yangilash
      const { data } = await api.put<UserType>("/users/me", {
        full_name: fullName.trim(),
        email: email.trim() || null,
        talk_level: talkLevel,
      });

      // 3. Cache yangilash
      qc.setQueryData(["me"], data);
      setSuccess(true);
      setTimeout(() => router.push("/profile"), 1200);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === "string") setErrors({ general: detail });
      else setErrors({ general: "Saqlashda xato yuz berdi" });
    } finally {
      setSaving(false);
      setUploading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto px-4 py-6">
        <div className="h-8 w-32 bg-gray-100 rounded-xl animate-pulse mb-6" />
        <div className="space-y-4">
          <div className="h-32 bg-gray-100 rounded-2xl animate-pulse" />
          <div className="h-16 bg-gray-100 rounded-2xl animate-pulse" />
          <div className="h-16 bg-gray-100 rounded-2xl animate-pulse" />
          <div className="h-24 bg-gray-100 rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (!user) return null;

  const avatarSrc = previewUrl ?? user.profile_photo ?? undefined;

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
        <h1 className="text-lg font-bold text-gray-900">Profilni tahrirlash</h1>
      </div>

      {/* Avatar upload */}
      <div className="flex flex-col items-center mb-8">
        <div className="relative">
          <Avatar src={avatarSrc} name={user.full_name} size="xl" />
          <button
            onClick={() => fileRef.current?.click()}
            className="absolute -bottom-1 -right-1 w-8 h-8 bg-primary-500 rounded-xl flex items-center justify-center shadow-md hover:bg-primary-600 transition-colors"
          >
            <Camera size={14} className="text-white" />
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handlePhotoChange}
        />
        <button
          onClick={() => fileRef.current?.click()}
          className="mt-3 text-sm text-primary-600 font-medium hover:text-primary-700"
        >
          Rasm o'zgartirish
        </button>
      </div>

      <div className="space-y-5">
        {/* Full name */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-3">
            <User size={15} className="text-gray-400" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Ism-familiya</span>
          </div>
          <Input
            placeholder="Ism Familiya"
            value={fullName}
            onChange={(e) => { setFullName(e.target.value); setErrors({}); }}
            error={errors.full_name}
          />
        </div>

        {/* Email */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Mail size={15} className="text-gray-400" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Email</span>
          </div>
          <Input
            type="email"
            placeholder="email@example.com (ixtiyoriy)"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setErrors({}); }}
            error={errors.email}
            hint={email && email !== user.email ? "Saqlashdan so'ng email tasdiqlanmagan bo'ladi" : undefined}
          />
        </div>

        {/* Talk level */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-3">
            <MessageCircle size={15} className="text-gray-400" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Suhbat uslubi</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {TALK_OPTIONS.map(({ value, label, desc }) => (
              <button
                key={value}
                onClick={() => setTalkLevel(value)}
                className={`flex flex-col items-center gap-1 rounded-xl border-2 p-3 text-center transition-all ${
                  talkLevel === value
                    ? "border-primary-500 bg-primary-50"
                    : "border-gray-100 hover:border-gray-200"
                }`}
              >
                <span className={`text-sm font-semibold ${talkLevel === value ? "text-primary-700" : "text-gray-700"}`}>
                  {label}
                </span>
                <span className="text-[10px] leading-tight text-gray-400">{desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* General error */}
        {errors.general && (
          <p className="text-sm text-red-500 text-center bg-red-50 rounded-xl px-4 py-3">
            {errors.general}
          </p>
        )}

        {/* Success */}
        {success && (
          <div className="flex items-center gap-2 text-green-600 bg-green-50 rounded-xl px-4 py-3">
            <CheckCircle size={16} />
            <span className="text-sm font-medium">Profil muvaffaqiyatli saqlandi</span>
          </div>
        )}

        {/* Save button */}
        <Button
          fullWidth
          size="lg"
          onClick={handleSave}
          disabled={saving}
          loading={saving}
        >
          {uploading ? "Rasm yuklanmoqda..." : "Saqlash"}
        </Button>
      </div>
    </div>
  );
}
