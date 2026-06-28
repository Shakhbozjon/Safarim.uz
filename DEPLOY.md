# Safarim.uz — Production Deploy

## ⚡ Tezkor pilot (real foydalanuvchilar, SMS/domen shart emas)
Eng arzon real-sinov yo'li — bitta ~$5/oylik VPS (Hetzner/DigitalOcean), domensiz, IP orqali:
1. VPS oling, Docker o'rnating, kodni `git clone` qiling.
2. `cp .env.production.example .env.production` va to'ldiring. Pilot uchun:
   - `PILOT_MODE=true` → testerlar OTP'ni **ekranda** ko'radi (Eskiz SMS shart emas)
   - `MINIO_PUBLIC_ENDPOINT=SERVER_IP:9000` → rasm/avatar ko'rinadi
   - `CORS_ORIGINS=http://SERVER_IP` (yoki frontend manzili), `DEBUG=false`, kuchli kalitlar
   - Naqd-only: Click/Payme bo'sh qoldiring
3. `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`
4. Admin yarating (5-bo'lim), bir o'zingiz haydovchi bo'lib safar e'lon qiling, do'stlaringiz yo'lovchi bo'lib bron qilsin.
> ⚠️ `PILOT_MODE=true` faqat yopiq sinov uchun — OTP javobda ochiq ketadi. Haqiqiy ishga tushirishda `false` + Eskiz SMS.

---


Stack: Docker Compose orqali — PostgreSQL, Redis, MinIO, FastAPI (gunicorn), Celery (worker + beat),
Next.js (standalone), Nginx (HTTPS reverse proxy), avtomatik DB backup.

## 0. Talablar
- Linux server (Ubuntu 22.04+), Docker + Docker Compose plugin
- Domen `safarim.uz` A-record server IP ga yo'naltirilgan (www ham)
- 80 va 443 portlar ochiq

## 1. Kodni olish va env
```bash
git clone <repo> /opt/safarim && cd /opt/safarim
cp .env.production.example .env.production
nano .env.production   # barcha __TODO__ qiymatlarni to'ldiring
```
Kuchli kalitlar:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY, JWT_SECRET_KEY
```
`CORS_ORIGINS` ni real domeningizga, `DEBUG=false` ekanini tekshiring
(default kalit yoki CORS `*` bilan API ishga tushmaydi — bu ataylab).

## 2. Domenni Nginx konfiga yozish
`deploy/nginx/conf.d/safarim.conf` da `safarim.uz` ni 2 ta `server_name` va
`ssl_certificate` yo'llarida o'z domeningizga almashtiring.

## 3. HTTPS sertifikat (birinchi marta)
Avval faqat HTTP bilan nginx'ni ko'taring (yoki ACME challenge uchun), keyin certbot:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d nginx
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d safarim.uz -d www.safarim.uz \
  --email admin@safarim.uz --agree-tos --no-eff-email
docker compose -f docker-compose.prod.yml restart nginx
```
Sertifikat `certbot` xizmati orqali 12 soatda bir avtomatik yangilanadi.

## 4. To'liq stack'ni ko'tarish
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```
- API ishga tushganda `alembic upgrade head` avtomatik bajariladi (start-prod.sh).
- Holatni ko'rish: `docker compose -f docker-compose.prod.yml ps`
- Loglar: `docker compose -f docker-compose.prod.yml logs -f api`

## 5. MinIO bucket'lari va admin
```bash
# Buckets (bir marta) — MinIO console yoki mc bilan: documents, photos
# Super admin yaratish:
docker compose -f docker-compose.prod.yml exec api python scripts/create_admin.py
# Viloyat/tumanlar seed (agar kerak bo'lsa):
docker compose -f docker-compose.prod.yml exec api python -m app.scripts.seed   # (mavjud seed skriptingizga moslang)
```

## 6. Backup va tiklash
- Kunlik backup `backup` xizmati orqali `backup_data` volume'iga (`safarim_YYYYMMDD_*.sql.gz`), retention `BACKUP_RETENTION_DAYS`.
- Qo'lda backup: `docker compose -f docker-compose.prod.yml exec backup sh /usr/local/bin/backup.sh`
- Tiklash:
```bash
gunzip -c /path/backup.sql.gz | docker compose -f docker-compose.prod.yml exec -T db \
  psql -U $POSTGRES_USER -d $POSTGRES_DB
```
- Volume'ni server tashqarisiga (S3/boshqa) ko'chirib turish tavsiya etiladi.

## 7. Monitoring
- `SENTRY_DSN` ni `.env.production` ga qo'ying → xatolar Sentry'ga boradi.
- Healthcheck: `https://safarim.uz/api/health`
- Uptime kuzatuvi (UptimeRobot va sh.k.) shu endpointga.

## ⚠️ Hal qilinishi kerak (keyingi qadam)
**MinIO media URL** — hozir `storage_service` MinIO endpoint asosida URL yasaydi.
Prod'da MinIO ichki tarmoqda (`minio:9000`) — bu URL brauzerdan ochilmaydi.
Yechim variantlari: (a) MinIO uchun alohida public subdomen (masalan `cdn.safarim.uz`)
+ nginx proxy va `MINIO_ENDPOINT` shu domenga; (b) S3 (AWS/DigitalOcean Spaces).
`next.config.mjs` dagi `images.remotePatterns` ga shu domenni qo'shing.

## Foydali buyruqlar
```bash
# Faqat kodni yangilab qayta build:
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build api frontend
# Migratsiyani qo'lda:
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
# To'xtatish:
docker compose -f docker-compose.prod.yml down
```
