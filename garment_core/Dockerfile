# Garment Core — Python 3.12-slim
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# erdeniz_security paketini container'a kopyala (pip install öncesi)
COPY erdeniz_security/ /app/erdeniz_security/

# ecosystem registry'yi container'a kopyala
COPY ecosystem/ /app/ecosystem/

# Python bağımlılıkları (layer cache için önce requirements)
COPY requirements.txt ./
COPY requirements ./requirements/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-deps /app/erdeniz_security/

ENV ERDENIZ_ECOSYSTEM_REGISTRY=/app/ecosystem/registry.json

# Node.js (Tailwind build için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

# Tailwind CSS — lock dosyasına sadık kurulum + doğrudan tailwind derlemesi
RUN npm ci --force
RUN npx tailwindcss -i ./static/css/src/input.css -o ./static/css/dist/output.css --minify

# Statik dosyalar — production ayarı imaj derlemesinde SECRET_KEY/CSRF ister; development yalnızca statik toplar
ENV DJANGO_SETTINGS_MODULE=config.settings.development
RUN python manage.py collectstatic --noinput
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Çalışma zamanı: migrate railway.toml preDeployCommand / Procfile release ile;
# burada yalnızca gunicorn (çoklu replikada migrate yarışı olmaz).
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2"]
