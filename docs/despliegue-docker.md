# Despliegue con Docker – Registro Civil de Santiago del Estero

Guía para publicar el sistema en un servidor con Docker, por ejemplo en el dominio de prueba del ITSE bajo
`https://<dominio>/registro-civil/`.

## Resumen técnico

| Componente | Detalle |
| --- | --- |
| Lenguaje | Python 3.13 |
| Framework | Django 6.0 |
| Servidor de aplicación | Gunicorn (puerto 8000 dentro del contenedor) |
| Archivos estáticos | WhiteNoise (incluidos en la imagen; no requieren servidor aparte) |
| Imágenes subidas | Carpeta `/app/data/media` (volumen) |
| Base de datos | SQLite en `/app/data/db.sqlite3` (volumen); PostgreSQL opcional con `DATABASE_URL` |
| Servicios externos | Groq (chatbot, opcional), servidor SMTP (correos, opcional), OpenStreetMap (mapas, desde el navegador) |

Todo lo que cambia con el uso (base de datos e imágenes) vive en el volumen montado en `/app/data`. La imagen
se puede reconstruir y reemplazar sin perder datos.

## 1. Configurar

```bash
cp .env.docker.ejemplo .env.docker
```

Completar `.env.docker`. Las variables importantes:

| Variable | Ejemplo | Uso |
| --- | --- | --- |
| `SECRET_KEY` | (generar una nueva) | Clave de Django. Generarla con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `URL_PREFIX` | `/registro-civil` | Subdirectorio de publicación. Vacío si va en la raíz del dominio |
| `ALLOWED_HOSTS` | `dominio.itse.edu.ar` | Dominio por el que se accede |
| `CSRF_TRUSTED_ORIGINS` | `https://dominio.itse.edu.ar` | Origen HTTPS del sitio (necesario para los formularios del panel) |
| `CONFIAR_PROXY_HTTPS` | `True` | Si hay un proxy con HTTPS delante que envía `X-Forwarded-Proto` |
| `GROQ_API_KEY` | | Chatbot RegIna. Sin ella el chatbot responde que no está disponible |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | | Correos de confirmación de turnos. Sin ellos solo se registran en el log |
| `DATABASE_URL` | `postgres://usuario:clave@servidor:5432/registro_civil` | Solo si se usa PostgreSQL en lugar de SQLite |
| `GUNICORN_WORKERS` | `3` | Procesos de Gunicorn |

## 2. Construir y arrancar

```bash
docker compose up -d --build
```

Al arrancar, el contenedor aplica las migraciones de la base de datos y levanta Gunicorn en el puerto 8000.

Crear el primer usuario administrador (después el resto se crea desde el panel):

```bash
docker compose exec registro-civil python manage.py createsuperuser
```

## 3. Publicar en el subdirectorio

El servidor web del Data Center debe redirigir `/registro-civil/` al puerto 8000 del contenedor. Ejemplo para
nginx en [`docker/nginx-ejemplo.conf`](../docker/nginx-ejemplo.conf):

```nginx
absolute_redirect off;

location = /registro-civil {
    return 301 /registro-civil/;
}

location /registro-civil/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 6M;
}
```

El sistema funciona tanto si el proxy le pasa la ruta completa (`/registro-civil/sedes/`) como si le quita el
prefijo (`/sedes/`). Todos los enlaces, archivos estáticos, llamadas internas y cookies usan el valor de
`URL_PREFIX`. Las cookies del sistema (`rc_sessionid`, `rc_csrftoken`) se limitan a esa ruta, para no
mezclarse con otras aplicaciones del mismo dominio.

## 4. Migrar los datos existentes (opcional)

Para llevar los datos actuales (por ejemplo, desde PythonAnywhere), copiar la base y las imágenes al volumen:

```bash
docker compose cp db.sqlite3 registro-civil:/app/data/db.sqlite3
docker compose cp media/. registro-civil:/app/data/media/
docker compose exec -u root registro-civil chown -R app:app /app/data
docker compose restart registro-civil
```

## 5. Operación

| Tarea | Comando |
| --- | --- |
| Ver el registro del servidor | `docker compose logs -f registro-civil` |
| Actualizar a una versión nueva | `git pull` y luego `docker compose up -d --build` |
| Respaldar la base y las imágenes | `docker compose cp registro-civil:/app/data ./respaldo-AAAA-MM-DD` |
| Detener | `docker compose down` (los datos quedan en el volumen) |
| Correr las pruebas | `docker compose exec registro-civil python manage.py test` |

## Prueba local que simula el Data Center

`docker/docker-compose.prueba.yml` levanta el sistema detrás de un nginx en
`http://localhost:8080/registro-civil/`, con configuración de prueba (no usar en producción):

```bash
docker compose -f docker/docker-compose.prueba.yml up -d --build
docker compose -f docker/docker-compose.prueba.yml down
```

Con esta prueba se verificó el funcionamiento completo bajo `/registro-civil/`: páginas públicas, archivos
estáticos, buscador, noticias, turnero, chatbot, inicio de sesión, operaciones del panel y registro de actividad.
