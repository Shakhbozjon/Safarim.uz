#!/usr/bin/env bash
# UzSafar - saytdagi "Bog'lanish" xabarlari keladigan Telegram chatni sozlash.
#
# Forma xabarni TELEGRAM_ADMIN_CHAT_ID ga yuboradi. U bo'sh bo'lsa foydalanuvchi
# "Hozircha xabar yuborib bo'lmaydi" degan javobni oladi. Chat ID ni qo'lda
# topish oson emas (webhook o'rnatilgan bo'lsa getUpdates ishlamaydi), shuning
# uchun skript webhookni vaqtincha olib turadi, sizning xabaringizni kutadi,
# ID ni .env.production ga yozadi va webhookni joyiga qaytaradi.
#
# Ishlatish (serverda):  bash deploy/set-admin-chat.sh
set -uo pipefail

cd ~/Safarim.uz || { echo "XATO: ~/Safarim.uz topilmadi"; exit 1; }

ENV=.env.production
API="https://api.telegram.org/bot"

step() { printf "\n== %s\n" "$1"; }
ok()   { printf "   [OK]   %s\n" "$1"; }
bad()  { printf "   [XATO] %s\n" "$1"; }

getv() { grep -E "^$1=" "$ENV" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r'; }

setv() {
  if grep -qE "^$1=" "$ENV"; then
    sed -i "s|^$1=.*|$1=$2|" "$ENV"
  else
    printf "%s=%s\n" "$1" "$2" >> "$ENV"
  fi
}

# 0 - Qaysi stack ishlayapti (prod yoki pilot)
step "0/5  Stack"
COMPOSE=docker-compose.prod.yml
if [ -z "$(docker compose -f docker-compose.prod.yml --env-file $ENV ps -q api 2>/dev/null)" ]; then
  COMPOSE=docker-compose.pilot.yml
fi
DC="docker compose -f $COMPOSE --env-file $ENV"
if [ -z "$($DC ps -q api 2>/dev/null)" ]; then
  bad "ishlab turgan api konteyner topilmadi. Avval stackni ko'taring."
  exit 1
fi
ok "$COMPOSE"

# 1 - Token
step "1/5  Token"
TOKEN=$(getv TELEGRAM_BOT_TOKEN)
if [ -z "$TOKEN" ]; then
  bad "TELEGRAM_BOT_TOKEN bo'sh. Avval: bash deploy/setup-telegram.sh"
  exit 1
fi
INFO=$(curl -s --max-time 15 "$API$TOKEN/getMe")
case "$INFO" in
  *'"ok":true'*) : ;;
  *) bad "Tokenni Telegram qabul qilmadi."; exit 1 ;;
esac
BOTNAME=$(printf "%s" "$INFO" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
ok "Bot: @$BOTNAME"

CURRENT=$(getv TELEGRAM_ADMIN_CHAT_ID)
if [ -n "$CURRENT" ]; then
  ok "hozirgi qiymat: $CURRENT (qayta yozamiz)"
fi

cp "$ENV" "$ENV.bak"

# 2 - Webhookni vaqtincha olib turamiz (getUpdates u bilan birga ishlamaydi)
step "2/5  Webhook vaqtincha olinadi"
curl -s --max-time 15 -X POST "$API$TOKEN/deleteWebhook" >/dev/null
ok "olindi (oxirida qaytariladi)"

restore_webhook() {
  SECRET=$(getv TELEGRAM_WEBHOOK_SECRET)
  RES=$(curl -s --max-time 15 -X POST "$API$TOKEN/setWebhook" \
    -d "url=https://uzsafar.uz/api/v1/telegram/webhook" \
    -d "secret_token=$SECRET")
  case "$RES" in
    *'"ok":true'*) ok "webhook qaytarildi" ;;
    *) bad "webhook qaytarilmadi: $RES"; echo "          -> bash deploy/setup-telegram.sh" ;;
  esac
}
trap 'echo; bad "toxtatildi"; restore_webhook; exit 1' INT TERM

# 3 - Xabaringizni kutamiz
step "3/5  Telegramda @$BOTNAME ga istalgan xabar yuboring"
echo "   Havola: https://t.me/$BOTNAME   (masalan \"salom\" deb yozing)"
echo "   Kutamiz (2 daqiqagacha)..."

CHAT=""
for _ in $(seq 1 12); do
  UPD=$(curl -s --max-time 20 "$API$TOKEN/getUpdates?timeout=10&allowed_updates=%5B%22message%22%5D")
  CHAT=$(printf "%s" "$UPD" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit()
for u in reversed(d.get("result", [])):
    m = u.get("message") or {}
    c = m.get("chat") or {}
    if c.get("type") == "private" and c.get("id"):
        print(c["id"])
        break
' 2>/dev/null | tr -d '\r')
  [ -n "$CHAT" ] && break
  printf "."
done
printf "\n"

if [ -z "$CHAT" ]; then
  bad "xabar kelmadi. Skriptni qayta ishga tushiring va botga yozing."
  restore_webhook
  exit 1
fi
ok "chat ID: $CHAT"

# 4 - Yozib, konteynerlarni yangilaymiz
step "4/5  .env.production va konteynerlar"
setv TELEGRAM_ADMIN_CHAT_ID "$CHAT"
ok "TELEGRAM_ADMIN_CHAT_ID=$CHAT yozildi"
restore_webhook
trap - INT TERM

# env_file faqat konteyner qayta yaratilganda o'qiladi - restart yetmaydi.
$DC up -d --force-recreate api celery celery-beat >/dev/null 2>&1 || {
  bad "konteynerlarni yangilab bo'lmadi"; exit 1; }
$DC restart nginx >/dev/null 2>&1
ok "api/celery qayta yaratildi, nginx restart qilindi"

# 5 - Tekshiruv
step "5/5  Tekshiruv"
SEEN=$($DC exec -T api python -c 'from app.core.config import settings; print(settings.TELEGRAM_ADMIN_CHAT_ID or "BOSH")' 2>/dev/null | tr -d '\r')
if [ "$SEEN" = "$CHAT" ]; then
  ok "konteyner ko'ryapti: $SEEN"
else
  bad "konteynerda qiymat boshqacha: ${SEEN:-javob kelmadi}"
fi

curl -s --max-time 15 -X POST "$API$TOKEN/sendMessage" \
  -d "chat_id=$CHAT" \
  -d "text=UzSafar: bog'lanish formasi shu chatga xabar yuboradi." >/dev/null
ok "sinov xabari yuborildi - Telegramni tekshiring"

printf "\n== TAYYOR\n"
echo "   Saytda: uzsafar.uz -> Bog'lanish -> xabar yozib yuboring."
