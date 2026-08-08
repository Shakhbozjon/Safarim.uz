import Link from "next/link";
import Logo from "@/components/ui/Logo";

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

function Column({ title, items }: { title: string; items: { href: string; label: string }[] }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">{title}</div>
      <div className="flex flex-col gap-3 text-[14.5px]">
        {items.map((l) => (
          <Link key={l.href} href={l.href} className="text-gray-600 hover:text-primary-600 transition-colors">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-12 sm:pt-16 pb-7">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-10">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1 min-w-0">
            <Link href="/" className="inline-block mb-4">
              <Logo size={32} textSize="text-[17px]" />
            </Link>
            <p className="text-sm text-gray-500 leading-relaxed max-w-[280px] mb-4">
              O'zbekiston bo'ylab qulay va arzon safar. Haydovchi va yo'lovchilarni birlashtiruvchi platforma.
            </p>
            <div className="text-sm text-gray-500 leading-8">
              <div>+998 71 234 56 78</div>
              <div>info@uzsafar.uz</div>
              <div>Toshkent, O'zbekiston</div>
            </div>
          </div>

          <Column title="Platforma" items={links.platform} />
          <Column title="Kompaniya" items={links.company} />
          <Column title="Huquqiy" items={links.legal} />
        </div>

        <div className="mt-10 sm:mt-11 pt-6 border-t border-gray-100 text-[13px] text-gray-400">
          © {new Date().getFullYear()} UzSafar. Barcha huquqlar himoyalangan.
        </div>
      </div>
    </footer>
  );
}
