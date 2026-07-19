# Safarim.uz — Handoff (professional-grade ishlar uchun)

Bu hujjat yangi sessionга (Fable 5) davomiylikни ta'minlaydi. Xotira (`MEMORY.md`, `project-safarim.md`, `deployment-live.md`) avtomatik yuklanadi.

## Hozirgi holat (2026-07)
- Sayt **JONLI**: `http://34.185.192.138` (GCP VM, Docker Compose, PILOT_MODE, naqd-only, HTTP).
- Uchidan-uchiga tasdiqlangan: ro'yxatdan o'tish (OTP ekranда), seed (14 viloyat+tumanlar), admin (`+998901112233`).
- GitHub: github.com/Shakhbozjon/Safarim.uz. Server: `~/Safarim.uz`. Deploy: `docker-compose.pilot.yml`.
- **Fable 5 chuqur audit BAJARILDI** — natijalar pastda (fix checklist).

## Deploy/yangilash oqimi
```bash
# Lokalda: o'zgartir → git push origin main
# Serverda (SSH, ~/Safarim.uz):
git pull && docker compose -f docker-compose.pilot.yml --env-file .env.production up -d --build
docker compose -f docker-compose.pilot.yml --env-file .env.production logs api --tail 30
```
## Testlar (lokal)
```bash
cd safarim-backend && venv/Scripts/python.exe -m pytest -q    # hozir 59 passed
```

## Reja
A. Sayt ishlaydigan ✅ | **C. Audit ✅ (pastda)** | Keyingi: buglarni tuzatish → D. testlar → B. jonli E2E → E. mustahkamlash.
⚠️ GCP firewall port 9000 hali ochilmagan (rasm/avatar ko'rinmaydi).

---

# 🔴 AUDIT FIX CHECKLIST (Fable 5) — eng muhimidan boshlab

Har biri: `file:line` — muammo — tuzatish. Har fixdan keyin lokal test + `git push` + serverда rebuild.

## CRITICAL — pul/firibgarlik (real user pulga tegishdan OLDIN) — ✅ HAMMASI TUZATILDI (2026-07-19)
- [x] **Tekshirilmagan wallet self-topup** — endpoint butunlay o'chirildi (`drivers.py`). Haqiqiy oqim `/topup/pay` + callback qoldi.
- [x] **To'lanmagan online bron hamyonga daromad yozadi** — `_apply_completion` endi `payment_status`ни o'zi paid qilmaydi; online faqat callback orqali paid bo'lsa `add_earning`, aks holda naqd kabi komissiya ushlanadi.
- [x] **Click wallet-topup callback amount tekshirmaydi** — Click topup PREPARE+COMPLETE'da `abs(topup.amount-amount)>1` → rad; `_payme_create`ga topup VA booking branch'ida amount tekshiruvi qo'shildi.
- [x] **Seat-count race** — `create_booking` va `cancel_booking` seat qaytarishда `with_for_update(of=Trip)`; booking row'lariga ham lock (double-resolution himoyasi — MEDIUM lock item ham yopildi).
- [x] **Refund umuman bajarilmaydi** — `flag_refund_due()` qo'shildi: online to'langan bron bekor bo'lsa `payment_status=refunded` + adminга Telegram "Refund kerak (qo'lda)" xabari. Naqd bronда endi refund_amount=0 (hech narsa to'lanmagan). Joylar: cancel_booking, cancel_trip, _apply_not_happened, expire_due_trips.
- [x] **PILOT_MODE OTP har kimga** — `PILOT_OTP_ALLOWLIST` sozlamasi qo'shildi (vergulli raqamlar ro'yxati). Bo'sh bo'lsa eski xatti-harakat (hamma oladi); to'ldirilsa faqat allowlist'дагиlar `pilot_otp` oladi, qolganlarга Telegram orqali boradi. ⚠️ **Serverда `.env.production`га `PILOT_OTP_ALLOWLIST=+998...,+998...` qo'shish kerak!**

## HIGH — buzilgan asosiy oqim / ekspluatatsiya
- [ ] **Payme CancelTransaction hamyonни qaytarib olmaydi** — `payment_service.py:550-573` — refund qilinsа bron/seat/wallet daromad orqага qaytmaydi; topup case topilmaydi. **Fix:** completed to'lov cancel'да `payment_status=refunded` + `add_earning`ни teskari + topup case.
- [ ] **To'lov COMPLETE bekor qilinган bronни tiriltiradi** — `payment_service.py:313-324,493-541` — COMPLETE/Perform bron statusини tekshirmay `confirmed` qiladi. **Fix:** bron cancelled bo'lsа cancelled-error qaytar (Payme -31007/Click -9).
- [x] **Jo'nashдан keyin bekor qilish mumkin** — ✅ (2026-07-19) `cancel_booking` va bronli `cancel_trip` jo'nashdan keyin 400 qaytaradi (tasdiq oqimi hal qiladi).
- [x] **Timezone UTC vs Asia/Tashkent** — ✅ (2026-07-19) `app/core/timeutils.py` → `now_tashkent_naive()` helper; barcha departure_dt solishtiruvlari (cancel, confirm, expire, request_due) shu orqali. DB timestamp'lar UTC'da qoldi.
- [ ] **`driver_denied_reprompt_at` yozilib, o'qilmaydi** — `booking_service.py:484` vs `609-626` — haydovchi kech "Yo'q" bossа, yo'lovchining 48s e'tiroz oynаси ~0. **Fix:** `resolve_due_confirmations`да `driver_confirmed=='no'` bo'lса `driver_denied_reprompt_at<=now-48h` shart.
- [ ] **Login brute-force X-Forwarded-For orqali bypass** — `core/ratelimit.py:16-21,48-50` — XFF'га ishonadi. **Fix:** nginx `X-Real-IP` o'rnatsin, faqat shunга ishon; per-phone login limiter qo'sh.
- [ ] **To'lov statusи IDOR** — `api/v1/payments.py:35-54` — `GET /payments/{booking_id}` ownership tekshirmaydi. **Fix:** `get_booking` kabi passenger/driver/admin tekshiruvi.

## MEDIUM
- [x] **Confirmation double-resolution → komissiya 2 marta** — ✅ (2026-07-19) `with_for_update(of=Booking)` qo'shildi: confirm_booking, cancel_booking, admin_resolve_dispute, resolve_due_confirmations (skip_locked).
- [ ] **Waypoint narx validatsiyasiz — 0/manfiy narx** — `schemas/trip.py:14-21`, `booking_service.py:100`. **Fix:** `price_from_start>=0` va order bo'yicha o'suvchi; `price_per_seat<1000` rad.
- [ ] **`initiate_payment` naqd bronда ham ishlaydi** — `payment_service.py:162-212`. **Fix:** `payment_method==cash` bo'lsа rad.
- [ ] **No-show online'да 0% qoidаси buzilgan** — `booking_service.py:318-331` — online no-show `refund=total_price`. **Fix:** "safar bo'lmadi"(to'liq) vs "no-show"(0%) ajrat.
- [ ] **Withdraw pulни yo'qotadi (payout yo'q)** — `drivers.py:270-285`. **Fix:** pending withdrawal-request + admin bildirishnoma; admin tasdiqлаganда deduct.
- [ ] **Real bronli safar hech qachon `completed` bo'lmaydi** — hech joyда `TripStatus.completed` qo'yilmaydi. **Fix:** o'tган safarnینг barcha bronlari terminal bo'lса → `completed`.
- [ ] **Frontend refresh-fail redirect noto'g'ri** — `lib/api.ts:38` `/auth/login` → 404. **Fix:** `/login`.
- [ ] **Forgot-password oqimi yo'q** — `users.py:92-104` — faqat login bilan. **Fix:** unauth `POST /auth/reset-password` (phone+OTP+yangi parol).
- [ ] **Reyting auto-block butun akkauntни bloklaydi + warning_count shishadi + AdminAction.admin_id noto'g'ri** — `review_service.py:144-162`. **Fix:** userни emas, driver profilни pauza; warning bir marta; system admin id.
- [ ] **Yangi bron bildirishnomаси ref_id=NULL** — `booking_service.py:106-148` — flush'дан oldin. **Fix:** `db.add(booking)` dan keyin `await db.flush()`.
- [ ] **Tokenlar JS-ochiq cookie, Secure/SameSite yo'q** — `lib/auth.ts:5-8`. **Fix:** `sameSite:"lax"`; HTTPS kelганда httpOnly.

## LOW
- [ ] Invalid UUID → 500 (`booking_service.py:190,454`, `review_service.py:37`) — try/except → 400.
- [ ] `validate_regions_different` no-op (`schemas/trip.py:94-97`).
- [ ] Open redirect `?next=` (`login/page.tsx:48`) — faqat ichki path'ga ruxsat.
- [ ] Monthly commission oy chegараси UTC (`booking_service.py:159`); `payment_service.record_cash_commission:605` dead/duplicate.
- [ ] `expire_due_trips` pending bronда seat qaytarmaydi (`trip_service.py:329-350`).
- [ ] Chat `awaiting_confirmation`/`disputed`да yopiq (`message_service.py:46-51`) — nizoда yozisholmaydi.
- [ ] Refresh endpoint userни qayta tekshirmaydi (`auth.py:66-82`).
- [ ] `get_click_url` return_url `https://safarim.uz` hardcode (`payment_service.py:25-35`) — pilot IP-only.

## Toza (bug yo'q): JWT (`core/security.py`), OTP single-use/expiry, admin authz (backend), WebSocket access control, komissiya formulаси, fake-strike mantiqi.

## TOP 5 (pulga tegishdan oldin) — ✅ HAMMASI BAJARILDI (2026-07-19, testlar 59 passed)
1. ~~topup endpointни o'chir~~ ✅
2. ~~`add_earning`ни verified payment bilan gate qil~~ ✅
3. ~~Click topup callback amount tekshir~~ ✅ (+ Payme create'да ham)
4. ~~`create_booking`да trip row-lock~~ ✅ (+ cancel, confirm, dispute, resolve loop)
5. ~~Jo'nashdan keyin cancelни bloklа + UTC/Tashkent tuzat~~ ✅ (`core/timeutils.py`)

⚠️ Deploy eslatmasi: serverда `.env.production`га `PILOT_OTP_ALLOWLIST=+998901112233,...` (tester raqamlari) qo'shib rebuild qiling — aks holda OTP hali ham hammaga qaytadi (eski xatti-harakat).
