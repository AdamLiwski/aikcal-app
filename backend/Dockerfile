# Używamy lekkiego obrazu Python 3.11
FROM python:3.11-slim

# Ustawienia środowiskowe (nie twórz plików .pyc, logi od razu na wyjście)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Ustawiamy katalog roboczy
WORKDIR /app

# Instalujemy zależności systemowe (potrzebne czasem dla bibliotek C++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopiujemy requirements i instalujemy biblioteki (korzystamy z cache Dockera)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy resztę kodu aplikacji
COPY . .

# Tworzymy użytkownika non-root dla bezpieczeństwa
RUN useradd -m appuser
USER appuser

# Domyślny port
EXPOSE 8000

# Komenda startowa (na produkcji użyjemy Gunicorna, lokalnie nadpiszemy to w docker-compose)
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]