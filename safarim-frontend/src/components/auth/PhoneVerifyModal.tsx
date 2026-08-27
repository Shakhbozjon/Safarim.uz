"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ExternalLink, Loader2 } from "lucide-react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";

type Purpose = "verify" | "change_phone";

interface PhoneVerifyModalProps {
  open: boolean;
  onClose: () => void;
  /** Tasdiqlangach chaqiriladi — odatda to'xtab qolgan amalni davom ettirish uchun */
  onVerified?: () => void;
  /** Nima uchun tasdiqlash kerakligini tushuntiruvchi bir qator */
  reason?: string;
  /** "verify" — raqamni tasdiqlash, "change_phone" — boshqa raqamga almashtirish */
  purpose?: Purpose;
  /** Almashtirishda kerak: shu raqam o'zgarganini kutamiz */
  currentPhone?: string;
}

/**
 * Telefon raqamni Telegram orqali tasdiqlash yoki almashtirish.
 *
 * Foydalanuvchi Telegramga o'tadi va raqamini ulashadi; bu oyna esa fon rejimida
 * profilni so'rab turadi va natija kelishi bilan yopiladi. Shu sababli qo'lda
 * "tekshirish" tugmasi kerak emas.
 *
 * Almashtirishda bot raqamni solishtirmaydi — o'rnatadi. Shuning uchun bu yerda
 * tasdiq belgisini emas, raqamning o'zgarganini kuzatamiz: allaqachon
 * tasdiqlangan foydalanuvchida `is_phone_verified` hech qachon o'zgarmaydi.
 */
export default function PhoneVerifyModal({
  open,
  onClose,
  onVerified,
  reason,
  purpose = "verify",
  currentPhone,
}: PhoneVerifyModalProps) {
  const qc = useQueryClient();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false);
  const onVerifiedRef = useRef(onVerified);
  onVerifiedRef.current = onVerified;

  const isChange = purpose === "change_phone";
  const title = isChange ? "Telefon raqamni o'zgartirish" : "Telefon raqamni tasdiqlash";
  const hint =
    reason ??
    (isChange
      ? "Hisobingizdagi raqam siz ulashgan Telegram raqamiga almashtiriladi."
      : "Raqamingiz tasdiqlangach davom etasiz.");

  // Oyna ochilganda havolani olamiz
  useEffect(() => {
    if (!open) {
      setUrl("");
      setError("");
      setWaiting(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    api.post("/telegram/link", { purpose })
      .then(({ data }) => {
        if (cancelled) return;
        if (data.already_verified) {
          onVerifiedRef.current?.();
          onClose();
          return;
        }
        setUrl(data.url);
      })
      .catch((err) => { if (!cancelled) setError(getApiError(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, onClose, purpose]);

  // Telegramga o'tilgandan keyin natijani kutamiz
  useEffect(() => {
    if (!open || !waiting) return;
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get("/auth/me");
        const done = isChange
          ? Boolean(currentPhone) && data.phone !== currentPhone
          : data.is_phone_verified;
        if (done) {
          clearInterval(timer);
          qc.setQueryData(["me"], data);
          onVerifiedRef.current?.();
          onClose();
        }
      } catch {
        // vaqtincha tarmoq xatosi — keyingi urinishda qayta so'raladi
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [open, waiting, qc, onClose, isChange, currentPhone]);

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-5">
        <div className="flex gap-3">
          <span className="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
            <ShieldCheck size={20} />
          </span>
          <div className="min-w-0">
            <p className="text-sm text-gray-700">{hint}</p>
            <p className="text-xs text-gray-500 mt-1">
              Telegram raqamingizni o'zi yuboradi — kod terish shart emas.
            </p>
          </div>
        </div>

        {isChange && currentPhone && (
          <div className="bg-gray-50 text-sm rounded-xl px-4 py-3">
            <span className="text-gray-500">Hozirgi raqam: </span>
            <span className="font-medium text-gray-800">{currentPhone}</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3">{error}</div>
        )}

        {loading ? (
          <div className="h-12 rounded-xl bg-gray-100 animate-pulse" />
        ) : url ? (
          <>
            <a href={url} target="_blank" rel="noopener noreferrer" onClick={() => setWaiting(true)}>
              <Button fullWidth size="lg" className="gap-2">
                <ExternalLink size={16} />
                {isChange ? "Telegram orqali o'zgartirish" : "Telegram orqali tasdiqlash"}
              </Button>
            </a>

            {waiting && (
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <Loader2 size={15} className="animate-spin" />
                Telegramda raqamni ulashing — bu yerda o'zi davom etadi
              </div>
            )}

            <ol className="text-xs text-gray-500 space-y-1.5 list-decimal pl-4">
              <li>Yuqoridagi tugma Telegramdagi botni ochadi</li>
              <li>«Start» ni bosing</li>
              <li>
                {isChange
                  ? "«📱 Yangi raqamni ulashish» tugmasini bosing"
                  : "«📱 Raqamni ulashish» tugmasini bosing"}
              </li>
            </ol>

            {isChange && (
              <p className="text-xs text-gray-500">
                Yangi raqam bilan <b>o'sha Telegram hisobidan</b> kirasiz — keyingi
                safar saytga shu raqam bilan kiring.
              </p>
            )}
          </>
        ) : null}

        <p className="text-xs text-gray-400 border-t border-gray-100 pt-4">
          Telegramingiz bo'lmasa, administrator raqamingizni qo'lda tasdiqlab bera oladi.
        </p>
      </div>
    </Modal>
  );
}
