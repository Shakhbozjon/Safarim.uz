import Link from "next/link";
import { Car, Phone, Mail, MapPin } from "lucide-react";

const links = {
  platform: [
    { href: "/trips", label: "Safarlar" },
    { href: "/create-trip", label: "Safar qo'shish" },
    { href: "/how-it-works", label: "Qanday ishlaydi" },
  ],
  company: [
    { href: "/about", label: "Biz haqimizda" },
    { href: "/safety", label: "Xavfsizlik" },
    { href: "/blog", label: "Blog" },
  ],
  legal: [
    { href: "/terms", label: "Foydalanish shartlari" },
    { href: "/privacy", label: "Maxfiylik siyosati" },
    { href: "/cookies", label: "Cookie siyosati" },
  ],
};

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-14">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="w-9 h-9 bg-primary-500 rounded-xl flex items-center justify-center">
                <Car size={18} className="text-white" />
              </div>
              <span className="text-xl font-bold text-white">
                Safarim<span className="text-primary-400">.uz</span>
              </span>
            </Link>
            <p className="text-sm text-gray-400 leading-relaxed mb-5">
              O'zbekiston bo'ylab qulay va arzon safar. Haydovchi va yo'lovchilarni birlashtiruvchi platforma.
            </p>
            <div className="space-y-2">
              <a href="tel:+998712345678" className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
                <Phone size={14} />+998 71 234 56 78
              </a>
              <a href="mailto:info@safarim.uz" className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
                <Mail size={14} />info@safarim.uz
              </a>
              <span className="flex items-center gap-2 text-sm text-gray-400">
                <MapPin size={14} />Toshkent, O'zbekiston
              </span>
            </div>
          </div>

          {/* Platform */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Platforma</h4>
            <ul className="space-y-3">
              {links.platform.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-gray-400 hover:text-white transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Kompaniya</h4>
            <ul className="space-y-3">
              {links.company.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-gray-400 hover:text-white transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Huquqiy</h4>
            <ul className="space-y-3">
              {links.legal.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-gray-400 hover:text-white transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-500">
            © {new Date().getFullYear()} Safarim.uz. Barcha huquqlar himoyalangan.
          </p>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <span>O'zbek tilida</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
