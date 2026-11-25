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
- **Requisitos** (`docs/requisitos.md`): borrador completo. La entrevista con el docente **no se hizo**; el autor respondió él mismo las 20 preguntas y todo sigue siendo **supuesto** hasta que el docente lo confirme. Reglas de negocio RN-01..RN-14, RF-01..RF-18, RNF, historias HU.
- **Diseño** (`docs/diseno.md`) y prototipo aprobado (`docs/prototipos/prototipo-interfaz.html`): hechos.
- **Tecnología decidida:** Python + FastAPI, SQLite y frontend en HTML/CSS/JavaScript puro (sin Node.js). Un solo servidor sirve la API (`/api`), la documentación (`/docs`) y las páginas (`/`).
- **Backend** (`backend/`): implementado. 19 endpoints, reglas de negocio, seguridad (scrypt, JWT que vence a las 00:00 de Colombia, bloqueo por intentos) y validación de entradas. `backend/tests/` tiene la suite automatizada (`python -m pytest` desde `backend/`).
- **Frontend** (`frontend/`): implementado (catálogo, detalle e inscripción, login, panel, asistencia, consolidado) y verificado en el navegador contra el backend real.
- **Modelo de permisos:** el organizador gestiona solo sus eventos; la coordinación tiene sus mismos permisos sobre todos los eventos (incluida la creación) y además los consolidados; los participantes no inician sesión.
- **Pendiente:** documentar las 12 pruebas funcionales de la guía (Actividad 6) con evidencias en `evidencias/`; `docs/trazabilidad.md` (Actividad 7); completar el `README.md` como informe final; probar la instalación en el segundo equipo; y que el docente confirme `docs/requisitos.md`.
- **Ejecutar:** ver "Configuración del entorno" en `README.md`. Se necesita `.env` (copiar `.env.example`) con `SECRET_KEY` de 32 o más caracteres; `.env` nunca se sube a Git.

## Reglas de trabajo
- **Git:** una rama por tarea (`docs/...`, `feat/...`, `fix/...`), commits descriptivos, y pull request hacia `main` con propósito, cambios, pruebas efectuadas y requisitos asociados. Nada de commits genéricos ni una sola carga final. No fusionar un PR sin que el usuario lo pida.
- **Identidad de commits:** `Juan David Velasquez <juandavidvelasquezgomez@gmail.com>`. Verificar con `git config user.name` y `git config user.email` antes de commitear.
- **Repositorio público:** nunca subir contraseñas, tokens, claves ni `.env`. Usar solo datos ficticios.
- **Reproducibilidad:** todo debe poder instalarse desde cero en otro equipo siguiendo el `README.md` (dependencias declaradas, `.env.example`, scripts de base de datos y datos de prueba).
- **Idioma:** documentación y comunicación en español.
- Al cambiar de equipo: hacer `git pull` al empezar y `git push` al terminar.
