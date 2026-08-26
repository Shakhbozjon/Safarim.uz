"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ExternalLink, Loader2 } from "lucide-react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";

interface PhoneVerifyModalProps {
  open: boolean;
  onClose: () => void;
  /** Tasdiqlangach chaqiriladi — odatda to'xtab qolgan amalni davom ettirish uchun */
  onVerified?: () => void;
  /** Nima uchun tasdiqlash kerakligini tushuntiruvchi bir qator */
  reason?: string;
}

/**
 * Telefon raqamni Telegram orqali tasdiqlash.
 *
 * Foydalanuvchi Telegramga o'tadi va raqamini ulashadi; bu oyna esa fon rejimida
 * profilni so'rab turadi va tasdiq kelishi bilan yopiladi. Shu sababli qo'lda
 * "tekshirish" tugmasi kerak emas.
 */
export default function PhoneVerifyModal({
  open,
  onClose,
  onVerified,
  reason = "Raqamingiz tasdiqlangach davom etasiz.",
}: PhoneVerifyModalProps) {
  const qc = useQueryClient();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false);
  const onVerifiedRef = useRef(onVerified);
  onVerifiedRef.current = onVerified;

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
    api.post("/telegram/link")
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
  }, [open, onClose]);

  // Telegramga o'tilgandan keyin tasdiqni kutamiz
  useEffect(() => {
    if (!open || !waiting) return;
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get("/auth/me");
        if (data.is_phone_verified) {
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
  }, [open, waiting, qc, onClose]);

  return (
    <Modal open={open} onClose={onClose} title="Telefon raqamni tasdiqlash">
      <div className="space-y-5">
        <div className="flex gap-3">
          <span className="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
            <ShieldCheck size={20} />
          </span>
          <div className="min-w-0">
            <p className="text-sm text-gray-700">{reason}</p>
            <p className="text-xs text-gray-500 mt-1">
              Telegram raqamingizni o'zi yuboradi — kod terish shart emas.
            </p>
          </div>
        </div>

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
                Telegram orqali tasdiqlash
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
              <li>«📱 Raqamni ulashish» tugmasini bosing</li>
            </ol>
          </>
        ) : null}

        <p className="text-xs text-gray-400 border-t border-gray-100 pt-4">
          Telegramingiz bo'lmasa, administrator raqamingizni qo'lda tasdiqlab bera oladi.
        </p>
      </div>
    </Modal>
  );
}
