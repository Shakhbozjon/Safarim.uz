"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Banknote, CheckCircle, Clock, Phone, AlertTriangle } from "lucide-react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import api from "@/lib/api";

interface CommissionRecord {
  id: string;
  driver: { id: string; full_name: string; phone: string };
  month: string;
  total_cash_bookings: number;
  total_commission: number;
  is_paid: boolean;
  paid_at: string | null;
}

function formatPrice(n: number) {
  return new Intl.NumberFormat("uz-UZ").format(n);
}
function formatMonth(m: string) {
  const [y, mo] = m.split("-");
  const months = [
    "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
  ];
  return `${months[parseInt(mo)]} ${y}`;
}

export default function AdminCommissionsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"unpaid" | "paid">("unpaid");
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const { data: records = [], isLoading } = useQuery<CommissionRecord[]>({
    queryKey: ["admin-commissions", tab],
    queryFn: async () => {
      const { data } = await api.get(`/admin/commissions?paid=${tab === "paid"}`);
      return data;
    },
  });

  const markPaid = useMutation({
    mutationFn: (id: string) => api.post(`/admin/commissions/${id}/mark-paid`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-commissions"] });
      setConfirmId(null);
    },
  });

  // Jami to'lanmagan summa
  const totalUnpaid = records.reduce((s, r) => s + r.total_commission, 0);
  const confirmRecord = records.find((r) => r.id === confirmId);

  return (
    <div className="p-6 max-w-4xl">

      {/* Sarlavha */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Komissiyalar</h1>
        <p className="text-sm text-gray-400 mt-1">
          Naqd pul to'lovlaridan kelib chiquvchi haydovchi qarzlari
        </p>
      </div>

      {/* Tablar + umumiy summa */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-2">
          <button
            onClick={() => setTab("unpaid")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === "unpaid"
                ? "bg-red-50 text-red-600 border border-red-100"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            To'lanmagan
          </button>
          <button
            onClick={() => setTab("paid")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === "paid"
                ? "bg-green-50 text-green-600 border border-green-100"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            To'langan
          </button>
        </div>

        {tab === "unpaid" && records.length > 0 && (
          <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-2 text-right">
            <p className="text-xs text-red-400">Jami kutilayotgan</p>
            <p className="text-lg font-bold text-red-600 tabular-nums">
              {formatPrice(totalUnpaid)} so'm
            </p>
          </div>
        )}
      </div>

      {/* Jadval */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-12 text-center">
          <CheckCircle size={36} className="text-green-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">
            {tab === "unpaid" ? "Barcha komissiyalar to'langan ✅" : "Hali to'langan komissiyalar yo'q"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {records.map((r) => (
            <div
              key={r.id}
              className={`bg-white rounded-2xl border p-5 flex items-center gap-4 ${
                tab === "unpaid" ? "border-red-100" : "border-gray-100"
              }`}
            >
              {/* Oy ikona */}
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
                tab === "unpaid" ? "bg-red-50" : "bg-green-50"
              }`}>
                {tab === "unpaid"
                  ? <Clock size={20} className="text-red-400" />
                  : <CheckCircle size={20} className="text-green-500" />
                }
              </div>

              {/* Ma'lumot */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-bold text-gray-900">{r.driver.full_name}</p>
                  <Badge variant={tab === "unpaid" ? "error" : "success"} size="sm">
                    {formatMonth(r.month)}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <Phone size={11} />
                    {r.driver.phone}
                  </span>
                  <span>{r.total_cash_bookings} ta naqd bron</span>
                  {r.paid_at && (
                    <span>
                      To'landi: {new Date(r.paid_at).toLocaleDateString("uz-UZ")}
                    </span>
                  )}
                </div>
              </div>

              {/* Summa + tugma */}
              <div className="text-right shrink-0">
                <p className={`text-lg font-bold tabular-nums ${
                  tab === "unpaid" ? "text-red-600" : "text-green-600"
                }`}>
                  {formatPrice(r.total_commission)} so'm
                </p>
                {tab === "unpaid" && (
                  <Button
                    size="sm"
                    className="mt-2 text-xs"
                    onClick={() => setConfirmId(r.id)}
                  >
                    To'landi ✓
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Qo'llanma */}
      {tab === "unpaid" && (
        <div className="mt-6 bg-amber-50 border border-amber-100 rounded-2xl p-5 flex gap-3">
          <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
          <div className="text-sm text-amber-700 space-y-1">
            <p className="font-semibold">Naqd pul komissiyasini qanday yig'asiz?</p>
            <ol className="list-decimal list-inside space-y-1 text-amber-600">
              <li>Haydovchi bilan bog'laning (telefon raqami ko'rinadi)</li>
              <li>Komissiya miqdorini Click/Payme yoki naqd orqali oling</li>
              <li>Pul olingandan so'ng "To'landi ✓" tugmasini bosing</li>
            </ol>
          </div>
        </div>
      )}

      {/* Tasdiqlash modali */}
      <Modal
        open={!!confirmId}
        onClose={() => setConfirmId(null)}
        title="To'langanligini tasdiqlash"
      >
        {confirmRecord && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Haydovchi</span>
                <span className="font-semibold">{confirmRecord.driver.full_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Oy</span>
                <span className="font-semibold">{formatMonth(confirmRecord.month)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Naqd bronlar</span>
                <span className="font-semibold">{confirmRecord.total_cash_bookings} ta</span>
              </div>
              <div className="flex justify-between border-t border-gray-200 pt-2">
                <span className="font-semibold text-gray-700">Komissiya miqdori</span>
                <span className="text-lg font-bold text-primary-600">
                  {formatPrice(confirmRecord.total_commission)} so'm
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-500">
              Bu amalni bajarishdan oldin haydovchidan to'lov qabul qilganingizga ishonch hosil qiling.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" fullWidth onClick={() => setConfirmId(null)}>
                Bekor
              </Button>
              <Button
                fullWidth
                onClick={() => markPaid.mutate(confirmId!)}
                loading={markPaid.isPending}
              >
                Ha, to'langan ✓
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
