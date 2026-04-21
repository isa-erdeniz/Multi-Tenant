# Garment Core

AI destekli kişisel stil danışmanlığı ve sanal giysi deneme platformu.

## Kurulum

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/development.txt
cp .env.example .env
# .env dosyasını düzenleyin
python manage.py migrate
python manage.py create_default_plans
python manage.py createsuperuser
python manage.py runserver
```

## Railway Deployment

- PostgreSQL ve Redis Railway'den eklenir
- `DATABASE_URL` ve `REDIS_URL` otomatik ayarlanır
- Procfile ile web, worker ve beat process'leri çalışır

## Teknoloji

- Django 5.2, DRF
- PostgreSQL, Redis, Celery
- Tailwind CSS, Alpine.js, HTMX
- iyzico, AWS S3, Sentry
