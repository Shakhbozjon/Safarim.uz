"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Car, Camera, ChevronRight, ChevronLeft,
  CheckCircle, Upload, X, AlertCircle,
} from "lucide-react";
import { clsx } from "clsx";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import api from "@/lib/api";
import { getApiError, isAuthenticated } from "@/lib/auth";

// ─── Uzbekiston mashhur mashinalar ───────────────────────────────────────────

const MAKES = [
  "Chevrolet", "Hyundai", "Kia", "Toyota", "Nexia (Ravon)",
  "Daewoo", "Mercedes-Benz", "BMW", "Volkswagen", "Honda",
  "Nissan", "Mitsubishi", "Boshqa",
];

const MODELS_BY_MAKE: Record<string, string[]> = {
  "Chevrolet": [
    "Cobalt", "Gentra", "Lacetti", "Nexia 3", "Malibu", "Malibu 2",
    "Spark", "Matiz", "Onix", "Tracker", "Tracker 2", "Captiva",
    "Orlando", "Epica", "Aveo", "Monza", "Damas", "Labo",
    "Equinox", "Traverse", "Tahoe", "Trailblazer", "Silverado",
  ],
  "Hyundai":   ["Accent", "Elantra", "Sonata", "Tucson", "Santa Fe", "Creta", "Solaris", "i30", "Grandeur", "Palisade", "Staria", "H-1"],
  "Kia":       ["Rio", "Cerato", "Optima", "K5", "Sportage", "Sorento", "Sonet", "Seltos", "Carnival", "Picanto", "Soul"],
  "Toyota":    ["Camry", "Corolla", "RAV4", "Prado", "Land Cruiser", "Hilux", "Yaris", "Avalon", "Highlander", "Fortuner", "Venza"],
  "Nexia (Ravon)": ["Nexia 3", "Gentra", "Cobalt", "R2", "R3", "R4", "Matiz", "Damas"],
  "Daewoo":    ["Nexia", "Nexia 2", "Matiz", "Damas", "Labo", "Tico", "Gentra", "Lacetti"],
  "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "A-Class", "GLA", "GLC", "GLE", "GLS", "Sprinter", "Vito", "Viano"],
  "BMW":       ["3 Series", "5 Series", "7 Series", "X1", "X3", "X5", "X6", "X7"],
  "Volkswagen":["Polo", "Jetta", "Passat", "Golf", "Tiguan", "Touareg", "Caravelle", "Transporter"],
  "Honda":     ["Civic", "Accord", "CR-V", "HR-V", "Pilot", "Odyssey"],
  "Nissan":    ["Sentra", "Almera", "Sunny", "Qashqai", "X-Trail", "Murano", "Patrol", "Pathfinder"],
  "Mitsubishi":["Lancer", "ASX", "Outlander", "Pajero", "Montero", "Eclipse Cross", "L200"],
  "Boshqa":    [],
};

// Model select oxirida "o'zi kiritish" varianti uchun sentinel qiymati
const MODEL_CUSTOM = "__custom__";

const COLORS = [
  { value: "Oq",        hex: "#ffffff" },
  { value: "Qora",      hex: "#1a1a1a" },
  { value: "Kumush",    hex: "#c0c0c0" },
  { value: "Kulrang",   hex: "#808080" },
  { value: "Qizil",     hex: "#dc2626" },
  { value: "Ko'k",      hex: "#2563eb" },
  { value: "Yashil",    hex: "#16a34a" },
  { value: "Sariq",     hex: "#ca8a04" },
  { value: "To'q jigarrang", hex: "#92400e" },
  { value: "Boshqa",    hex: "linear-gradient(135deg,#f00,#ff0,#0f0,#00f)" },
];

const STEPS = ["Avtomobil", "Hujjat"];

// ─── O'zbekiston avtomobil raqami formati ────────────────────────────────────
// 01A123BC (2 raqam + harf + 3 raqam + 2 harf), 01123ABC, 30BB777AA
const UZ_PLATE_PATTERNS = [
  /^\d{2}[A-Z]\d{3}[A-Z]{2}$/,
  /^\d{2}\d{3}[A-Z]{3}$/,
  /^\d{2}[A-Z]{2}\d{3}[A-Z]{2}$/,
];

function normalizePlate(raw: string): string {
  return raw.replace(/[\s-]/g, "").toUpperCase();
}

function isValidUzPlate(raw: string): boolean {
  const p = normalizePlate(raw);
  return UZ_PLATE_PATTERNS.some((re) => re.test(p));
}

// ─── Komponentlar ─────────────────────────────────────────────────────────────

function StepIndicator({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const done   = n < step;
        const active = n === step;
        return (
          <div key={n} className="flex items-center flex-1">
            <div className="flex flex-col items-center gap-1">
              <div className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all",
                done   ? "bg-green-500 text-white" :
                active ? "bg-primary-500 text-white" : "bg-gray-100 text-gray-400"
              )}>
                {done ? "✓" : n}
              </div>
              <span className={clsx(
                "text-xs hidden sm:block",
                active ? "text-primary-600 font-medium" : "text-gray-400"
              )}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={clsx(
                "flex-1 h-0.5 mb-5 mx-1",
                done ? "bg-green-200" : "bg-gray-100"
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Step 1: Avtomobil ma'lumotlari ─────────────────────────────────────────

interface Step1Data {
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: string;
  vehicle_color: string;
  vehicle_plate: string;
  vehicle_seats: string;
}

function Step1Form({
  data,
  onChange,
  onNext,
}: {
  data: Step1Data;
  onChange: (key: keyof Step1Data, val: string) => void;
  onNext: () => void;
}) {
  const models = data.vehicle_make ? (MODELS_BY_MAKE[data.vehicle_make] ?? []) : [];
  const currentYear = new Date().getFullYear();

  // Ro'yxatda modeli yo'q haydovchi o'zi yozishi mumkin.
  // "Boshqa" brend yoki bo'sh ro'yxat — doim qo'lda kiritish.
  const [customModel, setCustomModel] = useState(false);
  // Brend o'zgarganda qo'lda-kiritish rejimini tiklash
  useEffect(() => { setCustomModel(false); }, [data.vehicle_make]);

  const useTextModel = customModel || data.vehicle_make === "Boshqa" || !models.length;

  const plateEntered = data.vehicle_plate.trim().length > 0;
  const plateValid = isValidUzPlate(data.vehicle_plate);

  const canNext =
    data.vehicle_make &&
    data.vehicle_model &&
    data.vehicle_year &&
    Number(data.vehicle_year) >= 1990 &&
    Number(data.vehicle_year) <= currentYear + 1 &&
    data.vehicle_color &&
    plateValid &&
    Number(data.vehicle_seats) >= 1;

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Avtomobil ma'lumotlari</h2>

        {/* Make */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Brend</label>
          <select
            value={data.vehicle_make}
            onChange={(e) => { onChange("vehicle_make", e.target.value); onChange("vehicle_model", ""); }}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 bg-white appearance-none outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">Brend tanlang</option>
            {MAKES.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Model</label>
          {useTextModel ? (
            <>
              <Input
                placeholder="Modelni yozing (masalan: Nexia, Camry...)"
                value={data.vehicle_model}
                onChange={(e) => onChange("vehicle_model", e.target.value)}
                autoFocus={customModel}
              />
              {/* Ro'yxat mavjud bo'lsa — unga qaytish imkoni */}
              {models.length > 0 && (
                <button
                  type="button"
                  onClick={() => { setCustomModel(false); onChange("vehicle_model", ""); }}
                  className="text-xs text-primary-600 hover:text-primary-700 mt-1.5"
                >
                  ← Ro'yxatdan tanlash
                </button>
              )}
            </>
          ) : (
            <select
              value={data.vehicle_model}
              onChange={(e) => {
                if (e.target.value === MODEL_CUSTOM) {
                  setCustomModel(true);
                  onChange("vehicle_model", "");
                } else {
                  onChange("vehicle_model", e.target.value);
                }
              }}
              disabled={!data.vehicle_make}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 bg-white appearance-none outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 disabled:opacity-50"
            >
              <option value="">Model tanlang</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
              <option value={MODEL_CUSTOM}>Boshqa (o'zim kiritaman)…</option>
            </select>
          )}
        </div>

        {/* Year */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Yil</label>
          <select
            value={data.vehicle_year}
            onChange={(e) => onChange("vehicle_year", e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 bg-white appearance-none outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">Yil tanlang</option>
            {Array.from({ length: currentYear - 1990 + 2 }, (_, i) => currentYear + 1 - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {/* Color */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Rang</label>
          <div className="flex flex-wrap gap-2">
            {COLORS.map(({ value, hex }) => (
              <button
                key={value}
                type="button"
                onClick={() => onChange("vehicle_color", value)}
                title={value}
                className={clsx(
                  "w-9 h-9 rounded-xl border-2 transition-all flex items-center justify-center",
                  data.vehicle_color === value
                    ? "border-primary-500 scale-110 shadow-md"
                    : "border-gray-200 hover:border-gray-300"
                )}
                style={{ background: hex }}
              >
                {data.vehicle_color === value && (
                  <CheckCircle
                    size={16}
                    className={value === "Oq" ? "text-gray-500" : "text-white"}
                  />
                )}
              </button>
            ))}
          </div>
          {data.vehicle_color && (
            <p className="text-xs text-gray-500 mt-1.5">Tanlangan: {data.vehicle_color}</p>
          )}
        </div>

        {/* Plate */}
        <Input
          label="Davlat raqami"
          placeholder="01A123BC"
          value={data.vehicle_plate}
          onChange={(e) => onChange("vehicle_plate", e.target.value.toUpperCase())}
          error={plateEntered && !plateValid ? "Raqam O'zbekiston formatiga mos emas" : undefined}
          hint={plateEntered && !plateValid ? undefined : "Masalan: 01A123BC, 01123ABC yoki 30BB777AA"}
        />

        {/* Seats */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Yo'lovchi o'rinlari: <span className="text-primary-600 font-bold">{data.vehicle_seats || "—"}</span>
          </label>
          <div className="flex gap-2">
            {[2, 3, 4, 5, 6, 7, 8].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => onChange("vehicle_seats", String(n))}
                className={clsx(
                  "flex-1 h-10 rounded-xl text-sm font-semibold transition-all border",
                  data.vehicle_seats === String(n)
                    ? "bg-primary-500 text-white border-primary-500"
                    : "bg-gray-50 text-gray-600 border-gray-100 hover:border-gray-200"
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Preview card */}
      {data.vehicle_make && data.vehicle_model && (
        <div className="bg-primary-50 rounded-2xl border border-primary-100 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center text-xl">
            🚗
          </div>
          <div>
            <p className="text-sm font-semibold text-primary-900">
              {data.vehicle_make} {data.vehicle_model} {data.vehicle_year && `(${data.vehicle_year})`}
            </p>
            <p className="text-xs text-primary-600">
              {data.vehicle_color && `${data.vehicle_color} · `}
              {data.vehicle_plate && `${data.vehicle_plate} · `}
              {data.vehicle_seats && `${data.vehicle_seats} o'rin`}
            </p>
          </div>
        </div>
      )}

      <Button fullWidth size="lg" disabled={!canNext} onClick={onNext}>
        Keyingisi
        <ChevronRight size={16} />
      </Button>
    </div>
  );
}

// ─── Step 2: Hujjat yuklash ────────────────────────────────────────────────────

function Step2Form({
  onBack,
  onSubmit,
  loading,
  error,
}: {
  onBack: () => void;
  onSubmit: (file: File) => void;
  loading: boolean;
  error: string;
}) {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile]       = useState<File | null>(null);
  const [clientError, setClientError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFile(f: File) {
    setClientError("");
    if (!f.type.startsWith("image/")) {
      setClientError("Faqat rasm fayli yuklang (JPEG yoki PNG)");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setClientError("Rasm hajmi 5 MB dan oshmasligi kerak");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      // Rasm o'lchamini tekshirish — juda kichik rasm guvohnoma bo'la olmaydi
      const probe = new window.Image();
      probe.onload = () => {
        if (probe.width < 400 || probe.height < 250) {
          setClientError("Rasm juda kichik. Guvohnomani yaqindan, aniq suratga oling");
          setFile(null);
          setPreview(null);
          return;
        }
        setFile(f);
        setPreview(dataUrl);
      };
      probe.onerror = () => setClientError("Rasmni o'qib bo'lmadi. Boshqa rasm tanlang");
      probe.src = dataUrl;
    };
    reader.readAsDataURL(f);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Haydovchilik guvohnomasi</h2>
          <p className="text-sm text-gray-500 mt-1">
            Guvohnomangizning old tomonini aniq suratga oling (JPEG/PNG, maks 5MB)
          </p>
        </div>

        {/* Upload zone */}
        <div
          onClick={() => inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className={clsx(
            "relative border-2 border-dashed rounded-2xl cursor-pointer transition-all",
            "hover:border-primary-400 hover:bg-primary-50/30",
            preview ? "border-primary-300 p-2" : "border-gray-200 p-8"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />

          {preview ? (
            <div className="relative">
              <img
                src={preview}
                alt="Guvohnoma"
                className="w-full h-48 object-cover rounded-xl"
              />
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setPreview(null); setFile(null); }}
                className="absolute top-2 right-2 w-7 h-7 bg-red-500 rounded-lg flex items-center justify-center text-white hover:bg-red-600 transition-colors"
              >
                <X size={14} />
              </button>
              <div className="absolute bottom-2 left-2 bg-black/50 rounded-lg px-2 py-1">
                <p className="text-white text-xs">Bosing — almashtirish</p>
              </div>
            </div>
          ) : (
            <div className="text-center space-y-3">
              <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto">
                <Camera size={24} className="text-gray-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-700">
                  Rasm yuklash uchun bosing
                </p>
                <p className="text-xs text-gray-400 mt-1">yoki bu yerga tashlang</p>
              </div>
              <div className="flex items-center justify-center gap-1.5 text-xs text-gray-400">
                <Upload size={12} />
                JPEG, PNG · Maks 5MB
              </div>
            </div>
          )}
        </div>

        {/* Tips */}
        <div className="bg-blue-50 rounded-xl p-4 space-y-2">
          <p className="text-xs font-semibold text-blue-800">📋 Talablar:</p>
          {[
            "Barcha ma'lumotlar aniq ko'rinishi kerak",
            "Guvohnoma muddati o'tmagan bo'lishi kerak",
            "Faqat siz egasi bo'lgan guvohnoma",
          ].map((tip) => (
            <p key={tip} className="text-xs text-blue-600 flex items-start gap-1.5">
              <span className="text-blue-400 mt-0.5">•</span>
              {tip}
            </p>
          ))}
        </div>
      </div>

      {(clientError || error) && (
        <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100 flex items-start gap-2">
          <AlertCircle size={15} className="shrink-0 mt-0.5" />
          {clientError || error}
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="outline" size="lg" onClick={onBack} className="w-24">
          <ChevronLeft size={16} />
          Orqaga
        </Button>
        <Button
          fullWidth
          size="lg"
          disabled={!file || loading}
          loading={loading}
          onClick={() => file && onSubmit(file)}
        >
          Ariza topshirish
        </Button>
      </div>
    </div>
  );
}

// ─── Asosiy sahifa ────────────────────────────────────────────────────────────

const EMPTY: Step1Data = {
  vehicle_make: "",
  vehicle_model: "",
  vehicle_year: "",
  vehicle_color: "",
  vehicle_plate: "",
  vehicle_seats: "",
};

export default function DriverApplyPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [step, setStep]     = useState(1);
  const [form, setForm]     = useState<Step1Data>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  // Avval avtorizatsiya — kirmagan foydalanuvchi avval login qiladi,
  // keyin ?next= orqali shu ariza sahifasiga qaytadi.
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login?next=/profile/driver-apply");
    } else {
      setAuthChecked(true);
    }
  }, [router]);

  if (!authChecked) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-20 text-center text-gray-400 text-sm">
        Yuklanmoqda...
      </div>
    );
  }

  function handleChange(key: keyof Step1Data, val: string) {
    setForm((prev) => ({ ...prev, [key]: val }));
  }

  async function handleSubmit(licenseFile: File) {
    setLoading(true);
    setError("");

    const fd = new FormData();
    fd.append("vehicle_make",   form.vehicle_make);
    fd.append("vehicle_model",  form.vehicle_model);
    fd.append("vehicle_year",   form.vehicle_year);
    fd.append("vehicle_color",  form.vehicle_color);
    fd.append("vehicle_plate",  form.vehicle_plate);
    fd.append("vehicle_seats",  form.vehicle_seats);
    fd.append("license_image",  licenseFile);

    try {
      await api.post("/drivers/apply", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      router.push("/profile/driver-status");
    } catch (err: any) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => step === 1 ? router.back() : setStep(1)}
          className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Haydovchi bo'lish</h1>
          <p className="text-sm text-gray-500">Ariza 1-3 ish kunida ko'rib chiqiladi</p>
        </div>
      </div>

      <StepIndicator step={step} />

      {step === 1 ? (
        <Step1Form data={form} onChange={handleChange} onNext={() => setStep(2)} />
      ) : (
        <Step2Form
          onBack={() => setStep(1)}
          onSubmit={handleSubmit}
          loading={loading}
          error={error}
        />
      )}
    </div>
  );
}
