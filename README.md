# TurboTurn

TurboTurn es una plataforma web para gestionar citas entre clientes, talleres y mecanicos. Incluye registro de usuarios, aprobacion de talleres, agenda del taller, gestion de servicios, asignacion de mecanicos, historial de mantenimientos, mapa de talleres con Leaflet y autenticacion MFA con Google Authenticator.

## Estructura

```text
backend/    API en FastAPI, rutas, conexion a base de datos y utilidades de correo
frontend/   Paginas HTML, estilos, JavaScript e imagenes
database/   Esquema SQL y migraciones
```

## Ramas

```text
prueba       Rama de desarrollo y validacion
Produccion   Rama para publicar cambios estables
```

Flujo recomendado:

```bash
git checkout prueba
git pull origin prueba

# Despues de probar cambios
git add .
git commit -m "mensaje del cambio"
git push origin prueba

# Para subir a produccion
git checkout Produccion
git merge prueba
git push origin Produccion
```

## Requisitos

- Python 3.11 o superior
- PostgreSQL o base de datos RDS compatible
- Node.js para validar JavaScript con `node --check`
- Navegador web

## Configuracion

Crear un archivo `.env` en la raiz del proyecto:

```env
DB_HOST=host_de_base_de_datos
DB_NAME=postgres
DB_USER=usuario
DB_PASSWORD=contrasena
DB_PORT=5432
```

El archivo `.env` no debe subirse a GitHub porque contiene credenciales.

## Instalacion

Crear y activar entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r backend/requirements.txt
```

## Ejecutar el backend

Desde la carpeta `backend`:

```bash
cd backend
HOST=127.0.0.1 PORT=8001 ./run_server.sh
```

La API queda disponible en:

```text
http://127.0.0.1:8001
```

Documentacion Swagger:

```text
http://127.0.0.1:8001/docs
```

## Ejecutar el frontend

El frontend esta en:

```text
frontend/index.html
```

Si Apache esta configurado, sirve la carpeta `frontend/` como sitio estatico y redirige `/api/` al backend FastAPI.

## Migraciones

Las migraciones principales estan en `database/` y los scripts para aplicarlas estan en `backend/scripts/`.

Ejemplos:

```bash
python backend/scripts/apply_mecanicos_migration.py
python backend/scripts/apply_revision_mecanico_migration.py
python backend/scripts/apply_talleres_mapa_migration.py
python backend/scripts/apply_mecanicos_mfa_migration.py
```

## Funcionalidades principales

- Registro y verificacion por correo.
- Login unificado para usuarios, talleres, administradores y mecanicos.
- MFA con Google Authenticator para usuarios y mecanicos.
- Panel de cliente para vehiculos, citas, servicios e historial.
- Panel de taller para agenda, clientes, mecanicos y servicios.
- Panel de mecanico para revisar trabajos, registrar tiempo estimado y trabajo requerido.
- Panel de administrador para aprobar o rechazar talleres.
- Notificacion por correo cuando el taller cancela una cita.
- Mapa de talleres con Leaflet.

## Validaciones utiles

Validar Python:

```bash
python -m py_compile backend/main.py backend/routes/*.py
```

Validar JavaScript:

```bash
node --check frontend/js/app.js
node --check frontend/js/taller.js
node --check frontend/js/mecanico.js
node --check frontend/js/admin.js
```

## Produccion

La configuracion de Apache esta en:

```text
backend/apache_turboturn.conf
```

Esa configuracion sirve el frontend y envia las peticiones `/api/` al backend FastAPI. Antes de publicar, confirmar que las rutas del `DocumentRoot` y el puerto del backend coincidan con el servidor real.
