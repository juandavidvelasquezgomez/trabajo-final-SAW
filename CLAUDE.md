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
- Actividad 2 (requisitos): **borrador completo**. La entrevista con el docente **no se hizo**; el autor respondió él mismo las 20 preguntas y todo sigue siendo **supuesto** hasta que el docente lo confirme. Ver `docs/requisitos.md`: entrevista (sección 3), reglas de negocio RN-01..RN-14 (sección 4), requisitos RF/RNF, historias de usuario y decisiones (sección 9). Si `docs/requisitos.md` no aparece en `main`, está en la rama `docs/requisitos` (pull request abierto).
- Modelo de permisos acordado: el organizador gestiona solo sus eventos; la coordinación tiene todos sus permisos sobre todos los eventos (incluida la creación) y además los consolidados; los participantes no inician sesión.
- Siguiente paso: Actividad 3, `docs/diseno.md` (arquitectura, tecnología, modelo de datos, especificación de la API). Antes de construir mucho, conviene que el docente confirme `docs/requisitos.md`.
- Tecnología (lenguaje, frameworks, base de datos): **aún sin decidir**. Se decide en `docs/diseno.md`. Preferir una base de datos que se levante igual en ambos equipos sin instalar un servidor.

## Reglas de trabajo
- **Git:** una rama por tarea (`docs/...`, `feat/...`, `fix/...`), commits descriptivos, y pull request hacia `main` con propósito, cambios, pruebas efectuadas y requisitos asociados. Nada de commits genéricos ni una sola carga final. No fusionar un PR sin que el usuario lo pida.
- **Identidad de commits:** `Juan David Velasquez <juandavidvelasquezgomez@gmail.com>`. Verificar con `git config user.name` y `git config user.email` antes de commitear.
- **Repositorio público:** nunca subir contraseñas, tokens, claves ni `.env`. Usar solo datos ficticios.
- **Reproducibilidad:** todo debe poder instalarse desde cero en otro equipo siguiendo el `README.md` (dependencias declaradas, `.env.example`, scripts de base de datos y datos de prueba).
- **Idioma:** documentación y comunicación en español.
- Al cambiar de equipo: hacer `git pull` al empezar y `git push` al terminar.
