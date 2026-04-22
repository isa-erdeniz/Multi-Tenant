#!/bin/bash
# ErdenizTech — Tüm Projelere Güvenlik Kurulumu (tek katman: erdeniz_security)
set -e
ROOT="${ERDENIZTECH_ROOT:-/home/isa/erdeniztech}"
SECURITY="${ROOT}/erdeniz_security"

# Platform tespiti
detect_platform() {
    case "$(uname -s 2>/dev/null)" in
        Linux*)
            if grep -qi "android" /proc/version 2>/dev/null || [ -d "/data/data/com.termux" ] 2>/dev/null; then
                echo "android"
            else
                echo "linux"
            fi
            ;;
        Darwin*) echo "mac" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

PLATFORM=$(detect_platform)
echo "Platform: $PLATFORM"

# Android/Termux için minimal kurulum
if [ "$PLATFORM" = "android" ]; then
    echo "Android/Termux modu — minimal bağımlılıklar"
    pip install cryptography argon2-cffi django python-decouple -q 2>/dev/null || true
    pip install -e "$SECURITY" -q --no-deps 2>/dev/null || true
    echo "Android kurulumu tamamlandı."
    exit 0
fi

# Windows Git Bash
if [ "$PLATFORM" = "windows" ]; then
    pip install --only-binary cryptography --only-binary argon2-cffi -e "$SECURITY" -q 2>/dev/null || true
else
    pip install -e "$SECURITY" -q 2>/dev/null || true
fi

PROJECTS=(
    "looopone_dashboard"
    "worktrackere"
    "garment_core"
    "gyminfinitye_saas"
    "mehlr_1.0"
)

echo "═══════════════════════════════════════════"
echo "  ErdenizTech Security Setup — Tek Katman"
echo "  Root: $ROOT"
echo "  Not: GitHub yüklemek için Gitingiroe gerekir."
echo "═══════════════════════════════════════════"

pip install -e "$SECURITY" -q 2>/dev/null || true

for project in "${PROJECTS[@]}"; do
    dir="${ROOT}/${project}"
    if [ ! -f "$dir/manage.py" ]; then
        echo "▶ [$project] manage.py yok — atlanıyor"
        continue
    fi
    echo ""
    echo "▶ [$project] Kuruluyor..."
    (cd "$dir" && pip install -e "$SECURITY" -q 2>/dev/null || true)
    (cd "$dir" && pip install cryptography argon2-cffi django-encrypted-model-fields python-decouple -q 2>/dev/null || true)
    (cd "$dir" && python manage.py generate_key --type fernet 2>/dev/null | head -1) || true
    (cd "$dir" && python manage.py generate_key --type field 2>/dev/null | head -1) || true
    (cd "$dir" && python manage.py generate_test_env --project "$project" 2>/dev/null || true)
    (cd "$dir" && python manage.py makemigrations erdeniz_security 2>/dev/null || true)
    (cd "$dir" && python manage.py migrate 2>/dev/null || true)
    (cd "$dir" && python manage.py security_check 2>/dev/null || true)
    echo "✓ [$project] Tamamlandı"
done

echo ""
echo "═══════════════════════════════════════════"
echo "  INSTALLED_APPS'a 'erdeniz_security' ve 'axes' ekleyin."
echo "  get_django_security_settings() ile ayarları yükleyin."
echo "═══════════════════════════════════════════"
