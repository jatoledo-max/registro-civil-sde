# Registro Civil – Santiago del Estero

Portal web y panel administrativo del Registro Civil de Santiago del Estero: información de trámites,
mapa de sedes, noticias, turnos online para trámites de DNI y la asistente virtual **RegIna**.

Proyecto desarrollado en la Práctica Profesionalizante III de la Tecnicatura Superior en Desarrollo
de Software del Instituto Tecnológico de Santiago del Estero (ITSE), 2026.

## Funcionalidades

**Portal público (sin registro)**
- Trámites por categoría, con requisitos, pasos, costo y modalidad.
- Turnos online de DNI en 3 pasos, con disponibilidad real y confirmación por correo.
- Sedes en mapa, "Cómo llegar" y "Sede más cercana".
- Noticias, buscador, preguntas frecuentes y asistente virtual RegIna.

**Panel administrativo (`/login/`)**
- Turnos: estados, carga manual por sede, reprogramación y estadísticas.
- Noticias, trámites y sedes con flujo de aprobación; ubicación de sedes marcada en un mapa.
- Usuarios con roles Operador y Super Admin; contraseña propia obligatoria en el primer ingreso.

## Tecnologías

Python 3.13 · Django 6.0 · SQLite (o PostgreSQL) · Bootstrap 5 · Leaflet + OpenStreetMap ·
Groq API · Whitenoise · django-axes · Docker + Gunicorn

## Instalación local

```bash
git clone https://github.com/jatoledo-max/proyecto-registro-civil.git
cd proyecto-registro-civil
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Crear un archivo `.env` en la raíz con al menos `DEBUG=True` para desarrollo.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `SECRET_KEY` | Clave de Django (obligatoria en producción) |
| `DEBUG` | `True` solo en desarrollo |
| `ALLOWED_HOSTS` | Dominios del sitio, separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Origen HTTPS del sitio |
| `GROQ_API_KEY` / `GROQ_MODEL` | Chatbot RegIna (modelo por defecto: `openai/gpt-oss-120b`) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Envío de correos |
| `DATABASE_URL` | Opcional, para usar PostgreSQL |
| `URL_PREFIX` | Subdirectorio de publicación (ej.: `/registro-civil`); vacío en la raíz |

## Pruebas

```bash
python manage.py test
```

## Actualizar el despliegue (PythonAnywhere)

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Luego, **Reload** en la pestaña Web.

## Despliegue con Docker

El proyecto incluye `Dockerfile` y `docker-compose.yml`. Puede publicarse en la raíz de un dominio o en un
subdirectorio (por ejemplo `/registro-civil`) con la variable `URL_PREFIX`.

```bash
cp .env.docker.ejemplo .env.docker      # completar la configuración
docker compose up -d --build
```

Guía completa para el servidor: [docs/despliegue-docker.md](docs/despliegue-docker.md).

## Documentación

La documentación completa (arquitectura, modelo de datos, reglas de negocio, pruebas, manuales de
usuario y protocolo de entrega) se entrega por separado junto con el sistema.

## Equipo

Yanucci, Agustina Micaela · Lobos, Noelia Soledad del Huerto · Toledo, Javier Hernán ·
Barros de Oliveira, Fábio · Castillo, Bianca Victoria
