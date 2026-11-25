# Contexto del proyecto (para sesiones de Claude)

Proyecto final PF-04 de *Aplicaciones y Servicios Web* (Tecnología en Desarrollo de Software): **aplicación web para organizar eventos y actividades académicas**. Autor único: Juan David Velasquez. El usuario trabaja en dos equipos (escritorio y portátil) y sincroniza solo mediante este repositorio de GitHub.

## Qué debe cumplir (guía PF-04)
Interfaz web + API REST + base de datos relacional, conectadas de verdad (sin datos simulados). Seis condiciones obligatorias:
- CA-01 Crear y publicar actividades (personal autorizado).
- CA-02 Consultar eventos y disponibilidad de cupos.
- CA-03 Inscribir participantes.
- CA-04 Controlar cupos y rechazar sobrecupo/duplicados sin alterar datos.
- CA-05 Registrar asistencia y ver lista de participantes (personal autorizado).
- CA-06 Consolidado para la coordinación.

Entregables en el repo: `README.md` (es el informe), `docs/requisitos.md`, `docs/diseno.md`, `docs/trazabilidad.md`, `evidencias/`, código, `.env.example`, scripts de base de datos. Hay 12 pruebas funcionales documentadas (no se exige automatizarlas). Evaluación: implementación e integración 45 %, pruebas y documentación 20 %, Git/GitHub 15 %, requisitos 10 %, diseño 10 %.

## Estado actual
- **Implementado y probado:** backend (`backend/`), frontend (`frontend/`), extensiones (constancia de asistencia sin firma digital y códigos QR) y suite automatizada (`python -m pytest` desde `backend/`).
- **Documentación:** `README.md` (informe final), `docs/requisitos.md`, `docs/diseno.md`, `docs/pruebas-funcionales.md`, `docs/trazabilidad.md`, `evidencias/`.
- **Tecnología:** Python + FastAPI, SQLite, HTML/CSS/JavaScript puro. Un servidor sirve la API (`/api`), `/docs` y las páginas (`/`).
- **Permisos:** el organizador gestiona solo sus eventos; la coordinación todos, más el consolidado; los participantes no inician sesión.
- **Pendiente:** confirmación del docente sobre los requisitos (son supuestos del autor; la entrevista no se hizo); probar en el segundo equipo y en un celular físico.
- **Preparar una demostración:** `db/seed.py --reiniciar` (con el servidor apagado), `db/preparar_demo.py` (evento en curso) y `uvicorn app.main:app`.
- **Ejecutar:** ver "Configuración del entorno" en `README.md`. Se necesita `.env` (copiar `.env.example`) con `SECRET_KEY` de 32 o más caracteres; `.env` nunca se sube a Git.

## Reglas de trabajo
- **Git:** una rama por tarea (`docs/...`, `feat/...`, `fix/...`), commits descriptivos, y pull request hacia `main` con propósito, cambios, pruebas efectuadas y requisitos asociados. Nada de commits genéricos ni una sola carga final. No fusionar un PR sin que el usuario lo pida.
- **Identidad de commits:** `Juan David Velasquez <juandavidvelasquezgomez@gmail.com>`. Verificar con `git config user.name` y `git config user.email` antes de commitear.
- **Repositorio público:** nunca subir contraseñas, tokens, claves ni `.env`. Usar solo datos ficticios.
- **Reproducibilidad:** todo debe poder instalarse desde cero en otro equipo siguiendo el `README.md` (dependencias declaradas, `.env.example`, scripts de base de datos y datos de prueba).
- **Idioma:** documentación y comunicación en español.
- Al cambiar de equipo: hacer `git pull` al empezar y `git push` al terminar.
