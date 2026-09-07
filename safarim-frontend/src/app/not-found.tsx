import Link from "next/link";
import { Compass } from "lucide-react";

/**
 * 404. Ilgari bu fayl yo'q edi va Next'ning inglizcha default sahifasi
 * chiqardi ("This page could not be found") — o'zbek tilidagi saytda bu
 * xatoning o'zidan ko'ra yomonroq taassurot qoldirardi.
 */
export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <Compass size={30} className="text-primary-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Sahifa topilmadi</h1>
        <p className="text-[15px] text-gray-500 mb-7">
          Havola eskirgan yoki noto&apos;g&apos;ri yozilgan bo&apos;lishi mumkin.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-primary-500 text-white font-semibold hover:bg-primary-600 transition-colors"
          >
            Bosh sahifa
          </Link>
          <Link
            href="/trips"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-gray-100 text-gray-800 font-semibold hover:bg-gray-200 transition-colors"
          >
            Safar qidirish
          </Link>
        </div>
      </div>
    </div>
  );
}
