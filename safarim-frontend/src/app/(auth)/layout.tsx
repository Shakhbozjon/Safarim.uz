import type { Metadata } from "next";

export const metadata: Metadata = { title: "Safarim.uz — Kirish" };

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-orange-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
              <span className="text-white text-xl font-bold">S</span>
            </div>
            <span className="text-2xl font-bold text-gray-900">Safarim.uz</span>
          </div>
          <p className="text-sm text-gray-500">O'zbekiston bo'ylab arzon va qulay safar</p>
        </div>

        {/* Karta */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-100/80 border border-gray-100 p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
