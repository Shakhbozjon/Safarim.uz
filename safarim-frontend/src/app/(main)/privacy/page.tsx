import { DocPage, DocSection, DocList } from "@/components/layout/DocPage";

export const metadata = { title: "Maxfiylik siyosati — Safarim.uz" };

export default function PrivacyPage() {
  return (
    <DocPage
      title="Maxfiylik siyosati"
      updated="27-iyul, 2026"
      intro="Sizning shaxsiy ma'lumotlaringiz biz uchun muhim. Ushbu siyosat qanday ma'lumot yig'ishimiz va undan qanday foydalanishimizni tushuntiradi."
    >
      <DocSection heading="1. Qanday ma'lumot yig'amiz">
        <DocList
          items={[
            "Ism, telefon raqami va profil rasmi (ro'yxatdan o'tishda).",
            "Haydovchilar uchun: avtomobil ma'lumotlari va haydovchilik guvohnomasi.",
            "Safar, bron va to'lov tarixi.",
            "Qurilma va foydalanish ma'lumotlari (texnik xizmat sifati uchun).",
          ]}
        />
      </DocSection>

      <DocSection heading="2. Ma'lumotdan qanday foydalanamiz">
        <DocList
          items={[
            "Safar qidiruvi, bron va tomonlarni bog'lash uchun.",
            "Haydovchi hujjatlarini tekshirish va xavfsizlikni ta'minlash uchun.",
            "Bildirishnoma va xizmat sifatini yaxshilash uchun.",
          ]}
        />
      </DocSection>

      <DocSection heading="3. Ma'lumot ulashish">
        <p>
          Telefon raqami faqat bron tasdiqlangач ikkinchi tomonga (haydovchi/yo'lovchi) ko'rinadi.
          Biz sizning ma'lumotingizni uchinchi tomonlarга sotmaymiz. Ma'lumot faqat qonun talabiga
          binoan yoki xizmatni ta'minlash uchun zarur bo'lganda ulashilishi mumkin.
        </p>
      </DocSection>

      <DocSection heading="4. Saqlash va xavfsizlik">
        <p>
          Ma'lumotlar himoyalangan serverlarда saqlanadi. Parollar shifrlanган holda saqlanadi.
          Biz ma'lumotlarни ruxsatsiz kirishдан himoya qilish uchun texnik choralarни qo'llaymiz.
        </p>
      </DocSection>

      <DocSection heading="5. Sizning huquqlaringiz">
        <DocList
          items={[
            "O'z ma'lumotlaringizni ko'rish va tahrirlash.",
            "Hisobingizni o'chirishни so'rash.",
            "Ma'lumotdan foydalanish bo'yicha savol berish: info@safarim.uz.",
          ]}
        />
      </DocSection>

      <DocSection heading="6. O'zgartirishlar">
        <p>
          Ushbu siyosat yangilanishi mumkin. Muhim o'zgarishlar haqida sizni xabardor qilamiz.
        </p>
      </DocSection>
    </DocPage>
  );
}
