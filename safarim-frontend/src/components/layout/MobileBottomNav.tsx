"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Search, Plus, MessageCircle, User } from "lucide-react";
import { clsx } from "clsx";
import { useQuery } from "@tanstack/react-query";
import { isAuthenticated } from "@/lib/auth";
import api from "@/lib/api";

export default function MobileBottomNav() {
  const pathname = usePathname();

  // O'qilmagan xabarlar soni
  const { data: unreadList = [] } = useQuery<{ booking_id: string; unread_count: number }[]>({
    queryKey: ["unread-count"],
    queryFn: async () => {
      const { data } = await api.get("/messages/unread/count");
      return data;
    },
    enabled: isAuthenticated(),
    refetchInterval: 30_000, // 30 soniyada bir yangilash
  });

  const totalUnread = unreadList.reduce((sum, r) => sum + r.unread_count, 0);

  const NAV = [
    { href: "/",            icon: Home,          label: "Bosh sahifa" },
    { href: "/trips",       icon: Search,        label: "Safarlar" },
    { href: "/create-trip", icon: Plus,          label: "Qo'shish", primary: true },
    { href: "/my-trips",    icon: MessageCircle, label: "Xabarlar", badge: totalUnread },
    { href: "/profile",     icon: User,          label: "Profil" },
  ];

  return (
    <nav className="fixed bottom-0 inset-x-0 z-40 md:hidden bg-white border-t border-gray-100 safe-area-bottom">
      <div className="flex items-center justify-around px-2 py-2">
        {NAV.map(({ href, icon: Icon, label, primary, badge }) => {
          const active = pathname === href || pathname.startsWith(href + "/");

          if (primary) {
            return (
              <Link key={href} href={href} className="flex flex-col items-center -mt-5">
                <div className="w-12 h-12 bg-primary-500 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-500/30">
                  <Icon size={22} className="text-white" />
                </div>
              </Link>
            );
          }

          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex flex-col items-center gap-1 p-2 rounded-xl transition-colors min-w-[56px] relative",
                active ? "text-primary-500" : "text-gray-400"
              )}
            >
              <div className="relative">
                <Icon size={20} />
                {!!badge && badge > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 bg-red-500 rounded-full flex items-center justify-center text-white text-[9px] font-bold px-0.5">
                    {badge > 99 ? "99+" : badge}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-medium">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
