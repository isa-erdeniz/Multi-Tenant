FROM python:3.11-slim

LABEL maintainer="ErdenizTech <contact@erdeniztech.com>"
LABEL version="1.0.0"
LABEL description="ErdenizTech Security Package"

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Paket
COPY . .
RUN pip install --no-cache-dir -e .

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import erdeniz_security; print('OK')" || exit 1

CMD ["python", "-c", "import erdeniz_security; print(f'ErdenizSecurity {erdeniz_security.__version__} hazır')"]
