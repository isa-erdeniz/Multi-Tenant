@echo off
REM ErdenizTech — Windows Güvenlik Kurulumu
REM Python 3.11+ gerektirir

SET ROOT=%ERDENIZTECH_ROOT%
IF "%ROOT%"=="" SET ROOT=%USERPROFILE%\erdeniztech

SET SECURITY=%ROOT%\erdeniz_security

echo ==========================================
echo   ErdenizTech Security Setup — Windows
echo   Root: %ROOT%
echo ==========================================

pip install --only-binary cryptography --only-binary argon2-cffi -e "%SECURITY%" -q

SET PROJECTS=looopone_dashboard worktrackere garment_core mehlr_1.0

FOR %%P IN (%PROJECTS%) DO (
    IF EXIST "%ROOT%\%%P\manage.py" (
        echo.
        echo Kuruluyor %%P ...
        cd /d "%ROOT%\%%P"
        pip install -e "%SECURITY%" -q
        python manage.py generate_key --type fernet 2>nul
        python manage.py generate_key --type field 2>nul
        python manage.py generate_test_env --project %%P 2>nul
        python manage.py makemigrations erdeniz_security 2>nul
        python manage.py migrate 2>nul
        python manage.py security_check 2>nul
        echo Tamamlandı: %%P
    ) ELSE (
        echo Atlandı %%P: manage.py Bulunamadı
    )
)

echo.
echo ==========================================
echo   Add 'erdeniz_security' to INSTALLED_APPS
echo   Run get_django_security_settings()
echo ==========================================
pause
