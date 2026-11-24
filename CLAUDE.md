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
- Actividad 2 (requisitos) en curso: la entrevista con el docente **no se hizo**; el autor responde él mismo y todo sigue siendo **supuesto** hasta que el docente lo confirme. Ver `docs/requisitos.md` (secciones 3 y 9) para lo ya respondido y lo pendiente.
- Tecnología (lenguaje, frameworks, base de datos): **aún sin decidir**. Se decide en `docs/diseno.md`. Preferir una base de datos que se levante igual en ambos equipos sin instalar un servidor.

## Reglas de trabajo
- **Git:** una rama por tarea (`docs/...`, `feat/...`, `fix/...`), commits descriptivos, y pull request hacia `main` con propósito, cambios, pruebas efectuadas y requisitos asociados. Nada de commits genéricos ni una sola carga final. No fusionar un PR sin que el usuario lo pida.
- **Identidad de commits:** `Juan David Velasquez <juandavidvelasquezgomez@gmail.com>`. Verificar con `git config user.name` y `git config user.email` antes de commitear.
- **Repositorio público:** nunca subir contraseñas, tokens, claves ni `.env`. Usar solo datos ficticios.
- **Reproducibilidad:** todo debe poder instalarse desde cero en otro equipo siguiendo el `README.md` (dependencias declaradas, `.env.example`, scripts de base de datos y datos de prueba).
- **Idioma:** documentación y comunicación en español.
- Al cambiar de equipo: hacer `git pull` al empezar y `git push` al terminar.
