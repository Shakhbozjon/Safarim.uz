import { DocPage, DocSection, DocList } from "@/components/layout/DocPage";

export const metadata = { title: "Foydalanish shartlari — Safarim.uz" };

export default function TermsPage() {
  return (
    <DocPage
      title="Foydalanish shartlari"
      updated="27-iyul, 2026"
      intro="Safarim.uz platformasidan foydalanish orqali siz quyidagi shartlarga rozilik bildirasiz. Iltimos, diqqat bilan o'qing."
    >
      <DocSection heading="1. Umumiy qoidalar">
        <p>
          Safarim.uz — haydovchi va yo'lovchilarni bir-biriga bog'lovchi carpooling (birga
          sayohat) platformasi. Platforma faqat tomonlarni bog'laydi; safarning o'zi haydovchi
          va yo'lovchi o'rtasidagi shaxsiy kelishuvdir.
        </p>
      </DocSection>

      <DocSection heading="2. Hisob (akkaunt)">
        <DocList
          items={[
            "Ro'yxatdan o'tish uchun haqiqiy telefon raqami va to'g'ri ma'lumot talab qilinadi.",
            "Bir shaxs faqat bitta hisobga ega bo'lishi mumkin.",
            "Hisob ma'lumotlari maxfiyligi va undan foydalanish uchun javobgarlik egasiga tegishli.",
          ]}
        />
      </DocSection>

      <DocSection heading="3. Haydovchilar uchun">
        <DocList
          items={[
            "Haydovchi bo'lish uchun haydovchilik guvohnomasi va avtomobil ma'lumotlari tasdiqlanishi shart.",
            "Haydovchi e'lon qilingan vaqt, narx va yo'nalishga rioya qilishi kerak.",
            "Xavfsiz haydash, texnik soz avtomobil va yo'lovchilarга hurmat — majburiy.",
          ]}
        />
      </DocSection>

      <DocSection heading="4. Yo'lovchilar uchun">
        <DocList
          items={[
            "Yo'lovchi band qilingan safarga o'z vaqtida yetib borishi kerak.",
            "Naqd to'lov safar davomida haydovchiga to'g'ridan-to'g'ri beriladi.",
            "Haydovchi va boshqa yo'lovchilarга hurmat bilan munosabatda bo'lish talab qilinadi.",
          ]}
        />
      </DocSection>

      <DocSection heading="5. To'lov va komissiya">
        <p>
          Hozircha to'lov naqd amalga oshiriladi — yo'lovchi haydovchiga to'g'ridan-to'g'ri
          to'laydi. Platforma o'z komissiyasini haydovchining oldindan to'ldirilган depozitidan
          safar yakunlangач ushlab qoladi. Komissiya safar narxiga qarab 2–5% ni tashkil etadi.
        </p>
      </DocSection>

      <DocSection heading="6. Bekor qilish">
        <p>
          Safar jo'nashidan oldin bekor qilinishi mumkin. Jo'nash vaqti boshlangач bekor qilib
          bo'lmaydi — bunday holatda safar bo'lgan/bo'lmagani tasdiq oqimi orqали aniqlanadi.
        </p>
      </DocSection>

      <DocSection heading="7. Taqiqlangan xatti-harakatlar">
        <DocList
          items={[
            "Soxta ma'lumot, boshqa shaxs nomidan ro'yxatdan o'tish.",
            "Platformadan tashqari to'lov yoki komissiyadan qochish uchun soxta belgilash.",
            "Qonunga zid yuk yoki xizmat tashish.",
          ]}
        />
      </DocSection>

      <DocSection heading="8. Javobgarlik">
        <p>
          Safarim.uz tomonlarни bog'lovchi vosita sifatida ishlaydi va safar davomidagi kelishmovchilik,
          kechikish yoki zarar uchun bevosita javobgar emas. Nizolar tasdiq va admin ko'rigи orqали hal
          qilinadi.
        </p>
      </DocSection>

      <DocSection heading="9. O'zgartirishlar">
        <p>
          Ushbu shartlar vaqti-vaqti bilan yangilanishi mumkin. Muhim o'zgarishlar haqida
          foydalanuvchilar xabardor qilinadi. Savollar bo'lsa: info@safarim.uz.
        </p>
      </DocSection>
    </DocPage>
  );
}
