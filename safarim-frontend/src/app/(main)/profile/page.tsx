"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  User, Phone, Car, Edit3, ChevronRight,
  Shield, Bell, LogOut, CheckCircle, Clock, XCircle,
} from "lucide-react";
import Avatar from "@/components/ui/Avatar";
import Badge from "@/components/ui/Badge";
import Tabs from "@/components/ui/Tabs";
import Button from "@/components/ui/Button";
import { ProfileSkeleton } from "@/components/ui/Skeleton";
import { useAuth } from "@/hooks/useAuth";
import { useQuery } from "@tanstack/react-query";
import { isAuthenticated } from "@/lib/auth";
import api from "@/lib/api";
import { useState, useEffect } from "react";

const MENU_ITEMS = [
  { icon: User,   href: "/profile/edit",     label: "Profilni tahrirlash",  desc: "Ism, rasm, haqida" },
  { icon: Car,    href: "/my-trips",          label: "Safarlarim",            desc: "Bronlar va tarix" },
  { icon: Bell,   href: "/notifications",     label: "Bildirishnomalar",      desc: "SMS va push sozlamalari" },
  { icon: Shield, href: "/profile/security",  label: "Xavfsizlik",            desc: "Parol o'zgartirish" },
];

export default function ProfilePage() {
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("info");

  // Haydovchi ariza holati (faqat login bo'lganda)
  const { data: driverStatus } = useQuery<{
    status: "pending" | "approved" | "rejected";
    message: string;
  }>({
    queryKey: ["driver-status"],
    queryFn: async () => {
      const { data } = await api.get("/drivers/me/status");
      return data;
    },
    enabled: isAuthenticated() && !user?.is_driver,
    retry: false,
    // 404 → ariza topshirilmagan, xato emas
  });

  // Kirmagan foydalanuvchini login'ga yo'naltirish (render paytida emas — SSR xavfsizligi)
  useEffect(() => {
    if (!isLoading && !user) router.push("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
        <ProfileSkeleton />
      </div>
    );
  }

  const memberYear = new Date(user.created_at).getFullYear();

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
      {/* Profile header */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-5">
        <div className="flex items-start gap-4">
          <div className="relative">
            <Avatar src={user.profile_photo} name={user.full_name} size="xl" />
            <Link
              href="/profile/edit"
              className="absolute -bottom-1 -right-1 w-7 h-7 bg-primary-500 rounded-xl flex items-center justify-center shadow-md"
            >
              <Edit3 size={13} className="text-white" />
            </Link>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h1 className="text-xl font-bold text-gray-900 truncate">{user.full_name}</h1>
                <div className="flex items-center gap-2 mt-1">
                  <Phone size={12} className="text-gray-400" />
                  <span className="text-sm text-gray-500">{user.phone}</span>
                </div>
              </div>
              {user.is_phone_verified && (
                <Badge variant="success" size="sm" dot>Tasdiqlangan</Badge>
              )}
            </div>

            <div className="flex items-center gap-4 mt-3">
              <div className="text-center">
                <p className="text-sm font-semibold text-gray-700">{memberYear}</p>
                <p className="text-xs text-gray-400">A'zo bo'lgan</p>
              </div>
              <div className="w-px h-8 bg-gray-100" />
              <div className="text-center">
                {user.is_driver ? (
                  <Badge variant="success" size="sm">Haydovchi</Badge>
                ) : (
                  <Badge variant="default" size="sm">Yo'lovchi</Badge>
                )}
              </div>
              {user.is_admin && (
                <>
                  <div className="w-px h-8 bg-gray-100" />
                  <div className="text-center">
                    <Badge variant="warning" size="sm">Admin</Badge>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <Tabs
        tabs={[
          { key: "info",   label: "Profil",    icon: <User size={14} /> },
          { key: "driver", label: "Haydovchi",  icon: <Car size={14} /> },
        ]}
        active={activeTab}
        onChange={setActiveTab}
        className="mb-5"
      />

      {activeTab === "info" && (
        <div className="space-y-3">
          {MENU_ITEMS.map(({ icon: Icon, href, label, desc }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-4 bg-white rounded-2xl border border-gray-100 p-4 hover:border-gray-200 hover:shadow-card transition-all"
            >
              <div className="w-10 h-10 bg-gray-50 rounded-xl flex items-center justify-center">
                <Icon size={18} className="text-gray-500" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-900">{label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
              </div>
              <ChevronRight size={16} className="text-gray-300" />
            </Link>
          ))}

          <button
            onClick={logout}
            className="flex items-center gap-4 bg-white rounded-2xl border border-gray-100 p-4 w-full hover:border-red-100 hover:bg-red-50 transition-all group"
          >
            <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center group-hover:bg-red-100 transition-colors">
              <LogOut size={18} className="text-red-400" />
            </div>
            <div className="flex-1 text-left">
              <p className="text-sm font-semibold text-red-500">Chiqish</p>
              <p className="text-xs text-gray-400 mt-0.5">Hisobdan chiqish</p>
            </div>
          </button>
        </div>
      )}

      {activeTab === "driver" && (
        <div className="space-y-4">
          {/* ── Tasdiqlangan haydovchi ── */}
          {user.is_driver && (
            <>
              <div className="bg-green-50 border border-green-100 rounded-2xl p-5 flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                  <CheckCircle size={24} className="text-green-500" />
                </div>
                <div>
                  <p className="font-semibold text-green-800">Faol haydovchi</p>
                  <p className="text-sm text-green-600">Safar e'lon qilishingiz mumkin</p>
                </div>
              </div>
              <Link href="/create-trip">
                <Button fullWidth size="lg">
                  <Car size={16} />
                  Safar e'lon qilish
                </Button>
              </Link>
              <Link href="/my-trips">
                <Button fullWidth variant="outline">
                  Safarlarimni ko'rish
                </Button>
              </Link>
            </>
          )}

          {/* ── Ko'rib chiqilmoqda ── */}
          {!user.is_driver && driverStatus?.status === "pending" && (
            <>
              <div className="bg-yellow-50 border border-yellow-100 rounded-2xl p-5 flex items-center gap-4">
                <div className="w-12 h-12 bg-yellow-100 rounded-xl flex items-center justify-center">
                  <Clock size={24} className="text-yellow-500" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-yellow-800">Ko'rib chiqilmoqda</p>
                  <p className="text-sm text-yellow-600">1-3 ish kuni ichida javob beriladi</p>
                </div>
              </div>
              <Link href="/profile/driver-status">
                <Button fullWidth variant="outline">
                  Ariza holatini ko'rish
                </Button>
              </Link>
            </>
          )}

          {/* ── Rad etildi ── */}
          {!user.is_driver && driverStatus?.status === "rejected" && (
            <>
              <div className="bg-red-50 border border-red-100 rounded-2xl p-5 flex items-center gap-4">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                  <XCircle size={24} className="text-red-500" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-red-800">Ariza rad etildi</p>
                  <p className="text-sm text-red-600">Qaytadan ariza topshirishingiz mumkin</p>
                </div>
              </div>
              <Link href="/profile/driver-apply">
                <Button fullWidth size="lg">
                  Qaytadan ariza topshirish
                </Button>
              </Link>
              <Link href="/profile/driver-status">
                <Button fullWidth variant="outline">Sababini ko'rish</Button>
              </Link>
            </>
          )}

          {/* ── Ariza topshirilmagan ── */}
          {!user.is_driver && !driverStatus && (
            <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center">
              <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Car size={28} className="text-primary-500" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">Haydovchi bo'ling</h3>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed">
                Yo'lingizda yo'lovchi olib boring va qo'shimcha daromad qiling.
              </p>
              <div className="space-y-2.5 text-left mb-6">
                {[
                  "Haydovchilik guvohnomangiz",
                  "Avtomobil ma'lumotlari",
                  "1-3 ish kuni — tekshirish vaqti",
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm text-gray-600">
                    <CheckCircle size={15} className="text-green-500 shrink-0" />
                    {item}
                  </div>
                ))}
              </div>
              <Link href="/profile/driver-apply">
                <Button fullWidth size="lg">Ariza topshirish</Button>
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
