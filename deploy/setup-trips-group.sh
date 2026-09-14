#!/usr/bin/env bash
# UzSafar - safar e'lonlari tashlanadigan Telegram guruhini sozlash.
# Bir marta ishga tushiriladi; qayta ishga tushirilsa zarar qilmaydi.
#
# Ishlatish:
#   bash deploy/setup-trips-group.sh @uzsafar_qoqon
#
# Nega getUpdates emas: botda webhook yoqilgan, getUpdates esa o'shanda
# 409 Conflict qaytaradi. Guruh ochiq (public username bilan) bo'lgani uchun
# chat ID sini getChat orqali olamiz - webhook'ga tegmaydi.
set -uo pipefail

cd ~/Safarim.uz || { echo "XATO: ~/Safarim.uz topilmadi"; exit 1; }

ENV=.env.production
DC="docker compose -f docker-compose.prod.yml --env-file $ENV"
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

jsonval() { printf "%s" "$2" | sed -n "s/.*\"$1\":\([-0-9]*\).*/\1/p" | head -1; }

GROUP="${1:-}"
if [ -z "$GROUP" ]; then
  bad "Guruh nomini bering, masalan: bash deploy/setup-trips-group.sh @uzsafar_qoqon"
  exit 1
fi
case "$GROUP" in @*) : ;; *) GROUP="@$GROUP" ;; esac

# 1 - Token
step "1/5  Token"
TOKEN=$(getv TELEGRAM_BOT_TOKEN)
if [ -z "$TOKEN" ]; then
  bad "TELEGRAM_BOT_TOKEN bosh - avval: bash deploy/setup-telegram.sh"
  exit 1
fi
ok "token joyida"

# 2 - Guruh ID si
step "2/5  Guruh ID si ($GROUP)"
CHAT_JSON=$(curl -s --max-time 15 "$API$TOKEN/getChat?chat_id=$GROUP")
case "$CHAT_JSON" in
  *'"ok":true'*) : ;;
  *)
    bad "guruh topilmadi"
    echo "          -> guruh OCHIQ (public) bo'lishi va username to'g'ri bo'lishi kerak"
    echo "          -> javob: $(printf '%s' "$CHAT_JSON" | head -c 200)"
    exit 1
    ;;
esac
CHAT_ID=$(jsonval id "$CHAT_JSON")
if [ -z "$CHAT_ID" ]; then
  bad "chat ID o'qilmadi: $(printf '%s' "$CHAT_JSON" | head -c 200)"
  exit 1
fi
ok "chat ID: $CHAT_ID"

# 3 - Bot admin bo'lishi shart
step "3/5  Bot guruhda adminmi"
ME=$(curl -s --max-time 15 "$API$TOKEN/getMe")
BOT_ID=$(jsonval id "$ME")
MEMBER=$(curl -s --max-time 15 "$API$TOKEN/getChatMember?chat_id=$CHAT_ID&user_id=$BOT_ID")
case "$MEMBER" in
  *'"status":"administrator"'*|*'"status":"creator"'*)
    ok "bot admin - yoza oladi"
    ;;
  *)
    bad "bot admin emas - guruhga e'lon tasholmaydi"
    echo "          -> Telegram: guruh -> Administrators -> Add Admin -> botni qo'shing"
    exit 1
    ;;
esac

# 4 - Sinov xabari
step "4/5  Sinov xabari"
SEND=$(curl -s --max-time 15 -X POST "$API$TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"$CHAT_ID\",\"text\":\"UzSafar: lenta ulandi. Safar e'lonlari shu yerga chiqadi.\",\"disable_notification\":true}")
case "$SEND" in
  *'"ok":true'*) ok "guruhga xabar tushdi (tekshiring)" ;;
  *) bad "yuborilmadi: $(printf '%s' "$SEND" | head -c 200)"; exit 1 ;;
esac

# 5 - Sozlamani yozish va qayta ko'tarish
step "5/5  Sozlama"
setv TELEGRAM_TRIPS_CHAT_ID "$CHAT_ID"
ok "$ENV ga yozildi"

$DC up -d --force-recreate api >/dev/null 2>&1
CONF=$($DC exec -T api python -c 'from app.services import telegram_service; print(int(telegram_service.trips_chat_configured()))' 2>/dev/null | tr -d '\r')
if [ "$CONF" = "1" ]; then
  ok "konteyner lentani ko'ryapti"
else
  bad "konteynerda sozlama yetishmayapti (javob: ${CONF:-javob yoq})"
  echo "          -> $DC up -d --force-recreate api"
fi

printf "\n== TAYYOR\n"
echo "   Haydovchi safar e'lon qilsa, e'lon $GROUP ga ovozsiz chiqadi."
echo "   O'rin tugasa yoki safar bekor qilinsa - o'sha post tahrirlanadi."
echo "   O'chirish: $ENV da TELEGRAM_TRIPS_CHAT_ID= ni bo'sh qoldiring."
