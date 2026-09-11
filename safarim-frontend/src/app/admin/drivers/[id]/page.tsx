"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowLeft, Car, Phone, Calendar, Image as ImageIcon,
  CheckCircle, XCircle, Loader2, ExternalLink,
} from "lucide-react";
import api from "@/lib/api";
import type { AdminDriverDocuments, AdminDriverListItem } from "@/types";
import Avatar from "@/components/ui/Avatar";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import VerifiedBadge from "@/components/ui/VerifiedBadge";

/** Sahifa ilgari haydovchini "kutayotganlar" ro'yxatidan qidirardi: ariza
 *  ko'rib chiqilgach u ro'yxatdan chiqib ketardi va sahifa "topilmadi" derdi.
 *  Avtomatik tasdiqlashda esa ro'yxat butunlay bo'sh bo'ladi. */
async function fetchDriver(id: string): Promise<AdminDriverListItem> {
  const { data } = await api.get(`/admin/drivers/${id}`);
  return data;
}

async function fetchDocuments(id: string): Promise<AdminDriverDocuments> {
  const { data } = await api.get(`/admin/drivers/${id}/documents`);
  return data;
}

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-3 border-b border-gray-50 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default function DriverDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");

  const { data: driver, isLoading: driversLoading } = useQuery<AdminDriverListItem>({
    queryKey: ["admin", "driver", id],
    queryFn: () => fetchDriver(id),
    enabled: !!id,
    retry: false,
  });

  const { data: docs, isLoading: docsLoading } = useQuery<AdminDriverDocuments>({
    queryKey: ["admin", "driver-docs", id],
    queryFn: () => fetchDocuments(id),
    enabled: !!id,
  });

  const approveMut = useMutation({
    mutationFn: () => api.post(`/admin/drivers/${id}/approve`),
    onSuccess: () => {
      // Prefiks bo'yicha: ro'yxat kaliti ["admin","drivers",tab,q] — aniq
      // kalit bilan invalidatsiya uni yangilamay qo'yardi.
      qc.invalidateQueries({ queryKey: ["admin", "drivers"] });
      qc.invalidateQueries({ queryKey: ["admin", "driver", id] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
      router.push("/admin/drivers");
    },
  });

  const rejectMut = useMutation({
    mutationFn: () => api.post(`/admin/drivers/${id}/reject`, { reason }),
    onSuccess: () => {
      // Prefiks bo'yicha: ro'yxat kaliti ["admin","drivers",tab,q] — aniq
      // kalit bilan invalidatsiya uni yangilamay qo'yardi.
      qc.invalidateQueries({ queryKey: ["admin", "drivers"] });
      qc.invalidateQueries({ queryKey: ["admin", "driver", id] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
      router.push("/admin/drivers");
    },
  });

  if (driversLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <Loader2 size={28} className="animate-spin text-primary-400" />
      </div>
    );
  }

  if (!driver) {
    return (
      <div className="p-8">
        <p className="text-gray-500">Haydovchi topilmadi.</p>
        <Link href="/admin/drivers" className="text-primary-600 text-sm mt-2 inline-block">
          Orqaga qaytish
        </Link>
      </div>
    );
  }

  return (
    <div className="p-5 sm:p-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/admin/drivers"
          className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Haydovchi arizasi</h1>
          <p className="text-sm text-gray-400">
            {driver.documents_verified
              ? "Hujjatlari tekshirilgan"
              : driver.status === "approved"
                ? "Hisobi ochiq — hujjatlari hali tekshirilmagan"
                : "Ko'rib chiqing va qaror qabul qiling"}
          </p>
        </div>
      </div>

      {/* User card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
        <div className="flex items-center gap-4 mb-5">
          <Avatar src={driver.user.profile_photo} name={driver.user.full_name} size="lg" />
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-1.5">
              {driver.user.full_name}
              {driver.documents_verified && <VerifiedBadge size={17} />}
            </h2>
            <div className="flex items-center gap-2 mt-1 text-gray-500 text-sm">
              <Phone size={14} />
              {driver.user.phone}
            </div>
          </div>
        </div>
        <InfoRow
          label="Ariza sanasi"
          value={new Date(driver.created_at).toLocaleDateString("uz-UZ", {
            day: "2-digit", month: "long", year: "numeric",
          })}
        />
      </div>

      {/* Vehicle info */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <Car size={16} className="text-gray-400" />
          Avtomobil ma'lumotlari
        </h3>
        {docsLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-gray-50 animate-pulse rounded-lg" />
            ))}
          </div>
        ) : docs ? (
          <>
            <InfoRow label="Marka" value={docs.vehicle.make} />
            <InfoRow label="Model" value={docs.vehicle.model} />
            <InfoRow label="Rang" value={docs.vehicle.color} />
            <InfoRow label="Davlat raqami" value={docs.vehicle.plate} />
            <InfoRow label="O'rindiqlar soni" value={`${docs.vehicle.seats} ta`} />
          </>
        ) : (
          <p className="text-sm text-gray-400">Ma'lumotlarni yuklashda xatolik</p>
        )}
      </div>

      {/* Hujjatlar */}
      <DocPanel
        title="Haydovchilik guvohnomasi"
        url={docs?.license_url}
        loading={docsLoading}
        emptyText="Hujjat yuklanmagan — haydovchini yuzma-yuz ko'rgan bo'lsangiz shundayam tasdiqlashingiz mumkin"
      />

      <DocPanel
        title="Texpasport"
        note={
          <>
            Hujjatdagi davlat raqami yuqorida yozilgan{" "}
            <b className="font-semibold text-gray-700">{docs?.vehicle.plate}</b> bilan
            mos kelishini tekshiring
          </>
        }
        url={docs?.tech_passport_url}
        loading={docsLoading}
        emptyText="Texpasport yuklanmagan — uchrashganda raqamni hujjatdan tekshiring"
      />

      {/* Tugmalar holatga qarab: tekshirilgan haydovchida qaror qabul
          qilinib bo'lingan, faqat sana ko'rsatiladi. */}
      {driver.documents_verified ? (
        <div className="bg-green-50 border border-green-100 rounded-2xl p-5 flex items-center gap-3">
          <CheckCircle size={20} className="text-green-500 shrink-0" />
          <p className="text-sm font-semibold text-green-800">
            Hujjatlari tekshirilgan
            {driver.verified_at &&
              ` — ${new Date(driver.verified_at).toLocaleDateString("uz-UZ", {
                day: "2-digit", month: "long", year: "numeric",
              })}`}
          </p>
        </div>
      ) : (
        <>
          {!docsLoading && !docs?.license_url && (
            <p className="text-xs text-gray-400 mb-2.5 leading-relaxed">
              Guvohnoma yuklanmagan — tasdiqlasangiz ham profilida tasdiq belgisi
              berilmaydi (belgi hujjat ko'rilganda beriladi).
            </p>
          )}
          <div className="flex gap-3">
            <Button
              onClick={() => approveMut.mutate()}
              disabled={approveMut.isPending || rejectMut.isPending}
              className="flex-1 gap-2 bg-green-500 hover:bg-green-600"
            >
              {approveMut.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <CheckCircle size={16} />
              )}
              {driver.status === "approved" ? "Hujjatlarni tasdiqlash" : "Tasdiqlash"}
            </Button>
            <Button
              variant="outline"
              onClick={() => setRejectOpen(true)}
              disabled={approveMut.isPending || rejectMut.isPending}
              className="flex-1 gap-2 border-red-200 text-red-600 hover:bg-red-50"
            >
              <XCircle size={16} />
              {driver.status === "approved" ? "Haydovchilikdan chiqarish" : "Rad etish"}
            </Button>
          </div>
        </>
      )}

      {/* Reject modal */}
      <Modal
        open={rejectOpen}
        onClose={() => { setRejectOpen(false); setReason(""); }}
        title="Arizani rad etish"
      >
        <p className="text-sm text-gray-500 mb-4">
          Rad etish sababini kiriting. Bu haydovchiga yuboriladi.
        </p>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Masalan: Guvohnoma ravshanmas, qayta yuklang..."
          rows={4}
          className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
        />
        <div className="flex gap-3 mt-4">
          <Button
            variant="outline"
            onClick={() => { setRejectOpen(false); setReason(""); }}
            className="flex-1"
          >
            Bekor qilish
          </Button>
          <Button
            onClick={() => {
              if (reason.trim()) {
                rejectMut.mutate();
                setRejectOpen(false);
                setReason("");
              }
            }}
            disabled={!reason.trim() || rejectMut.isPending}
            className="flex-1 gap-2 bg-red-500 hover:bg-red-600"
          >
            {rejectMut.isPending ? <Loader2 size={15} className="animate-spin" /> : null}
            Rad etish
          </Button>
        </div>
      </Modal>
    </div>
  );
}

/** Bitta hujjat rasmi. Guvohnoma va texpasport bir xil ko'rinishda chiqadi. */
function DocPanel({
  title,
  note,
  url,
  loading,
  emptyText,
}: {
  title: string;
  note?: React.ReactNode;
  url?: string | null;
  loading: boolean;
  emptyText: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
      <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-1">
        <ImageIcon size={16} className="text-gray-400" />
        {title}
      </h3>
      {note && <p className="text-xs text-gray-500 mb-4">{note}</p>}
      {!note && <div className="mb-4" />}

      {loading ? (
        <div className="w-full h-48 bg-gray-50 animate-pulse rounded-xl" />
      ) : url ? (
        <div className="space-y-3">
          <img
            src={url}
            alt={title}
            className="w-full max-h-64 object-contain rounded-xl border border-gray-100 bg-gray-50"
          />
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:underline"
          >
            <ExternalLink size={13} />
            Katta o&apos;lchamda ochish
          </a>
        </div>
      ) : (
        <div className="w-full min-h-[8rem] bg-gray-50 rounded-xl flex items-center justify-center p-6">
          <p className="text-sm text-gray-400 text-center">{emptyText}</p>
        </div>
      )}
    </div>
  );
}
