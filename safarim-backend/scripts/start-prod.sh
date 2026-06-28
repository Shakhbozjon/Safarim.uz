#!/bin/sh
# Production ishga tushirish: migratsiya + gunicorn (uvicorn worker'lar bilan).
set -e

echo "[start-prod] Migratsiyalar bajarilmoqda (alembic upgrade head)..."
alembic upgrade head

echo "[start-prod] Gunicorn ishga tushmoqda..."
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-3}" \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --timeout 60 \
  --graceful-timeout 30
