import { DocPage, DocSection, DocList } from "@/components/layout/DocPage";

export const metadata = { title: "Cookie siyosati — UzSafar" };

export default function CookiesPage() {
  return (
    <DocPage
      title="Cookie siyosati"
      updated="27-iyul, 2026"
      intro="UzSafar sayti to'g'ri ishlashi va foydalanishни qulay qilish uchun cookie (kuki) fayllaridan foydalanadi."
    >
      <DocSection heading="1. Cookie nima?">
        <p>
          Cookie — brauzeringizga saqlanadigan kichik matn fayli. U sizni tizimда saqlab turish,
          sozlamalarни eslab qolish va saytни yaxshiroq ishlashi uchun ishlatiladi.
        </p>
      </DocSection>

      <DocSection heading="2. Biz qanday cookie ishlatamiz">
        <DocList
          items={[
            "Zarur cookie'lar — tizimga kirish (token) va xavfsizlik uchun; ularsiz sayt ishlamaydi.",
            "Sozlama cookie'lari — til va afzalliklaringizни eslab qolish uchun.",
            "Tahliliy cookie'lar — saytdan qanday foydalanilishini tushunib, uni yaxshilash uchun.",
          ]}
        />
      </DocSection>

      <DocSection heading="3. Cookie'larni boshqarish">
        <p>
          Brauzeringiz sozlamalari orqали cookie'larni o'chirishingiz yoki bloklashingiz mumkin.
          Ammo zarur cookie'lar o'chirilса, tizimга kirish va bron kabi funksiyalar ishlamasligi mumkin.
        </p>
      </DocSection>

      <DocSection heading="4. Savollar">
        <p>Cookie siyosati bo'yicha savollar uchun: info@uzsafar.uz.</p>
      </DocSection>
    </DocPage>
  );
}
