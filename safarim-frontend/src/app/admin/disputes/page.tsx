"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Scale, Phone, CheckCircle, XCircle, AlertTriangle, User as UserIcon, Car } from "lucide-react";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import api from "@/lib/api";

interface Dispute {
  id: string;
  seats_count: number;
  total_price: number;
  commission_amount: number;
  payment_method: string;
  confirmation_requested_at: string | null;
  route: string;
  departure_date: string | null;
  departure_time: string | null;
  passenger: { id: string; full_name: string; phone: string };
  driver: { id: string | null; full_name: string; phone: string | null; fake_confirmation_count: number };
}

function formatPrice(n: number) {
  return new Intl.NumberFormat("uz-UZ").format(n);
}
function fmtDate(d?: string | null) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("uz-UZ", { day: "numeric", month: "short" });
}

export default function AdminDisputesPage() {
  const qc = useQueryClient();
  // { id, happened } — tasdiqlash modali
  const [confirm, setConfirm] = useState<{ id: string; happened: boolean } | null>(null);

  const { data: disputes = [], isLoading } = useQuery<Dispute[]>({
    queryKey: ["admin-disputes"],
    queryFn: async () => (await api.get("/admin/disputes")).data,
    refetchInterval: 60_000,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, happened }: { id: string; happened: boolean }) =>
      api.post(`/admin/disputes/${id}/resolve`, { happened }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-disputes"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
      setConfirm(null);
    },
  });

  const confirmItem = disputes.find((d) => d.id === confirm?.id);

  return (
    <div className="p-6 max-w-4xl">
      {/* Sarlavha */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Nizolar</h1>
        <p className="text-sm text-gray-400 mt-1">
          Yo'lovchi «safar bo'lmadi», haydovchi «bo'ldi» degan bronlar. Qaror qabul qiling.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => <div key={i} className="h-32 bg-gray-100 rounded-2xl animate-pulse" />)}
        </div>
      ) : disputes.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-12 text-center">
          <CheckCircle size={36} className="text-green-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">Hozircha nizolar yo'q ✅</p>
        </div>
      ) : (
        <div className="space-y-4">
          {disputes.map((d) => (
            <div key={d.id} className="bg-white rounded-2xl border border-purple-100 p-5">
              {/* Marshrut */}
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center shrink-0">
                    <Scale size={18} className="text-purple-500" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-gray-900 truncate">{d.route}</p>
                    <p className="text-xs text-gray-400">
                      {fmtDate(d.departure_date)} {d.departure_time?.slice(0, 5)} · {d.seats_count} o'rin · {formatPrice(d.total_price)} so'm
                    </p>
                  </div>
                </div>
                <span className="text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-1 rounded-full shrink-0">
                  {d.payment_method === "cash" ? "Naqd" : d.payment_method}
                </span>
              </div>

              {/* Ikki tomon da'vosi */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-red-50 border border-red-100 rounded-xl p-3">
                  <p className="text-[11px] font-semibold text-red-500 uppercase tracking-wide mb-1 flex items-center gap-1">
                    <UserIcon size={11} /> Yo'lovchi
                  </p>
                  <p className="text-sm font-semibold text-gray-900 truncate">{d.passenger.full_name}</p>
                  <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                    <Phone size={10} /> {d.passenger.phone}
                  </p>
                  <p className="text-xs font-medium text-red-600 mt-1.5">«Safar bo'lmadi»</p>
                </div>
                <div className="bg-green-50 border border-green-100 rounded-xl p-3">
                  <p className="text-[11px] font-semibold text-green-600 uppercase tracking-wide mb-1 flex items-center gap-1">
                    <Car size={11} /> Haydovchi
                  </p>
                  <p className="text-sm font-semibold text-gray-900 truncate">{d.driver.full_name}</p>
                  <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                    <Phone size={10} /> {d.driver.phone ?? "—"}
                  </p>
                  <p className="text-xs font-medium text-green-700 mt-1.5">«Safar bo'ldi»</p>
                  {d.driver.fake_confirmation_count > 0 && (
                    <p className="text-[11px] text-orange-600 mt-1">
                      ⚠️ {d.driver.fake_confirmation_count} ta oldingi soxtalik
                    </p>
                  )}
                </div>
              </div>

              {/* Qaror tugmalari */}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="flex-1 gap-1.5"
                  onClick={() => setConfirm({ id: d.id, happened: true })}
                >
                  <CheckCircle size={14} /> Safar bo'ldi
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 gap-1.5 border-red-200 text-red-500 hover:bg-red-50"
                  onClick={() => setConfirm({ id: d.id, happened: false })}
                >
                  <XCircle size={14} /> Safar bo'lmadi
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tasdiqlash modali */}
      <Modal open={!!confirm} onClose={() => setConfirm(null)} title="Nizoni hal qilish">
        {confirmItem && confirm && (
          <div className="space-y-4">
            {confirm.happened ? (
              <div className="bg-green-50 border border-green-100 rounded-xl p-4 text-sm text-green-700">
                Safar <b>bo'lgan</b> deb belgilanadi. {confirmItem.payment_method === "cash"
                  ? `Haydovchidan ${formatPrice(confirmItem.commission_amount)} so'm komissiya hisoblanadi.`
                  : "Haydovchi ulushi hamyoniga o'tkaziladi."}
              </div>
            ) : (
              <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-sm text-red-700">
                Safar <b>bo'lmagan</b> deb belgilanadi. Haydovchi yolg'on «bo'ldi» degani uchun
                unga <b>jarima balli</b> qo'shiladi (3 taga yetganda e'lonlari vaqtincha yashiriladi).
              </div>
            )}
            <p className="text-sm text-gray-500">
              Qaror qabul qilishdan oldin ikki tomon bilan bog'laning (telefon raqamlari ko'rinadi).
            </p>
            <div className="flex gap-3">
              <Button variant="outline" fullWidth onClick={() => setConfirm(null)}>
                Bekor
              </Button>
              <Button
                fullWidth
                className={confirm.happened ? "" : "bg-red-500 hover:bg-red-600"}
                loading={resolveMutation.isPending}
                onClick={() => resolveMutation.mutate(confirm)}
              >
                {confirm.happened ? "Ha, safar bo'ldi" : "Ha, safar bo'lmadi"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
