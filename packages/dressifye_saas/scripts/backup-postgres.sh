#!/usr/bin/env bash
# PostgreSQL mantıksal yedeği (gzip). DATABASE_URL ortam değişkeni gerekir.
set -euo pipefail
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL tanımlı değil." >&2
  exit 1
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/garment_core_db_${TS}.sql.gz"
pg_dump --no-owner --no-acl "$DATABASE_URL" | gzip >"$OUT"
echo "$OUT"
