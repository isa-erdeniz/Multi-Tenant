#!/usr/bin/env bash
# Veritabanı + Drizzle migrasyon dosyaları + şema kaynakları arşivi.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "Veritabanı yedeği alınıyor..."
  (cd "$ROOT" && DATABASE_URL="$DATABASE_URL" BACKUP_DIR="$BACKUP_DIR" bash scripts/backup-postgres.sh)
else
  echo "DATABASE_URL yok; yalnızca dosya arşivi alınacak." >&2
fi

ARCH="$BACKUP_DIR/garment_core_bundle_${TS}.tar.gz"
tar -czf "$ARCH" \
  -C "$ROOT" \
  drizzle \
  drizzle.config.ts \
  src/db/schema \
  package.json \
  VERSION
echo "$ARCH"
