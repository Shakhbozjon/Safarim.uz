"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle, Send } from "lucide-react";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import api from "@/lib/api";
import { getApiError } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { useMounted } from "@/hooks/useMounted";

/**
 * Bog'lanish — xabar to'g'ridan-to'g'ri adminning Telegramiga tushadi.
 * Saytda qo'lda yozilgan telefon/email turardi, ularga javob beradigan
 * odam yo'q edi.
 */
/** Backenddagi tekshiruv bilan bir xil */
const MIN_MESSAGE = 10;

export default function SupportPage() {
  const mounted = useMounted();
  const { user } = useAuth();

  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  // Tugma o'chib turgani sababini aytmaydi — shuning uchun tugma doim
  // bosiladi, kamchilik esa maydon ostida yoziladi
  const [fieldError, setFieldError] = useState("");

  const filledName = mounted && user ? user.full_name : name;
  const filledContact = mounted && user ? user.phone : contact;

  const mutation = useMutation({
    mutationFn: async () => {
      await api.post("/support/", {
        name: filledName || undefined,
        contact: filledContact,
        message,
      });
    },
    onSuccess: () => setError(""),
    onError: (err) => setError(getApiError(err)),
  });

  if (mutation.isSuccess) {
    return (
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 text-center">
        <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <CheckCircle size={32} className="text-green-500" />
        </div>
        <h1 className="text-xl font-bold text-gray-900 mb-2">Xabaringiz yuborildi</h1>
        <p className="text-gray-500">
          Tez orada {filledContact} orqali javob beramiz.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto px-4 sm:px-6 py-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Bog&apos;lanish</h1>
      <p className="text-[15px] text-gray-500 mb-6">
        Savol, taklif yoki muammo bo&apos;lsa yozing — xabaringiz to&apos;g&apos;ridan-to&apos;g&apos;ri
        bizga yetib boradi.
      </p>

      <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6 space-y-4">
        {mounted && user ? (
          <div className="bg-gray-50 rounded-xl px-4 py-3 text-sm text-gray-600">
            <span className="font-semibold text-gray-900">{user.full_name}</span> · {user.phone}
            <p className="text-xs text-gray-400 mt-0.5">Javob shu raqamga keladi</p>
          </div>
        ) : (
          <>
            <Input
              label="Ismingiz"
              placeholder="Masalan: Jasur"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              label="Telefon yoki Telegram"
              placeholder="+998 90 123 45 67"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              hint="Javob bera olishimiz uchun kerak"
            />
          </>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Xabar</label>
          <textarea
            value={message}
            onChange={(e) => { setMessage(e.target.value); setFieldError(""); }}
            rows={5}
            maxLength={2000}
            placeholder="Nima bo'ldi yoki nimani taklif qilasiz?"
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
          />
          <p className="text-xs text-gray-400 mt-1 tabular-nums">
            {message.trim().length < MIN_MESSAGE
              ? `Kamida ${MIN_MESSAGE} ta belgi — hozir ${message.trim().length} ta`
              : `${message.length}/2000`}
          </p>
          {fieldError && <p className="text-xs text-red-500 mt-1">{fieldError}</p>}
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
            {error}
          </div>
        )}

        <Button
          fullWidth
          size="lg"
          loading={mutation.isPending}
          onClick={() => {
            if (filledContact.trim().length < 5) {
              setFieldError("Javob bera olishimiz uchun telefon yoki Telegram yozing");
              return;
            }
            if (message.trim().length < MIN_MESSAGE) {
              setFieldError(`Xabarni to'liqroq yozing — kamida ${MIN_MESSAGE} ta belgi`);
              return;
            }
            setFieldError("");
            setError("");
            mutation.mutate();
          }}
        >
          <Send size={16} />
          Yuborish
        </Button>
      </div>
    </div>
  );
}
