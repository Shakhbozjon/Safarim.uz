#!/bin/sh
# PostgreSQL avtomatik backup (retention bilan). Cron yoki compose backup xizmatidan chaqiriladi.
#
# Kerakli env: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
# Ixtiyoriy: BACKUP_DIR (default /backups), BACKUP_RETENTION_DAYS (default 14)
set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/safarim_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] ${PGDATABASE} → ${OUT}"
pg_dump --no-owner --no-privileges | gzip > "$OUT"

echo "[backup] ${RETENTION_DAYS} kundan eski backuplar tozalanmoqda..."
find "$BACKUP_DIR" -name "safarim_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[backup] Tayyor. Mavjud backuplar:"
ls -lh "$BACKUP_DIR" | tail -n +2
