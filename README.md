# Proyecto Final 04 - Organización de eventos y actividades académicas

Asignatura: Aplicaciones y Servicios Web - Tecnología en Desarrollo de Software

## 1. Información General
- Autor: Juan David Velasquez (trabajo individual)
- Repositorio: https://github.com/juandavidvelasquezgomez/trabajo-final-SAW

> README en construcción. Las secciones se completarán a medida que avance el proyecto (ver guía PF-04).

## Documentación
- [Requisitos](docs/requisitos.md)
- [Diseño](docs/diseno.md)
- [Prototipo de la interfaz](docs/prototipos/prototipo-interfaz.html) (abrir en el navegador)
- [Preparar un segundo equipo](docs/setup-portatil.md)
- [Trazabilidad](docs/trazabilidad.md) - pendiente
- [Evidencias](evidencias/)

## Estado
- Backend (API REST + base de datos SQLite): implementado y probado. Ver `backend/`.
- Frontend: pendiente (el prototipo visual ya está aprobado).

## Configuración del entorno (backend)
Requisitos: Python 3.12 o superior (probado con 3.14). Comandos en PowerShell, desde la raíz del repositorio:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item ..\.env.example ..\.env
```

Edita `.env` en la raíz y define `SECRET_KEY` (obligatoria, mínimo 32 caracteres). Para generar una:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

`SEED_PASSWORD` (opcional) es la contraseña de las cuentas de prueba; si la dejas vacía, el siguiente comando genera una y la muestra una sola vez. El archivo `.env` nunca se sube a Git.

Cargar datos de prueba ficticios y arrancar la API:

```powershell
.\.venv\Scripts\python.exe db\seed.py --reiniciar
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Documentación interactiva de la API: http://127.0.0.1:8000/docs
- Cuentas de prueba (todas con la contraseña de `SEED_PASSWORD`): `coordinacion@ejemplo.test`, `ana.torres@ejemplo.test` y `luis.mora@ejemplo.test`.

Ejecutar las pruebas automatizadas del backend:

```powershell
.\.venv\Scripts\python.exe -m pytest
```
