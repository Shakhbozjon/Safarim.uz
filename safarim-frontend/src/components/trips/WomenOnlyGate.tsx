"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";
import type { Gender } from "@/types";

interface WomenOnlyGateProps {
  open: boolean;
  onClose: () => void;
  /** Ayol ekani belgilangach chaqiriladi — to'xtagan band qilish davom etadi */
  onAllowed: () => void;
}

/**
 * "Faqat ayollar" safarini band qilishdan oldingi to'siq.
 *
 * Jins ro'yxatdan o'tishda so'ralmaydi — faqat shu yerda, birinchi marta kerak
 * bo'lganda. Ma'lumot foydalanuvchining o'zi bildirgani, hujjat bilan
 * tekshirilmaydi; shuning uchun matnda ham shunday deyilgan.
 */
export default function WomenOnlyGate({ open, onClose, onAllowed }: WomenOnlyGateProps) {
  const qc = useQueryClient();
  const [saving, setSaving] = useState<Gender | null>(null);
  const [error, setError] = useState("");
  const [declined, setDeclined] = useState(false);

  async function choose(gender: Gender) {
    setError("");
    setSaving(gender);
    try {
      const { data } = await api.put("/users/me", { gender });
      qc.setQueryData(["me"], data);
      if (gender === "female") {
        onAllowed();
        onClose();
      } else {
        setDeclined(true);
      }
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSaving(null);
    }
  }

  function close() {
    setDeclined(false);
    setError("");
    onClose();
  }

  return (
    <Modal open={open} onClose={close} title="Faqat ayollar uchun safar">
      {declined ? (
        <div className="space-y-5">
          <p className="text-sm text-gray-700">
            Bu safarga faqat ayol yo'lovchilar joy band qila oladi. Boshqa safarlarni
            ko'rib chiqing — ular hammaga ochiq.
          </p>
          <Button fullWidth onClick={close}>Tushunarli</Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex gap-3">
            <span className="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
              <ShieldCheck size={20} />
            </span>
            <p className="text-sm text-gray-700">
              Haydovchi bu safarni faqat ayol yo'lovchilar uchun e'lon qilgan.
              Davom etish uchun jinsingizni belgilang.
            </p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3">{error}</div>
          )}

          <div className="flex gap-3">
            <Button
              fullWidth
              onClick={() => choose("female")}
              loading={saving === "female"}
              disabled={saving !== null}
            >
              Ayolman
            </Button>
            <Button
              fullWidth
              variant="outline"
              onClick={() => choose("male")}
              loading={saving === "male"}
              disabled={saving !== null}
            >
              Erkakman
            </Button>
          </div>

          <p className="text-xs text-gray-400 border-t border-gray-100 pt-4">
            Bu ma'lumot profilingizda saqlanadi va faqat shunday safarlarda ishlatiladi.
          </p>
        </div>
      )}
    </Modal>
  );
}
