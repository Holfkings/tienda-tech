#!/usr/bin/env bash
# Backup diario de la base SQLite.
# NO modifica la DB: solo lee con ".backup" (copia consistente incluso con la app escribiendo).
# Uso:  bash scripts/backup_db.sh [ruta_db] [dir_backups]
#   en Railway:  bash scripts/backup_db.sh /data/tienda.db /data/backups
#   en local:    bash scripts/backup_db.sh ./tienda_dev.db ./backups
set -euo pipefail

DB_PATH="${1:-${DATABASE_PATH:-/data/tienda.db}}"
BACKUP_DIR="${2:-/data/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

if [ ! -f "$DB_PATH" ]; then
  echo "ERROR: no existe la DB en $DB_PATH" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
TARGET="$BACKUP_DIR/tienda-$STAMP.db"

sqlite3 "$DB_PATH" ".backup '$TARGET'"

# Verificar que el backup sea legible y tenga tablas (un backup vacio no sirve)
TABLES="$(sqlite3 "$TARGET" "SELECT count(*) FROM sqlite_master WHERE type='table';")"
SIZE="$(wc -c < "$TARGET" | tr -d ' ')"
if [ "$TABLES" -lt 1 ]; then
  echo "ERROR: el backup $TARGET no tiene tablas, se descarta" >&2
  rm -f "$TARGET"
  exit 1
fi

echo "OK backup: $TARGET (${SIZE} bytes, ${TABLES} tablas)"

# Retencion: borra backups mas viejos que RETENTION_DAYS (ESTE COMANDO SI ELIMINA ARCHIVOS)
find "$BACKUP_DIR" -name 'tienda-*.db' -type f -mtime "+${RETENTION_DAYS}" -print -delete

echo "Backups actuales:"
ls -lh "$BACKUP_DIR" | tail -n 10
