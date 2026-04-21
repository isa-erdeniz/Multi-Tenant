FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --no-input && python manage.py seed_projects && python create_superuser.py && gunicorn config.wsgi:application --workers 2 --threads 4 --bind 0.0.0.0:$PORT --log-level info"]
