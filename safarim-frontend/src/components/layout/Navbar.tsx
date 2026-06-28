"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Bell, Plus, User, LogOut, ChevronDown, Car } from "lucide-react";
import { clsx } from "clsx";
import Avatar from "@/components/ui/Avatar";
import Button from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { useUnreadCount } from "@/hooks/useNotifications";

const PASSENGER_LINKS = [
  { href: "/trips", label: "Safar qidirish" },
];
// Haydovchilar — viloyatlar aro taksistlar (kasbiy). Safar qidirmaydi, faqat e'lon qiladi.
const DRIVER_LINKS = [
  { href: "/driver", label: "Panel" },
];

interface NavbarProps {
  transparent?: boolean;
}

export default function Navbar({ transparent = false }: NavbarProps) {
  const { user, logout } = useAuth();
  const unreadCount = useUnreadCount();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    if (!transparent) return;
    const handler = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, [transparent]);

  const isTransparent = transparent && !scrolled;

  return (
    <>
      <header
        className={clsx(
          "fixed top-0 inset-x-0 z-40 transition-all duration-300",
          isTransparent
            ? "bg-transparent"
            : "bg-white/95 backdrop-blur-md shadow-nav"
        )}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <div className="w-8 h-8 bg-primary-500 rounded-xl flex items-center justify-center shadow-sm">
                <Car size={16} className="text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">
                Safarim<span className="text-primary-500">.uz</span>
              </span>
            </Link>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-1">
              {(user?.is_driver ? DRIVER_LINKS : PASSENGER_LINKS).map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={clsx(
                    "px-4 py-2 rounded-xl text-sm font-medium transition-colors",
                    pathname === link.href
                      ? "text-primary-600 bg-primary-50"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {/* Right */}
            <div className="flex items-center gap-2">
              {user ? (
                <>
                  {/* Notifications */}
                  <Link
                    href="/notifications"
                    className="relative p-2 rounded-xl text-gray-500 hover:bg-gray-100 transition-colors"
                  >
                    <Bell size={20} />
                    {unreadCount > 0 && (
                      <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
                        {unreadCount > 9 ? "9+" : unreadCount}
                      </span>
                    )}
                  </Link>

                  {/* Create trip */}
                  {user.is_driver && (
                    <Link href="/create-trip" className="hidden sm:block">
                      <Button size="sm" className="gap-1.5">
                        <Plus size={15} />
                        Safar qo'shish
                      </Button>
                    </Link>
                  )}

                  {/* User dropdown */}
                  <div className="relative">
                    <button
                      onClick={() => setUserMenuOpen((p) => !p)}
                      className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-gray-100 transition-colors"
                    >
                      <Avatar src={user.profile_photo} name={user.full_name} size="sm" />
                      <ChevronDown
                        size={14}
                        className={clsx(
                          "text-gray-400 transition-transform hidden sm:block",
                          userMenuOpen && "rotate-180"
                        )}
                      />
                    </button>

                    {userMenuOpen && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setUserMenuOpen(false)} />
                        <div className="absolute right-0 top-full mt-2 w-52 bg-white rounded-2xl border border-gray-100 shadow-card-lg py-2 z-20 animate-scale-in">
                          <div className="px-4 py-2.5 border-b border-gray-50">
                            <p className="text-sm font-semibold text-gray-900 truncate">
                              {user.full_name}
                            </p>
                            <p className="text-xs text-gray-400 truncate">{user.phone}</p>
                          </div>
                          {[
                            { href: "/profile", icon: User, label: "Profilim" },
                            ...(user.is_driver
                              ? [
                                  { href: "/driver",      icon: Car,  label: "Panel" },
                                  { href: "/create-trip", icon: Plus, label: "Safar qo'shish" },
                                ]
                              : [
                                  { href: "/my-trips", icon: Car, label: "Safarlarim" },
                                ]),
                          ].map(({ href, icon: Icon, label }) => (
                            <Link
                              key={href}
                              href={href}
                              onClick={() => setUserMenuOpen(false)}
                              className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                            >
                              <Icon size={15} className="text-gray-400" />
                              {label}
                            </Link>
                          ))}
                          <div className="border-t border-gray-50 mt-1 pt-1">
                            <button
                              onClick={() => { setUserMenuOpen(false); logout(); }}
                              className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
                            >
                              <LogOut size={15} />
                              Chiqish
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <Link href="/login" className="hidden sm:block">
                    <Button variant="ghost" size="sm">Kirish</Button>
                  </Link>
                  <Link href="/register">
                    <Button size="sm">Ro'yxatdan o'tish</Button>
                  </Link>
                </>
              )}

              {/* Mobile hamburger */}
              <button
                onClick={() => setMobileOpen((p) => !p)}
                className="md:hidden p-2 rounded-xl text-gray-500 hover:bg-gray-100 transition-colors"
              >
                {mobileOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden bg-white border-t border-gray-100 animate-slide-up">
            <nav className="px-4 py-3 space-y-1">
              {(user?.is_driver ? DRIVER_LINKS : PASSENGER_LINKS).map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className={clsx(
                    "flex items-center px-4 py-3 rounded-xl text-sm font-medium transition-colors",
                    pathname === link.href
                      ? "text-primary-600 bg-primary-50"
                      : "text-gray-700 hover:bg-gray-50"
                  )}
                >
                  {link.label}
                </Link>
              ))}
              {!user && (
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center px-4 py-3 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Kirish
                </Link>
              )}
            </nav>
          </div>
        )}
      </header>

      {!transparent && <div className="h-16" />}
    </>
  );
}
