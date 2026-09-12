"use client";

import { useState, useRef } from "react";
import { Camera, Upload, X, AlertCircle } from "lucide-react";
import { clsx } from "clsx";
import Button from "@/components/ui/Button";

/** Bitta hujjat rasmi: kamera/galereya, ko'rib chiqish va o'z xatosi.
 *  Guvohnoma bilan texpasport bir xil yuklanadi — farqi faqat matnlarda. */
export default function DocUpload({
  title,
  hint,
  docName,
  tips,
  onPick,
}: {
  title: string;
  hint: React.ReactNode;
  /** Xato va tugma matnlarida ishlatiladi: "Guvohnoma" → "Guvohnomani suratga oling" */
  docName: string;
  tips: string[];
  onPick: (f: File | null) => void;
}) {
  const [preview, setPreview] = useState<string | null>(null);
  const [clientError, setClientError] = useState("");
  const inputRef  = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  function reset() {
    setPreview(null);
    onPick(null);
  }

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
      // Rasm o'lchamini tekshirish — juda kichik rasm hujjat bo'la olmaydi
      const probe = new window.Image();
      probe.onload = () => {
        if (probe.width < 400 || probe.height < 250) {
          setClientError(`Rasm juda kichik. ${docName}ni yaqindan, aniq suratga oling`);
          reset();
          return;
        }
        onPick(f);
        setPreview(dataUrl);
      };
      probe.onerror = () => setClientError("Rasmni o'qib bo'lmadi. Boshqa rasm tanlang");
      probe.src = dataUrl;
    };
    reader.readAsDataURL(f);
  }

  function pickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
    // Bo'shatmasak, o'chirib qayta o'sha faylni tanlaganda `change` otilmaydi
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
        <p className="text-sm text-gray-500 mt-1">{hint}</p>
      </div>

      {/* Upload zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className={clsx(
          "relative border-2 border-dashed rounded-2xl transition-all",
          preview ? "border-primary-300 p-2" : "border-gray-200 p-8"
        )}
      >
        {/* Kamera: `capture` telefonda galereya emas, to'g'ridan-to'g'ri kamerani
            ochadi. Galereya alohida qoladi — ko'p haydovchida hujjat skani
            allaqachon telefonida bor, ularni suratga olishga majburlash keraksiz. */}
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={pickFile}
        />
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={pickFile}
        />

        {preview ? (
          <div className="relative">
            <img
              src={preview}
              alt={docName}
              className="w-full h-48 object-cover rounded-xl"
            />
            <button
              type="button"
              onClick={reset}
              className="absolute top-2 right-2 w-7 h-7 bg-red-500 rounded-lg flex items-center justify-center text-white hover:bg-red-600 transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="text-center space-y-3">
            <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto">
              <Camera size={24} className="text-gray-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700">
                {docName}ni suratga oling
              </p>
              <p className="text-xs text-gray-400 mt-1">
                quyidagi tugma orqali — yoki faylni bu yerga tashlang
              </p>
            </div>
            <div className="flex items-center justify-center gap-1.5 text-xs text-gray-400">
              <Upload size={12} />
              JPEG, PNG · Maks 5MB
            </div>
          </div>
        )}
      </div>

      {/* Tor ekranda yonma-yon qo'ysak tugma matni ikki qatorga bo'linadi */}
      <div className="flex flex-col sm:flex-row gap-2">
        <Button
          type="button"
          fullWidth
          className="gap-2"
          onClick={() => cameraRef.current?.click()}
        >
          <Camera size={16} />
          {preview ? "Qayta suratga olish" : "Suratga olish"}
        </Button>
        <Button
          type="button"
          variant="outline"
          fullWidth
          className="gap-2"
          onClick={() => inputRef.current?.click()}
        >
          <Upload size={16} />
          Galereyadan
        </Button>
      </div>

      {clientError && (
        <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100 flex items-start gap-2">
          <AlertCircle size={15} className="shrink-0 mt-0.5" />
          {clientError}
        </div>
      )}

      {/* Tips */}
      <div className="bg-blue-50 rounded-xl p-4 space-y-2">
        <p className="text-xs font-semibold text-blue-800">📋 Talablar:</p>
        {tips.map((tip) => (
          <p key={tip} className="text-xs text-blue-600 flex items-start gap-1.5">
            <span className="text-blue-400 mt-0.5">•</span>
            {tip}
          </p>
        ))}
      </div>
    </div>
  );
}
