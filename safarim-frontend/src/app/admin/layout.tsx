"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Car,
  Users,
  Shield,
  LogOut,
  ChevronRight,
  Banknote,
  Scale,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const NAV = [
  { href: "/admin",             label: "Dashboard",        icon: LayoutDashboard, exact: true },
  { href: "/admin/drivers",     label: "Haydovchilar",     icon: Car },
  { href: "/admin/users",       label: "Foydalanuvchilar", icon: Users },
  { href: "/admin/disputes",    label: "Nizolar",          icon: Scale },
  { href: "/admin/commissions", label: "Komissiyalar",     icon: Banknote },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !user?.is_admin) {
      router.replace("/");
    }
  }, [user, isLoading, router]);

  if (isLoading || !user?.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 bg-white border-r border-gray-100 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-gray-100">
          <div className="w-8 h-8 bg-primary-500 rounded-xl flex items-center justify-center">
            <Shield size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-gray-900 leading-tight">Admin Panel</p>
            <p className="text-xs text-gray-400">Safarim.uz</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ href, label, icon: Icon, exact }) => {
            const active = exact ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                  active
                    ? "bg-primary-50 text-primary-600"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                )}
              >
                <Icon size={17} />
                {label}
                {active && <ChevronRight size={13} className="ml-auto text-primary-400" />}
              </Link>
            );
          })}
        </nav>

        {/* User info + logout */}
        <div className="p-3 border-t border-gray-100">
          <div className="px-3 py-2 mb-1">
            <p className="text-xs font-semibold text-gray-800 truncate">{user.full_name}</p>
            <p className="text-xs text-gray-400">{user.admin_role === "super_admin" ? "Super Admin" : "Moderator"}</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 transition-colors"
          >
            <LogOut size={16} />
            Chiqish
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}
