"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Ban, CheckCircle, Loader2, Users, Shield, Banknote } from "lucide-react";
import api from "@/lib/api";
import type { User } from "@/types";
import Avatar from "@/components/ui/Avatar";
import Badge from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

interface UsersResponse {
  total: number;
  page: number;
  users: User[];
}

async function fetchUsers(page: number): Promise<UsersResponse> {
  const { data } = await api.get("/admin/users", { params: { page, limit: 20 } });
  return data;
}

export default function AdminUsersPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [blockTarget, setBlockTarget] = useState<User | null>(null);
  const [blockReason, setBlockReason] = useState("");

  // Hamyon to'ldirish
  const [topupTarget, setTopupTarget] = useState<User | null>(null);
  const [topupAmount, setTopupAmount] = useState("");
  const [topupNote, setTopupNote] = useState("");
  const [topupDone, setTopupDone] = useState(false);

  const { data, isLoading } = useQuery<UsersResponse>({
    queryKey: ["admin", "users", page],
    queryFn: () => fetchUsers(page),
  });

  const topupMut = useMutation({
    mutationFn: ({ id, amount, note }: { id: string; amount: number; note: string }) =>
      api.post(`/admin/users/${id}/wallet/topup`, { amount, note }),
    onSuccess: () => {
      setTopupDone(true);
      setTopupAmount("");
      setTopupNote("");
    },
  });

  const blockMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/admin/users/${id}/block`, null, { params: { reason } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      setBlockTarget(null);
      setBlockReason("");
    },
  });

  const unblockMut = useMutation({
    mutationFn: (id: string) => api.post(`/admin/users/${id}/unblock`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  const filtered = (data?.users ?? []).filter((u) =>
    search
      ? u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.phone.includes(search)
      : true
  );

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Foydalanuvchilar</h1>
        <p className="text-sm text-gray-500 mt-1">
          {data ? `Jami ${data.total.toLocaleString()} ta` : "Yuklanmoqda..."}
        </p>
      </div>

      {/* Search */}
      <div className="relative mb-5 max-w-sm">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Ism yoki telefon..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {isLoading ? (
          <div className="p-8 flex justify-center">
            <Loader2 size={28} className="animate-spin text-gray-300" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Users size={36} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-400 text-sm">Foydalanuvchi topilmadi</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-50">
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Foydalanuvchi
                </th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-400 uppercase tracking-wide hidden sm:table-cell">
                  Telefon
                </th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-400 uppercase tracking-wide hidden md:table-cell">
                  Rol
                </th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Holat
                </th>
                <th className="text-right px-5 py-3.5 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Amal
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <Avatar src={user.profile_photo} name={user.full_name} size="sm" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                        <p className="text-xs text-gray-400 sm:hidden">{user.phone}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-600 hidden sm:table-cell">
                    {user.phone}
                  </td>
                  <td className="px-5 py-4 hidden md:table-cell">
                    <div className="flex gap-1.5 flex-wrap">
                      {user.is_admin && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-purple-50 text-purple-700 text-xs font-medium rounded-full">
                          <Shield size={10} />
                          {user.admin_role === "super_admin" ? "Super Admin" : "Moderator"}
                        </span>
                      )}
                      {user.is_driver && (
                        <Badge variant="success" size="sm">Haydovchi</Badge>
                      )}
                      {!user.is_admin && !user.is_driver && (
                        <span className="text-xs text-gray-400">Yo'lovchi</span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    {user.is_blocked ? (
                      <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-medium rounded-full">
                        Bloklangan
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 bg-green-50 text-green-600 text-xs font-medium rounded-full">
                        Faol
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {/* Haydovchi uchun hamyon tugmasi */}
                      {user.is_driver && (
                        <button
                          onClick={() => {
                            setTopupTarget(user);
                            setTopupDone(false);
                            setTopupAmount("");
                            setTopupNote("");
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors"
                        >
                          <Banknote size={12} />
                          Hamyon
                        </button>
                      )}
                      {!user.is_admin && (
                        user.is_blocked ? (
                          <button
                            onClick={() => unblockMut.mutate(user.id)}
                            disabled={unblockMut.isPending}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50"
                          >
                            {unblockMut.isPending ? (
                              <Loader2 size={11} className="animate-spin" />
                            ) : (
                              <CheckCircle size={12} />
                            )}
                            Blokdan chiqar
                          </button>
                        ) : (
                          <button
                            onClick={() => setBlockTarget(user)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
                          >
                            <Ban size={12} />
                            Bloklash
                          </button>
                        )
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-5">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 text-sm rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            Oldingi
          </button>
          <span className="text-sm text-gray-500 px-2">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 text-sm rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            Keyingi
          </button>
        </div>
      )}

      {/* Hamyon to'ldirish modali */}
      <Modal
        open={!!topupTarget}
        onClose={() => { setTopupTarget(null); setTopupDone(false); }}
        title="Haydovchi hamyonini to'ldirish"
      >
        {topupDone ? (
          <div className="flex flex-col items-center text-center py-4 gap-3">
            <div className="w-12 h-12 bg-green-50 rounded-2xl flex items-center justify-center">
              <CheckCircle size={24} className="text-green-500" />
            </div>
            <p className="font-semibold text-gray-900">Muvaffaqiyatli!</p>
            <p className="text-sm text-gray-500">
              <span className="font-medium">{topupTarget?.full_name}</span> hamyoniga{" "}
              pul qo'shildi.
            </p>
            <Button fullWidth onClick={() => { setTopupTarget(null); setTopupDone(false); }}>
              Yopish
            </Button>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">
              <span className="font-semibold">{topupTarget?.full_name}</span> ({topupTarget?.phone}) haydovchi hamyoniga pul qo'shasiz.
            </p>
            <div className="space-y-3">
              <Input
                label="Miqdor (so'm)"
                placeholder="100 000"
                value={topupAmount}
                inputMode="numeric"
                onChange={(e) => {
                  const raw = e.target.value.replace(/\D/g, "");
                  setTopupAmount(raw ? parseInt(raw).toLocaleString("uz-UZ") : "");
                }}
              />
              <Input
                label="Izoh (ixtiyoriy)"
                placeholder="Masalan: Click orqali 100,000 so'm qabul qilindi"
                value={topupNote}
                onChange={(e) => setTopupNote(e.target.value)}
              />
            </div>
            <div className="flex gap-3 mt-4">
              <Button
                variant="outline"
                onClick={() => { setTopupTarget(null); setTopupDone(false); }}
                className="flex-1"
              >
                Bekor qilish
              </Button>
              <Button
                onClick={() => {
                  const amt = parseInt(topupAmount.replace(/\D/g, ""), 10);
                  if (topupTarget && amt >= 1_000) {
                    topupMut.mutate({ id: topupTarget.id, amount: amt, note: topupNote });
                  }
                }}
                disabled={
                  !topupAmount ||
                  parseInt(topupAmount.replace(/\D/g, ""), 10) < 1_000 ||
                  topupMut.isPending
                }
                className="flex-1 gap-2 bg-green-500 hover:bg-green-600"
                loading={topupMut.isPending}
              >
                To'ldirish
              </Button>
            </div>
            {topupMut.isError && (
              <p className="text-xs text-red-500 mt-2 text-center">
                {(topupMut.error as any)?.response?.data?.detail ?? "Xato yuz berdi"}
              </p>
            )}
          </>
        )}
      </Modal>

      {/* Block modal */}
      <Modal
        open={!!blockTarget}
        onClose={() => { setBlockTarget(null); setBlockReason(""); }}
        title="Foydalanuvchini bloklash"
      >
        <p className="text-sm text-gray-600 mb-4">
          <span className="font-semibold">{blockTarget?.full_name}</span> ni bloklash uchun sabab kiriting.
        </p>
        <textarea
          value={blockReason}
          onChange={(e) => setBlockReason(e.target.value)}
          placeholder="Bloklash sababi..."
          rows={3}
          className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
        />
        <div className="flex gap-3 mt-4">
          <Button
            variant="outline"
            onClick={() => { setBlockTarget(null); setBlockReason(""); }}
            className="flex-1"
          >
            Bekor qilish
          </Button>
          <Button
            onClick={() => {
              if (blockTarget && blockReason.trim()) {
                blockMut.mutate({ id: blockTarget.id, reason: blockReason });
              }
            }}
            disabled={!blockReason.trim() || blockMut.isPending}
            className="flex-1 gap-2 bg-red-500 hover:bg-red-600"
          >
            {blockMut.isPending && <Loader2 size={14} className="animate-spin" />}
            Bloklash
          </Button>
        </div>
      </Modal>
    </div>
  );
}
