# Registro Civil � Santiago del Estero

Portal web y panel administrativo del Registro Civil de Santiago del Estero: informaci�n de tr�mites,
mapa de sedes, noticias, turnos online para tr�mites de DNI y la asistente virtual **RegIna**.

Proyecto desarrollado en la Pr�ctica Profesionalizante III de la Tecnicatura Superior en Desarrollo
de Software del Instituto Tecnol�gico de Santiago del Estero (ITSE), 2026.

## Funcionalidades

**Portal p�blico (sin registro)**
- Tr�mites por categor�a, con requisitos, pasos, costo y modalidad.
- Turnos online de DNI en 3 pasos, con disponibilidad real y confirmaci�n por correo.
- Sedes en mapa, "C�mo llegar" y "Sede m�s cercana".
- Noticias, buscador, preguntas frecuentes y asistente virtual RegIna.

**Panel administrativo (`/login/`)**
- Turnos: estados, carga manual por sede, reprogramaci�n y estad�sticas.
- Noticias, tr�mites y sedes con flujo de aprobaci�n; ubicaci�n de sedes marcada en un mapa.
- Usuarios con roles Operador y Super Admin; contrase�a propia obligatoria en el primer ingreso.

## Tecnolog�as

Python 3.13 � Django 6.0 � SQLite (o PostgreSQL) � Bootstrap 5 � Leaflet + OpenStreetMap �
Groq API � Whitenoise � django-axes � Docker + Gunicorn

## Instalaci�n local

```bash
git clone https://github.com/jatoledo-max/registro-civil-sde.git
cd registro-civil-sde
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Crear un archivo `.env` en la ra�z con al menos `DEBUG=True` para desarrollo.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `SECRET_KEY` | Clave de Django (obligatoria en producci�n) |
| `DEBUG` | `True` solo en desarrollo |
| `ALLOWED_HOSTS` | Dominios del sitio, separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Origen HTTPS del sitio |
| `GROQ_API_KEY` / `GROQ_MODEL` | Chatbot RegIna (modelo por defecto: `openai/gpt-oss-120b`) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Env�o de correos |
| `DATABASE_URL` | Opcional, para usar PostgreSQL |
| `URL_PREFIX` | Subdirectorio de publicaci�n (ej.: `/registro-civil`); vac�o en la ra�z |

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

Luego, **Reload** en la pesta�a Web.

## Despliegue con Docker

El proyecto incluye `Dockerfile` y `docker-compose.yml`. Puede publicarse en la ra�z de un dominio o en un
subdirectorio (por ejemplo `/registro-civil`) con la variable `URL_PREFIX`.

```bash
cp .env.docker.ejemplo .env.docker      # completar la configuraci�n
docker compose up -d --build
```

Gu�a completa para el servidor: [docs/despliegue-docker.md](docs/despliegue-docker.md).

## Documentaci�n

La documentaci�n completa (arquitectura, modelo de datos, reglas de negocio, pruebas, manuales de
usuario y protocolo de entrega) se entrega por separado junto con el sistema.

## Equipo

Yanucci, Agustina Micaela � Lobos, Noelia Soledad del Huerto � Toledo, Javier Hern�n �
Barros de Oliveira, F�bio � Castillo, Bianca Victoria
