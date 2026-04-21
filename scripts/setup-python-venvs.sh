#!/usr/bin/env bash
# Multi-Tenant altındaki Python projeleri için .venv oluşturur ve bağımlılıkları kurar.
# Kullanım: bash scripts/setup-python-venvs.sh [--force]
# Ortam: PYTHON=python3.12 gibi özelleştirilebilir.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
FORCE=false
if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
fi

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Hata: '$PY' bulunamadı. PYTHON ortam değişkeni ile yolu verin." >&2
  exit 1
fi

install_requirements() {
  local dir="$1"
  local venv_pip="$dir/.venv/bin/pip"
  if [[ -f "$dir/requirements.txt" ]]; then
    "$venv_pip" install -r "$dir/requirements.txt"
  else
    echo "  (requirements.txt yok, atlanıyor)"
  fi
}

setup_project() {
  local name="$1"
  local dir="$ROOT/$name"
  if [[ ! -d "$dir" ]]; then
    echo "[$name] dizin yok, atlanıyor"
    return 0
  fi

  echo "=== $name ==="
  local venv_ok=false
  if [[ -x "$dir/.venv/bin/pip" ]] && "$dir/.venv/bin/pip" --version >/dev/null 2>&1; then
    venv_ok=true
  fi

  if [[ "$FORCE" == true ]] || [[ "$venv_ok" != true ]]; then
    if [[ -d "$dir/.venv" ]]; then
      if [[ "$FORCE" == true ]]; then
        echo "  --force: eski .venv siliniyor"
      else
        echo "  .venv eksik/bozuk; yeniden oluşturuluyor"
      fi
      rm -rf "$dir/.venv"
    fi
    echo "  venv oluşturuluyor: $PY -m venv .venv"
    (cd "$dir" && "$PY" -m venv .venv)
  else
    echo "  .venv sağlam; yalnızca pip install"
  fi

  local venv_pip="$dir/.venv/bin/pip"
  "$venv_pip" install -U pip setuptools wheel >/dev/null

  if [[ "$name" == "erdeniz_security" ]]; then
    install_requirements "$dir"
    echo "  pip install -e . (paket modu)"
    (cd "$dir" && "$dir/.venv/bin/pip" install -e .)
  else
    install_requirements "$dir"
  fi
  echo "  tamam: $dir/.venv"
}

for proj in garment_core mehlr_1.0 dressifye erdeniz_security; do
  setup_project "$proj"
done

echo ""
echo "Bitti. Örnek: source garment_core/.venv/bin/activate"
