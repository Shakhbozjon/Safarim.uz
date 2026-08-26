#!/usr/bin/env bash
# UzSafar - Telegram tasdiqlashni sozlash va deploy.
# Bir marta ishga tushiriladi; qayta ishga tushirilsa zarar qilmaydi.
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

# 1 - Token
step "1/6  Token"
TOKEN=$(getv TELEGRAM_BOT_TOKEN)
if [ -z "$TOKEN" ]; then
  bad "TELEGRAM_BOT_TOKEN bosh. BotFather tokenini $ENV ga qoying."
  exit 1
fi

cp "$ENV" "$ENV.bak"
INFO=$(curl -s --max-time 15 "$API$TOKEN/getMe")
case "$INFO" in
  *'"ok":true'*) : ;;
  *) bad "Tokenni Telegram qabul qilmadi. BotFather'dan qaytadan nusxalang."; exit 1 ;;
esac

BOTNAME=$(printf "%s" "$INFO" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
ok "Bot: @$BOTNAME"

# 2 - Username
step "2/6  Bot username"
if [ "$(getv TELEGRAM_BOT_USERNAME)" = "$BOTNAME" ]; then
  ok "allaqachon togri"
else
  setv TELEGRAM_BOT_USERNAME "$BOTNAME"
  ok "yozildi: $BOTNAME"
fi

# 3 - Webhook siri
step "3/6  Webhook siri"
SECRET=$(getv TELEGRAM_WEBHOOK_SECRET)
if [ -z "$SECRET" ]; then
  SECRET=$(openssl rand -hex 32)
  setv TELEGRAM_WEBHOOK_SECRET "$SECRET"
  ok "yangi sir yaratildi"
else
  ok "mavjud sir ishlatiladi"
fi

# 4 - Deploy
step "4/6  Deploy (bir necha daqiqa)"
git pull --ff-only || { bad "git pull bajarilmadi"; exit 1; }
$DC up -d --build api celery celery-beat frontend || { bad "build bajarilmadi"; exit 1; }
$DC restart nginx >/dev/null 2>&1
ok "konteynerlar yangilandi"

printf "   sayt kotarilishini kutamiz"
CODE=000
for _ in $(seq 1 40); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://uzsafar.uz/ || echo 000)
  if [ "$CODE" = "200" ]; then break; fi
  printf "."
  sleep 3
done
printf "\n"
if [ "$CODE" = "200" ]; then
  ok "sayt javob beryapti"
else
  bad "sayt javob bermadi (kod $CODE)"
fi

# 5 - Webhook royxatdan otkazish
step "5/6  Webhook royxatdan otkazilmoqda"
RES=$(curl -s --max-time 15 -X POST "$API$TOKEN/setWebhook" \
  -d "url=https://uzsafar.uz/api/v1/telegram/webhook" \
  -d "secret_token=$SECRET")
case "$RES" in
  *'"ok":true'*) ok "webhook ornatildi" ;;
  *) bad "webhook ornatilmadi: $RES" ;;
esac

# 6 - Tekshiruv
step "6/6  Yakuniy tekshiruv"
WI=$(curl -s --max-time 15 "$API$TOKEN/getWebhookInfo")
WURL=$(printf "%s" "$WI" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')
WERR=$(printf "%s" "$WI" | sed -n 's/.*"last_error_message":"\([^"]*\)".*/\1/p')

if [ -n "$WURL" ]; then ok "manzil: $WURL"; else bad "webhook manzili bosh"; fi

if [ -n "$WERR" ]; then
  bad "Telegram xatosi: $WERR"
  case "$WERR" in
    *403*) echo "          -> sir mos kelmayapti; skriptni qayta ishga tushiring" ;;
    *502*) echo "          -> $DC restart nginx" ;;
    *)     echo "          -> $DC logs api --tail 30" ;;
  esac
else
  ok "Telegram tomonida xato yoq"
fi

CONF=$($DC exec -T api python -c 'from app.core.config import settings; print(int(bool(settings.TELEGRAM_BOT_TOKEN)), int(bool(settings.TELEGRAM_BOT_USERNAME)), int(bool(settings.TELEGRAM_WEBHOOK_SECRET)))' 2>/dev/null | tr -d '\r')
if [ "$CONF" = "1 1 1" ]; then
  ok "konteyner sozlamalarni koryapti"
else
  bad "konteynerda sozlama yetishmayapti (token/username/secret = ${CONF:-javob yoq})"
  echo "          -> $DC up -d --force-recreate api"
fi

printf "\n== TAYYOR\n"
echo "   Telefonda: uzsafar.uz -> Profil -> Raqamni tasdiqlash"
echo "   Bot: https://t.me/$BOTNAME"
