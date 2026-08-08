import type { Metadata } from "next";
import Link from "next/link";
import Logo from "@/components/ui/Logo";

export const metadata: Metadata = { title: "UzSafar — Kirish" };

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen gradient-hero flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center text-center mb-8">
          <Link href="/">
            <Logo size={44} textSize="text-2xl" />
          </Link>
          <p className="text-sm text-gray-500 mt-3">O'zbekiston bo'ylab arzon va qulay safar</p>
        </div>

        {/* Karta */}
        <div className="bg-white rounded-[18px] shadow-float border border-gray-100 p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
