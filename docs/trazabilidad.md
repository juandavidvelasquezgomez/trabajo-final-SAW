# Matriz de trazabilidad (Actividad 7)

Correspondencia entre condiciones obligatorias, requisitos, implementación, pull requests y pruebas.
Requisitos en [requisitos.md](requisitos.md); pruebas y evidencias en [pruebas-funcionales.md](pruebas-funcionales.md).

Repositorio: https://github.com/juandavidvelasquezgomez/trabajo-final-SAW

## Condiciones de aceptación

| Condición | Requisito aprobado | Implementación (ruta / componente) | Pull request | Prueba |
|---|---|---|---|---|
| **CA-01** Crear y publicar actividades | RF-01, RF-02, RF-03, RF-13, RF-16 | `backend/app/reglas.py` (`crear_evento`, `editar_evento`, `cambiar_estado_evento`), `routers/eventos.py`, `auth.py`; `frontend/panel.html`, `js/panel.js`, `login.html` | #5, #6 | P01, P02, P09 |
| **CA-02** Consultar eventos y disponibilidad | RF-04, RF-05, RF-18 | `reglas.py` (`catalogo`, `detalle_evento`, `finalizar_vencidos`); `index.html`, `js/catalogo.js`, `evento.html` | #5, #6 | P03, P04 |
| **CA-03** Inscribirse | RF-06, RF-07, RF-15 | `reglas.py` (`inscribir`, `_asegurar_participante`, `inscribir_en_el_momento`), `routers/inscripciones.py`; `js/evento.js`, `js/asistencia.js` | #5, #6 | P05, P06 |
| **CA-04** Cupos y reglas de inscripción | RF-08, RF-09 | `reglas.py` (`_crear_inscripcion`, `cancelar_inscripcion`), `db.py` (transacción), `db/schema.sql` (índice único y triggers) | #5, #6 | P07, P08 |
| **CA-05** Asistencia y lista de participantes | RF-07, RF-10, RF-11, RF-13, RF-15, RF-17 | `reglas.py` (`listar_inscritos`, `_aplicar_asistencia`, `registrar_asistencia_lote`), `routers/asistencia.py`; `asistencia.html`, `js/asistencia.js` | #5, #6 | P09, P10 |
| **CA-06** Consolidado para la coordinación | RF-12, RF-14, RF-16, RF-18 | `reglas.py` (`consolidado`), `routers/consolidado.py`; `consolidado.html`, `js/consolidado.js` | #5, #6 | P11, P12 |

## Extensiones

| Extensión | Requisito | Implementación | Pull request | Prueba |
|---|---|---|---|---|
| Constancia de asistencia (sin firma digital) | RF-19 | `backend/app/constancias.py`, `routers/extensiones.py`; `constancia.html`, `js/constancia.js` | #7 | EXT-02 a EXT-05 |
| Código QR | RF-20 | `backend/app/qr.py`, `routers/extensiones.py`; `js/evento.js` | #7 | EXT-01 |

## Reglas de negocio

| Regla | Resumen | Dónde se aplica | Prueba automatizada (`backend/tests/`) |
|---|---|---|---|
| RN-01 | No superar el cupo | `reglas._crear_inscripcion` + triggers `trg_cupo_*` | `test_inscripciones.py`, `test_bd.py` |
| RN-02 | Sin inscripción duplicada | `reglas._crear_inscripcion` + índice `ux_inscripcion_activa` | `test_inscripciones.py` |
| RN-03, RN-04 | Solo publicados y antes de iniciar | `reglas.inscribir` | `test_inscripciones.py` |
| RN-05 | Cancelar libera el cupo | `reglas.cancelar_inscripcion` | `test_inscripciones.py` |
| RN-06 | Asistencia solo de inscritos | `reglas._aplicar_asistencia` + trigger | `test_asistencia.py`, `test_bd.py` |
| RN-07 | Permisos por propiedad y rol | `reglas._exigir_gestion`, `auth.exigir_coordinacion` | `test_eventos.py`, `test_asistencia.py` |
| RN-08 | Cupo no menor que inscritos | `reglas.editar_evento` | `test_eventos.py` |
| RN-09 | Fechas y duración máxima 8 h | `reglas.validar_fechas` + `CHECK` | `test_eventos.py`, `test_bd.py` |
| RN-10 | Sin cruces de horario | `reglas._crear_inscripcion` | `test_inscripciones.py` |
| RN-11 | Ventanas de asistencia y cierre del historial | `reglas._aplicar_asistencia`, `cancelar_inscripcion_personal` | `test_asistencia.py`, `test_inscripciones.py` |
| RN-12, RN-13 | Estados y cancelación de evento | `reglas.cambiar_estado_evento`, `finalizar_vencidos` | `test_eventos.py` |
| RN-14 | Token vence a medianoche | `auth.crear_token` | `test_seguridad.py` |
| RN-15 | El público ve solo cifras | `reglas.a_evento`, `listar_inscritos` | `test_eventos.py` |
| RN-16 | Cambio de fechas | `reglas.editar_evento` | `test_eventos.py` |

## Pull requests

| PR | Rama | Contenido |
|---|---|---|
| #1 | `docs/requisitos` | Requisitos, entrevista y reglas de negocio |
| #2 | `chore/setup-multi-equipo` | Contexto del proyecto y guía para un segundo equipo |
| #3 | `docs/diseno` | Arquitectura, modelo de datos y API |
| #4 | `docs/prototipo-interfaz` | Prototipo navegable de la interfaz |
| #5 | `feat/backend` | API REST, base de datos, reglas, seguridad y pruebas |
| #6 | `feat/frontend` | Interfaz web conectada a la API |
| #7 | `feat/extensiones-y-entrega` | Extensiones, evidencias y documentación final |
