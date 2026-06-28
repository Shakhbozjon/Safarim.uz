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
import type { AdminDriverDocuments } from "@/types";
import Avatar from "@/components/ui/Avatar";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";

interface PendingDriver {
  id: string;
  user_id: string;
  vehicle_plate: string;
  vehicle_make: string;
  vehicle_model: string;
  status: string;
  created_at: string;
  user: {
    id: string;
    full_name: string;
    phone: string;
    profile_photo: string | null;
  };
}

async function fetchPendingDrivers(): Promise<PendingDriver[]> {
  const { data } = await api.get("/admin/drivers/pending");
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

  const { data: drivers, isLoading: driversLoading } = useQuery<PendingDriver[]>({
    queryKey: ["admin", "drivers", "pending"],
    queryFn: fetchPendingDrivers,
  });
  const driver = drivers?.find((d) => d.id === id);

  const { data: docs, isLoading: docsLoading } = useQuery<AdminDriverDocuments>({
    queryKey: ["admin", "driver-docs", id],
    queryFn: () => fetchDocuments(id),
    enabled: !!id,
  });

  const approveMut = useMutation({
    mutationFn: () => api.post(`/admin/drivers/${id}/approve`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "drivers", "pending"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
      router.push("/admin/drivers");
    },
  });

  const rejectMut = useMutation({
    mutationFn: () => api.post(`/admin/drivers/${id}/reject`, { reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "drivers", "pending"] });
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
        <p className="text-gray-500">Haydovchi topilmadi yoki allaqachon ko'rib chiqilgan.</p>
        <Link href="/admin/drivers" className="text-primary-600 text-sm mt-2 inline-block">
          Orqaga qaytish
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl">
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
          <p className="text-sm text-gray-400">Ko'rib chiqing va qaror qabul qiling</p>
        </div>
      </div>

      {/* User card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
        <div className="flex items-center gap-4 mb-5">
          <Avatar src={driver.user.profile_photo} name={driver.user.full_name} size="lg" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">{driver.user.full_name}</h2>
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
            <InfoRow label="Yil" value={docs.vehicle.year} />
            <InfoRow label="Rang" value={docs.vehicle.color} />
            <InfoRow label="Davlat raqami" value={docs.vehicle.plate} />
            <InfoRow label="O'rindiqlar soni" value={`${docs.vehicle.seats} ta`} />
          </>
        ) : (
          <p className="text-sm text-gray-400">Ma'lumotlarni yuklashda xatolik</p>
        )}
      </div>

      {/* License image */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <ImageIcon size={16} className="text-gray-400" />
          Haydovchilik guvohnomasi
        </h3>
        {docsLoading ? (
          <div className="w-full h-48 bg-gray-50 animate-pulse rounded-xl" />
        ) : docs?.license_url ? (
          <div className="space-y-3">
            <img
              src={docs.license_url}
              alt="Guvohnoma"
              className="w-full max-h-64 object-contain rounded-xl border border-gray-100 bg-gray-50"
            />
            <a
              href={docs.license_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:underline"
            >
              <ExternalLink size={13} />
              Katta o'lchamda ochish
            </a>
          </div>
        ) : (
          <div className="w-full h-48 bg-gray-50 rounded-xl flex items-center justify-center">
            <p className="text-sm text-gray-400">Rasm yuklanmagan</p>
          </div>
        )}
      </div>

      {/* Action buttons */}
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
          Tasdiqlash
        </Button>
        <Button
          variant="outline"
          onClick={() => setRejectOpen(true)}
          disabled={approveMut.isPending || rejectMut.isPending}
          className="flex-1 gap-2 border-red-200 text-red-600 hover:bg-red-50"
        >
          <XCircle size={16} />
          Rad etish
        </Button>
      </div>

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
