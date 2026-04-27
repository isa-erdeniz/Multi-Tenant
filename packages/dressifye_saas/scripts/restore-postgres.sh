#!/usr/bin/env bash
# gzip'li pg_dump çıktısını DATABASE_URL veritabanına geri yükler.
# Kullanım: DATABASE_URL=... ./scripts/restore-postgres.sh ./backups/garment_core_db_XXX.sql.gz
set -euo pipefail
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL tanımlı değil." >&2
  exit 1
fi
if [[ $# -lt 1 ]]; then
  echo "Kullanım: DATABASE_URL=postgresql://... $0 <yedek.sql.gz>" >&2
  exit 1
fi
FILE="$1"
if [[ ! -f "$FILE" ]]; then
  echo "Dosya yok: $FILE" >&2
  exit 1
fi
gunzip -c "$FILE" | psql "$DATABASE_URL"
echo "Geri yükleme tamamlandı."
