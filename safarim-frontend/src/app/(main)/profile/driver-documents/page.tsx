"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, CheckCircle, Clock, AlertCircle, ShieldCheck } from "lucide-react";
import Button from "@/components/ui/Button";
import DocUpload from "@/components/driver/DocUpload";
import VerifiedBadge from "@/components/ui/VerifiedBadge";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";
import type { DriverProfileResponse } from "@/types";

/** Hujjatni ARIZADAN KEYIN yuklash.
 *
 *  Ishga tushirish davrida hujjat ixtiyoriy: «hozircha o'tkazib yuborish»ni
 *  bosgan haydovchi uchun tekshiruvga boradigan yagona yo'l shu sahifa.
 *  Hujjat yuklash haydovchining ish holatiga TEGMAYDI — u baribir safar
 *  e'lon qilaveradi, belgi esa admin ko'rgandan keyin qo'shiladi. */
export default function DriverDocumentsPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [license, setLicense] = useState<File | null>(null);
  const [techPassport, setTechPassport] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // Yuborilgani haqidagi tasdiq. Faqat shu tashrif uchun — sahifa qayta
  // ochilganda "Tekshiruvda" holati o'zi gapiradi.
  const [sent, setSent] = useState(false);
  // `DocUpload` surat ko'rinishini O'ZIDA saqlaydi. Yuborilgach kalitni
  // o'zgartirib uni qaytadan yaratamiz — aks holda yuborilgan surat ekranda
  // qolib, hech narsa o'zgarmaganday tuyuladi (user shu ustida qoqildi).
  const [formKey, setFormKey] = useState(0);
  // Hujjati bor haydovchiga forma darrov ko'rsatilmaydi — kerak bo'lsa ochadi
  const [showForms, setShowForms] = useState(false);

  const { data: profile, isLoading } = useQuery<DriverProfileResponse>({
    queryKey: ["driver-profile"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me");
      return data;
    },
  });

  async function handleSubmit() {
    if (!license && !techPassport) return;
    setLoading(true);
    setError("");

    const fd = new FormData();
    if (license) fd.append("license_image", license);
    if (techPassport) fd.append("tech_passport_image", techPassport);

    try {
      await api.post("/drivers/me/documents", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // Sahifaning o'zi shu kesh ustida turadi — yangilanmasa haydovchi
      // hujjatini yuklab bo'lib ham "yuklanmagan" ekranni ko'rib turadi.
      await qc.invalidateQueries({ queryKey: ["driver-profile"] });
      qc.invalidateQueries({ queryKey: ["driver-status"] });
      setLicense(null);
      setTechPassport(null);
      setFormKey((k) => k + 1);
      setShowForms(false);
      setSent(true);
      // Tasdiq kartochkasi tepada — haydovchi tugma yonida, sahifaning
      // pastida turgan bo'ladi va uni ko'rmay qoladi.
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err: any) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }

  const header = (
    <div className="flex items-center gap-3 mb-6">
      <button
        onClick={() => router.push("/profile")}
        className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-colors"
      >
        <ChevronLeft size={20} />
      </button>
      <div>
        <h1 className="text-xl font-bold text-gray-900">Hujjatlarni tasdiqlash</h1>
        <p className="text-sm text-gray-500">Guvohnoma va texpasport</p>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <p className="text-gray-500 mb-4">Avval haydovchi arizasini topshiring</p>
        <Button onClick={() => router.push("/profile/driver-apply")}>
          Ariza topshirish
        </Button>
      </div>
    );
  }

  // ── Tekshirilgan: qiladigan ish qolmadi ──────────────────────────────────
  // Tekshirilgan suratni almashtirish yo'li ataylab yopiq (backend ham rad
  // etadi) — admin ko'rgan hujjat keyin boshqasiga almashtirilmasin.
  if (profile.documents_verified) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-6">
        {header}
        <div className="bg-green-50 border border-green-100 rounded-2xl p-6 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <ShieldCheck size={32} className="text-green-500" />
          </div>
          <h2 className="text-xl font-bold text-green-800 mb-2 flex items-center justify-center gap-2">
            Hujjatlaringiz tasdiqlangan
            <VerifiedBadge size={18} />
          </h2>
          <p className="text-sm text-gray-600 leading-relaxed">
            Ismingiz yonida tasdiq belgisi turibdi — yo&apos;lovchi safar
            tanlayotganda shuni ko&apos;radi. O&apos;zgartirish kerak bo&apos;lsa
            qo&apos;llab-quvvatlash xizmatiga murojaat qiling.
          </p>
        </div>
      </div>
    );
  }

  // Guvohnomasi bor — demak tekshiruv navbatida turibdi
  const waiting = profile.has_license;
  // Hujjati bo'lmasa forma darrov ochiq; bo'lsa — «qayta yuklash» bosilganda
  const formsVisible = showForms || !profile.has_license;

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-6">
      {header}

      {/* Holat kartochkasi: guvohnoma yuklangan bo'lsa navbatda turibdi,
          aks holda nima uchun kerakligi tushuntiriladi. */}
      {/* Yangi surat tanlangan bo'lsa «yuborildi» endi to'g'ri emas */}
      {sent && !license && !techPassport ? (
        <div className="bg-green-50 border border-green-100 rounded-2xl p-5 mb-5 flex items-start gap-4">
          <div className="w-11 h-11 bg-green-100 rounded-xl flex items-center justify-center shrink-0">
            <CheckCircle size={22} className="text-green-500" />
          </div>
          <div>
            <p className="font-semibold text-green-800">Hujjatingiz yuborildi</p>
            <p className="text-sm text-green-700 leading-relaxed mt-0.5">
              Tekshirilgach profilingizda tasdiq belgisi paydo bo&apos;ladi.
              Shu paytgacha safar e&apos;lon qilishda davom etavering.
            </p>
          </div>
        </div>
      ) : waiting ? (
        <div className="bg-yellow-50 border border-yellow-100 rounded-2xl p-5 mb-5 flex items-start gap-4">
          <div className="w-11 h-11 bg-yellow-100 rounded-xl flex items-center justify-center shrink-0">
            <Clock size={22} className="text-yellow-500" />
          </div>
          <div>
            <p className="font-semibold text-yellow-800">Tekshiruvda</p>
            <p className="text-sm text-yellow-700 leading-relaxed mt-0.5">
              Hujjatingiz qabul qilindi. Tekshirilgach profilingizda tasdiq
              belgisi paydo bo&apos;ladi. Shu paytgacha safar e&apos;lon qilishda
              davom etavering.
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5 mb-5">
          <p className="text-sm font-semibold text-blue-900 mb-1.5">
            Tekshiruv nima uchun kerak?
          </p>
          <p className="text-[13px] text-blue-700 leading-relaxed">
            Yo&apos;lovchi kim bilan ketayotganini bilishi kerak. Hujjatingizni{" "}
            <b>faqat admin ko&apos;radi</b> — yo&apos;lovchiga hech qachon
            ko&apos;rsatilmaydi. Tekshirilgach profilingizda{" "}
            {/* Tailwind preflight `svg { display: block }` qiladi — matn
                ichida ishlatilganda o'z qatoriga tushib ketmasin. */}
            <span className="inline-flex align-middle">
              <VerifiedBadge size={13} />
            </span>{" "}
            tasdiq belgisi paydo bo&apos;ladi.
          </p>
        </div>
      )}

      {/* Hujjati bor haydovchiga forma yopiq turadi — u allaqachon qilgan
          ishini qayta qilishga chaqirilmasin. Qayta yuklash yo'li esa ochiq:
          birinchi surat xira chiqqan bo'lishi mumkin, admin hali ko'rmagan. */}
      {!formsVisible && (
        <button
          type="button"
          onClick={() => setShowForms(true)}
          className="block mx-auto text-[13.5px] font-semibold text-gray-500 hover:text-gray-700 underline underline-offset-4 transition-colors"
        >
          Boshqa surat yuklash
        </button>
      )}

      {formsVisible && (
      <div className="space-y-5">
        <DocUpload
          key={`license-${formKey}`}
          title={
            profile.has_license
              ? "Haydovchilik guvohnomasi (yuklangan)"
              : "Haydovchilik guvohnomasi"
          }
          docName="Guvohnoma"
          hint={
            profile.has_license ? (
              <>
                Yuklangan surat ko&apos;rib chiqilmoqda. Xira chiqqan deb
                o&apos;ylasangiz, yangisini yuklang — eskisi o&apos;chiriladi.
              </>
            ) : (
              <>
                Guvohnomangizning old tomonini suratga oling. Hisobingizni
                o&apos;chirsangiz surat ham o&apos;chadi (JPEG/PNG, maks 5MB)
              </>
            )
          }
          tips={[
            "Barcha ma'lumotlar aniq ko'rinishi kerak",
            "Guvohnoma muddati o'tmagan bo'lishi kerak",
            "Faqat siz egasi bo'lgan guvohnoma",
          ]}
          onPick={setLicense}
        />

        <DocUpload
          key={`tech-${formKey}`}
          title={profile.has_tech_passport ? "Texpasport (yuklangan)" : "Texpasport"}
          docName="Texpasport"
          hint={
            <>
              Mashinaning <b>davlat raqami ko&apos;rinadigan</b> tomonini suratga
              oling — arizada yozgan <b>{profile.vehicle_plate}</b> raqamingiz shu
              hujjatga mos kelishini tekshiramiz (JPEG/PNG, maks 5MB)
            </>
          }
          tips={[
            "Davlat raqami aniq o'qilishi kerak",
            "Raqam arizada yozganingiz bilan bir xil bo'lsin",
          ]}
          onPick={setTechPassport}
        />

        {/* Belgi FAQAT guvohnomaga bog'liq — texpasport o'zi yetarli emas.
            Buni aytmasak, haydovchi texpasportini yuklab belgi kutib qoladi. */}
        {!profile.has_license && !license && techPassport && (
          <div className="bg-amber-50 text-amber-700 text-sm rounded-xl px-4 py-3 border border-amber-100 flex items-start gap-2">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            Texpasport saqlanadi, lekin tekshiruv uchun haydovchilik
            guvohnomasi ham kerak.
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100 flex items-start gap-2">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        <Button
          fullWidth
          size="lg"
          disabled={(!license && !techPassport) || loading}
          loading={loading}
          onClick={handleSubmit}
        >
          <CheckCircle size={16} />
          Yuborish
        </Button>
      </div>
      )}
    </div>
  );
}
