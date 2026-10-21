# Imagen del sistema web del Registro Civil (Django 6 + Gunicorn)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Datos persistentes: base SQLite e imágenes subidas (montar un volumen en /app/data)
    DATABASE_URL=sqlite:////app/data/db.sqlite3 \
    MEDIA_ROOT=/app/data/media

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Archivos estáticos (CSS, JS, imágenes del sitio) dentro de la imagen
RUN SECRET_KEY=solo-para-construir-la-imagen python manage.py collectstatic --noinput

# Usuario sin privilegios
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data/media \
    && chown -R app:app /app/data
USER app

EXPOSE 8000
ENTRYPOINT ["sh", "docker/entrypoint.sh"]
