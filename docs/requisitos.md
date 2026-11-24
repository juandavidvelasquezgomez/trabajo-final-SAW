# Requisitos - Organización de eventos y actividades académicas

**Proyecto:** PF-04 - Aplicaciones y Servicios Web
**Autor:** Juan David Velasquez (trabajo individual)
**Estado del documento:** BORRADOR - pendiente de entrevista y aprobación del docente

> Convención: todo lo marcado como **[SUPUESTO]** no ha sido confirmado por el docente y debe validarse en la entrevista (sección 3). Cuando se confirme, se cambia a **[CONFIRMADO]** y se registra la fecha.

---

## 1. Alcance

La aplicación permite a una institución educativa **crear y publicar actividades académicas, consultarlas, inscribir participantes, controlar cupos y registrar asistencia**, con información consolidada para la coordinación.

**Fuera de alcance** (según la guía): pasarelas de pago, videoconferencias, SMS/WhatsApp, certificados firmados, integración con sistemas institucionales y lectura de QR.

## 2. Actores y permisos

| Actor | Responsabilidad | Permisos propuestos [SUPUESTO] |
|---|---|---|
| Participante | Consulta eventos y se inscribe | Ver catálogo publicado, inscribirse, ver y cancelar sus inscripciones |
| Organizador | Programa y administra actividades | Crear/editar/publicar/cancelar sus eventos, ver inscritos, registrar asistencia |
| Coordinación | Supervisa y consulta consolidados | Ver todos los eventos y reportes; sin edición de eventos ajenos |

## 3. Entrevista con el docente (representante de la organización)

Registrar respuestas, acuerdos y pendientes. Estado: `Pendiente` / `Respondida` / `Confirmada`.

### 3.1 Eventos y publicación
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| E1 | ¿Qué datos debe tener un evento (título, descripción, tipo, fecha/hora, lugar o enlace, cupo, organizador)? ¿Cuáles son obligatorios? | | Pendiente |
| E2 | ¿Qué tipos de actividad existen (conferencia, taller, seminario, capacitación)? ¿Es una lista fija? | | Pendiente |
| E3 | ¿Qué estados tiene un evento (borrador, publicado, cancelado, finalizado)? ¿Quién cambia cada estado? | | Pendiente |
| E4 | ¿Un evento publicado se puede editar o cancelar? ¿Qué pasa con las inscripciones si se cancela? | | Pendiente |
| E5 | ¿Se permite crear eventos con fecha en el pasado? ¿Debe haber una duración máxima o validación de fechas? | | Pendiente |

### 3.2 Inscripción y cupos
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| I1 | ¿Quién puede inscribirse (solo estudiantes, docentes, externos)? ¿Se requiere registro/cuenta o basta con datos básicos? | | Pendiente |
| I2 | ¿Qué datos del participante se piden (nombre, documento, correo, programa, rol)? | | Pendiente |
| I3 | ¿Una persona puede inscribirse dos veces al mismo evento? ¿Cómo se identifica a la misma persona (correo, documento)? | | Pendiente |
| I4 | ¿Se permite cancelar una inscripción? ¿Hasta cuándo? ¿Libera el cupo? | | Pendiente |
| I5 | Con cupo agotado, ¿se rechaza sin más o hay lista de espera? | | Pendiente |
| I6 | ¿Hay fecha límite de inscripción? ¿Se puede inscribir a un evento ya iniciado o finalizado? | | Pendiente |
| I7 | ¿Se impide inscribirse a dos eventos que se crucen en horario? | | Pendiente |

### 3.3 Asistencia
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| A1 | ¿Quién registra la asistencia y cuándo (durante o después del evento)? | | Pendiente |
| A2 | ¿La asistencia es solo presente/ausente o hay otros estados (tardanza, excusa)? | | Pendiente |
| A3 | ¿Se puede registrar asistencia de alguien no inscrito? | | Pendiente |
| A4 | ¿Se puede corregir una asistencia ya registrada? | | Pendiente |

### 3.4 Usuarios, permisos y reportes
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| U1 | ¿Se requiere inicio de sesión? ¿Basta con roles simples o se necesita autenticación completa? | | Pendiente |
| U2 | ¿Un organizador solo gestiona sus propios eventos o todos? | | Pendiente |
| U3 | ¿Qué debe ver la coordinación (por evento: cupo, inscritos, asistentes, % de asistencia, estado)? ¿Con filtros por fecha, tipo o estado? | | Pendiente |
| U4 | ¿Hay requisitos de rendimiento, idioma o dispositivos (móvil)? | | Pendiente |

## 4. Reglas de negocio

| ID | Regla | Estado |
|---|---|---|
| RN-01 | El número de inscripciones activas de un evento nunca puede superar su cupo. | [SUPUESTO] |
| RN-02 | Un participante no puede tener dos inscripciones activas en el mismo evento (identificado por correo). | [SUPUESTO] |
| RN-03 | Solo se puede inscribir en eventos con estado `publicado`. | [SUPUESTO] |
| RN-04 | No se permite inscripción después de la fecha de inicio del evento. | [SUPUESTO] |
| RN-05 | Cancelar una inscripción libera el cupo. | [SUPUESTO] |
| RN-06 | Solo participantes con inscripción activa pueden tener asistencia registrada. | [SUPUESTO] |
| RN-07 | Solo el organizador del evento (o rol autorizado) puede editar, publicar, cancelar o registrar asistencia. | [SUPUESTO] |
| RN-08 | El cupo de un evento con inscripciones no puede reducirse por debajo del número de inscritos activos. | [SUPUESTO] |

## 5. Requisitos funcionales

Prioridad MoSCoW: **M** debe, **S** debería, **C** podría.

| ID | Requisito | Prioridad | Condición |
|---|---|---|---|
| RF-01 | Crear una actividad con título, descripción, tipo, fecha/hora, lugar, cupo y organizador. | M | CA-01 |
| RF-02 | Publicar una actividad para que aparezca en el catálogo. | M | CA-01 |
| RF-03 | Editar y cancelar una actividad según su estado y las reglas aprobadas. | S | CA-01 |
| RF-04 | Consultar el catálogo de eventos publicados con su disponibilidad de cupos. | M | CA-02 |
| RF-05 | Consultar el detalle de un evento. | M | CA-02 |
| RF-06 | Inscribir a un participante en un evento publicado. | M | CA-03 |
| RF-07 | Consultar las inscripciones de un participante y la lista de inscritos de un evento. | M | CA-03, CA-05 |
| RF-08 | Rechazar inscripciones que excedan el cupo, sean duplicadas o incumplan reglas, sin alterar los datos. | M | CA-04 |
| RF-09 | Cancelar una inscripción y liberar el cupo. | S | CA-04 |
| RF-10 | Registrar la asistencia de un inscrito a un evento. | M | CA-05 |
| RF-11 | Consultar la lista de participantes con su asistencia. | M | CA-05 |
| RF-12 | Consultar información consolidada por evento: cupo, inscritos, asistentes y estado. | M | CA-06 |
| RF-13 | Restringir la gestión de eventos y asistencia a roles autorizados. | M | CA-01, CA-05 |
| RF-14 | Filtrar el catálogo y los consolidados por fecha, tipo o estado. | C | CA-02, CA-06 |

## 6. Requisitos no funcionales

| ID | Requisito | Prioridad |
|---|---|---|
| RNF-01 | Persistencia en base de datos relacional; los datos sobreviven a reinicios. | M |
| RNF-02 | Validación de datos en el servidor, aunque la solicitud no venga de la interfaz. | M |
| RNF-03 | Respuestas HTTP con códigos adecuados y mensajes de error que no revelen información sensible. | M |
| RNF-04 | Sin credenciales reales en el repositorio; configuración mediante `.env` y `.env.example`. | M |
| RNF-05 | Uso exclusivo de datos ficticios. | M |
| RNF-06 | Control de concurrencia: dos inscripciones simultáneas no deben superar el cupo. | S |
| RNF-07 | Interfaz usable en escritorio y móvil (responsive). | C |
| RNF-08 | Instrucciones reproducibles de instalación y ejecución. | M |

## 7. Historias de usuario y criterios de aceptación

**HU-01 - Publicar una actividad** (RF-01, RF-02, RF-13 / CA-01)
Como organizador, quiero crear y publicar una actividad para que los participantes la vean.
- Dado un organizador autorizado y datos válidos, cuando crea y publica el evento, entonces queda guardado y aparece en el catálogo.
- Dados datos inválidos (título vacío, cupo ≤ 0, fecha inválida), cuando intenta crearlo, entonces se rechaza y no se guarda nada.

**HU-02 - Consultar eventos** (RF-04, RF-05 / CA-02)
Como participante, quiero ver los eventos y sus cupos disponibles para decidir a cuál inscribirme.
- Dado un catálogo con eventos, cuando lo consulto, entonces veo solo los publicados con cupos disponibles coherentes con las inscripciones.
- Dado un identificador inexistente, cuando consulto el detalle, entonces recibo un error controlado.

**HU-03 - Inscribirse** (RF-06, RF-07 / CA-03)
Como participante, quiero inscribirme en una actividad para reservar mi cupo.
- Dados datos válidos y cupo disponible, cuando me inscribo, entonces la inscripción queda guardada y puedo consultarla.
- Dados datos inválidos, cuando me inscribo, entonces se rechaza con un mensaje claro.

**HU-04 - Control de cupos y duplicados** (RF-08, RF-09 / CA-04)
Como organizador, quiero que el sistema impida sobrecupos y duplicados para mantener la información consistente.
- Dado un evento con cupo agotado, cuando alguien intenta inscribirse, entonces se rechaza y el cupo no cambia.
- Dado un participante ya inscrito, cuando intenta inscribirse de nuevo, entonces se rechaza según RN-02.

**HU-05 - Registrar asistencia** (RF-10, RF-11, RF-13 / CA-05)
Como organizador, quiero registrar y consultar la asistencia de los inscritos para tener el control real del evento.
- Dado un inscrito, cuando registro su asistencia, entonces se guarda asociada al evento y al participante.
- Dado un usuario sin autorización, cuando intenta registrar asistencia, entonces la operación es impedida.

**HU-06 - Consolidado** (RF-12, RF-14 / CA-06)
Como coordinador, quiero ver un resumen de eventos, inscripciones y asistencia para supervisar la programación.
- Dados varios eventos, cuando consulto el consolidado, entonces veo cupo, inscritos, asistentes y estado de cada uno con totales coherentes.

## 8. Trazabilidad preliminar con las condiciones de aceptación

| Condición | Requisitos | Historias |
|---|---|---|
| CA-01 | RF-01, RF-02, RF-03, RF-13 | HU-01 |
| CA-02 | RF-04, RF-05, RF-14 | HU-02 |
| CA-03 | RF-06, RF-07 | HU-03 |
| CA-04 | RF-08, RF-09 | HU-04 |
| CA-05 | RF-07, RF-10, RF-11, RF-13 | HU-05 |
| CA-06 | RF-12, RF-14 | HU-06 |

## 9. Registro de decisiones y pendientes

| Fecha | Decisión / acuerdo | Fuente |
|---|---|---|
| | *(se completa tras la entrevista)* | |

**Pendiente de aprobación del docente:** alcance, reglas de negocio (sección 4) y prioridades (sección 5).
