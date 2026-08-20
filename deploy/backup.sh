#!/bin/sh
# Respaldo diario de la base de datos (pg_dump), con rotación de 14 días.
# Se corre por cron como el usuario blutesa: 0 2 * * * /opt/blutesa-kardex/deploy/backup.sh
set -eu

APP_DIR=/opt/blutesa-kardex
BACKUP_DIR="$APP_DIR/backups"
DIAS_A_CONSERVAR=14

# shellcheck disable=SC1090
. "$APP_DIR/.env"

mkdir -p "$BACKUP_DIR"

FECHA=$(date +%Y%m%d_%H%M%S)
ARCHIVO="$BACKUP_DIR/blutesa_kardex_${FECHA}.dump"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "${POSTGRES_HOST:-127.0.0.1}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "$POSTGRES_USER" \
    -Fc \
    -f "$ARCHIVO" \
    "$POSTGRES_DB"

find "$BACKUP_DIR" -name 'blutesa_kardex_*.dump' -mtime "+$DIAS_A_CONSERVAR" -delete
