# Requisitos - Organización de eventos y actividades académicas

**Proyecto:** PF-04 - Aplicaciones y Servicios Web
**Autor:** Juan David Velasquez (trabajo individual)
**Estado del documento:** BORRADOR - entrevista respondida por el autor; pendiente de confirmación y aprobación del docente

> Convención: la entrevista con el docente no se realizó. Las respuestas de la sección 3 las dio el autor y son **[SUPUESTO]** hasta que el docente las confirme; entonces pasan a **[CONFIRMADO]** con fecha en la sección 9.

---

## 1. Alcance

La aplicación permite a una institución educativa **crear y publicar actividades académicas, consultarlas, inscribir participantes, controlar cupos y registrar asistencia**, con información consolidada para la coordinación.

**Fuera de alcance** (según la guía): pasarelas de pago, videoconferencias, SMS/WhatsApp, certificados firmados, integración con sistemas institucionales y lectura de QR.

**Mejoras futuras** (fuera del alcance actual): lista de espera cuando el cupo se agota, estados de asistencia adicionales (tardanza, excusa) e interfaz en inglés.

## 2. Actores y permisos

| Actor | Responsabilidad | ¿Inicia sesión? |
|---|---|---|
| Participante | Consulta eventos, se inscribe y cancela su inscripción | No (se identifica con correo y documento) |
| Organizador | Programa y administra **sus** actividades | Sí |
| Coordinación | Supervisa todas las actividades; mismos permisos del organizador sobre **todos** los eventos, más consolidados | Sí |

Jerarquía: la coordinación tiene el rango más alto y puede hacer todo lo que hace el organizador, pero sobre cualquier evento. No existe un rol administrador.

| Acción | Participante | Organizador | Coordinación |
|---|---|---|---|
| Consultar catálogo y detalle de eventos publicados | Sí | Sí | Sí |
| Inscribirse / cancelar su inscripción | Sí | - | - |
| Crear eventos | No | Sí | Sí (elige el organizador responsable; por defecto ella misma) |
| Editar, publicar y cancelar eventos | No | Solo los suyos | Todos |
| Ver inscritos de un evento | No | Solo los suyos | Todos |
| Registrar y corregir asistencia, inscribir en el momento | No | Solo los suyos | Todos |
| Consolidados | No | No | Sí |

## 3. Entrevista (respondida por el autor)

Estado: `Respondida` = respuesta del autor, pendiente de confirmación del docente.

### 3.1 Eventos y publicación
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| E1 | ¿Qué datos debe tener un evento y cuáles son obligatorios? | Obligatorios: título, tipo, fecha/hora de inicio, fecha/hora de fin, lugar o enlace, cupo máximo, organizador. Opcionales: descripción, imagen. Automáticos: estado, fecha de creación. | Respondida |
| E2 | ¿Qué tipos de actividad existen? ¿Es una lista fija? | Lista fija: conferencia, taller, seminario, capacitación (campo con valores permitidos, sin pantalla de administración). | Respondida |
| E3 | ¿Qué estados tiene un evento y quién cambia cada uno? | `borrador` (lo crea el organizador; solo él lo ve) -> `publicado` (organizador o coordinación) -> `cancelado` (organizador o coordinación). `finalizado` lo asigna el sistema al pasar la fecha de fin. | Respondida |
| E4 | ¿Un evento publicado se puede editar o cancelar? ¿Qué pasa con las inscripciones? | Editar un publicado: sí, sin bajar el cupo por debajo de los inscritos activos y no si está finalizado o cancelado. Cancelar: las inscripciones se conservan con estado `cancelada_por_evento`. | Respondida |
| E5 | ¿Se permiten fechas en el pasado? ¿Hay validación de fechas o duración? | Inicio posterior al momento actual; fin posterior al inicio; duración máxima de 8 horas (un evento de varios días se registra como actividades separadas). | Respondida |

### 3.2 Inscripción y cupos
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| I1 | ¿Quién puede inscribirse? ¿Se requiere cuenta? | Cualquier miembro de la comunidad (estudiante, docente o externo; el rol es un dato). Sin cuentas de participante: formulario de datos básicos sin contraseña. | Respondida |
| I2 | ¿Qué datos del participante se piden? | Obligatorios: nombre completo, correo, documento de identidad, rol. Opcional: programa académico. El participante se guarda una sola vez, identificado por su correo, y se reutiliza. Datos de prueba ficticios. | Respondida |
| I3 | ¿Puede inscribirse dos veces al mismo evento? ¿Cómo se identifica a la persona? | No: una inscripción activa por evento. Se identifica por correo único, normalizado (minúsculas, sin espacios). Si la anterior fue cancelada, puede volver a inscribirse. El duplicado se rechaza con HTTP 409 sin alterar datos. | Respondida |
| I4 | ¿Se puede cancelar una inscripción? ¿Hasta cuándo? ¿Libera el cupo? | Sí, mientras el evento no haya iniciado; libera el cupo; no se borra, pasa a `cancelada`. Iniciado el evento, solo el organizador o la coordinación cambian el estado de una inscripción. El participante se identifica con correo y documento. | Respondida |
| I5 | Con cupo agotado, ¿se rechaza o hay lista de espera? | Se rechaza con HTTP 409 ("cupo agotado"), sin lista de espera (mejora futura). La verificación del cupo y el guardado de la inscripción son una sola operación atómica (transacción). | Respondida |
| I6 | ¿Hay fecha límite de inscripción? ¿Se puede inscribir a un evento iniciado o finalizado? | Sin fecha límite propia: las inscripciones cierran cuando el evento inicia. Solo en eventos `publicado` que no han empezado; `borrador`, `cancelado` y `finalizado` las rechazan (HTTP 409 o 422). | Respondida |
| I7 | ¿Se impide inscribirse a dos eventos que se crucen en horario? | Sí. Hay solapamiento si `inicio_A < fin_B` y `inicio_B < fin_A`; si uno termina justo cuando empieza el otro, no hay conflicto. Se rechaza con HTTP 409 indicando con qué evento se cruza. | Respondida |

### 3.3 Asistencia
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| A1 | ¿Quién registra la asistencia y cuándo? | El organizador del evento o la coordinación; el participante no puede marcar la suya. Desde el inicio del evento hasta 2 horas después de su fin. Por participante inscrito, uno a uno o en lote. Solo en eventos `publicado` o `finalizado`. | Respondida |
| A2 | ¿Solo presente/ausente o hay más estados? | Solo `presente` y `ausente`. Al abrirse la ventana, los inscritos activos quedan `ausente` por defecto. Un cambio a `presente` guarda fecha, hora y quién lo hizo. Tardanza y excusa son mejora futura. | Respondida |
| A3 | ¿Se puede registrar asistencia de alguien no inscrito? | Solo con inscripción activa, salvo la **inscripción en el momento**: el organizador o la coordinación pueden inscribir a una persona y marcar su asistencia en un solo paso, si el evento está `publicado`, ya inició, no ha terminado y hay cupo. Aplican las mismas reglas de cupo, duplicados y cruce de horarios. Si es una persona nueva, se crea su registro con los datos mínimos. En cualquier otro caso se rechaza con HTTP 422. | Respondida |
| A4 | ¿Se puede corregir una asistencia ya registrada? | Sí, cambiar entre `presente` y `ausente` hasta 24 horas después del fin del evento; luego queda cerrada. Se guarda quién y cuándo hizo el último cambio, sin historial completo. | Respondida |

### 3.4 Usuarios, permisos y reportes
| # | Pregunta | Respuesta | Estado |
|---|---|---|---|
| U1 | ¿Se requiere inicio de sesión? ¿Roles simples o autenticación completa? | Participantes sin sesión. Organizadores y coordinación inician sesión con correo y contraseña (guardada con hash). La API entrega un token. Dos roles: `organizador` y `coordinacion`; 401 sin sesión y 403 si el rol no corresponde. Sin registro público de personal: los usuarios de prueba, ficticios, los crea el script de datos. El token expira a las 00:00 (hora de Colombia) de cada día, sin renovación automática. | Respondida |
| U2 | ¿Un organizador gestiona solo sus eventos o todos? | El organizador gestiona solo los suyos. La coordinación tiene los mismos permisos sobre todos los eventos, incluida la creación, y además los consolidados. Al crear un evento, la coordinación elige el organizador responsable (por defecto ella misma). Sin rol administrador. | Respondida |
| U3 | ¿Qué debe ver la coordinación? ¿Con qué filtros? | Por evento: título, tipo, fecha, organizador, estado, cupo, inscritos activos, cupos disponibles, asistentes y porcentaje de asistencia (asistentes ÷ inscritos activos). Totales: eventos por estado, inscripciones activas y asistentes. Filtros: rango de fechas, tipo, estado y organizador. Todo calculado desde la base de datos. | Respondida |
| U4 | ¿Hay requisitos de rendimiento, idioma o dispositivos? | Interfaz en español (inglés es mejora futura). Responsive, deseable. Chrome, Edge y Firefox recientes. Sin metas formales de rendimiento. Fechas en hora de Colombia (`America/Bogota`) y guardadas en UTC. | Respondida |

## 4. Reglas de negocio

| ID | Regla | Estado |
|---|---|---|
| RN-01 | Las inscripciones activas de un evento nunca superan su cupo. | [SUPUESTO] |
| RN-02 | Un participante tiene como máximo una inscripción activa por evento (identificado por correo normalizado). Tras cancelar puede volver a inscribirse. | [SUPUESTO] |
| RN-03 | Solo se admiten inscripciones en eventos `publicado`. | [SUPUESTO] |
| RN-04 | La inscripción cierra cuando el evento inicia. Excepción: durante el evento, el organizador o la coordinación pueden hacer una inscripción en el momento (con cupo y evento `publicado` sin terminar). | [SUPUESTO] |
| RN-05 | Cancelar una inscripción, posible hasta el inicio del evento, libera el cupo; no se borra. | [SUPUESTO] |
| RN-06 | Solo participantes con inscripción activa pueden tener asistencia registrada (o inscritos en el momento según RN-04). | [SUPUESTO] |
| RN-07 | El organizador solo gestiona sus eventos; la coordinación gestiona todos. | [SUPUESTO] |
| RN-08 | El cupo de un evento no puede reducirse por debajo de sus inscritos activos. | [SUPUESTO] |
| RN-09 | El inicio debe ser posterior al momento actual, el fin posterior al inicio, y la duración máxima es de 8 horas. | [SUPUESTO] |
| RN-10 | Un participante no puede tener dos inscripciones activas en eventos con horarios solapados. | [SUPUESTO] |
| RN-11 | La asistencia se registra desde el inicio del evento hasta 2 horas después de su fin, y se corrige hasta 24 horas después del fin. | [SUPUESTO] |
| RN-12 | Estados de evento: `borrador`, `publicado`, `cancelado` y `finalizado` (este último lo asigna el sistema al pasar la fecha de fin). | [SUPUESTO] |
| RN-13 | Cancelar un evento conserva sus inscripciones con estado `cancelada_por_evento`. | [SUPUESTO] |
| RN-14 | Los tokens de sesión expiran cada día a las 00:00, hora de Colombia. | [SUPUESTO] |

## 5. Requisitos funcionales

Prioridad MoSCoW: **M** debe, **S** debería, **C** podría.

| ID | Requisito | Prioridad | Condición |
|---|---|---|---|
| RF-01 | Crear una actividad con título, tipo, inicio, fin, lugar o enlace, cupo y organizador (opcionales: descripción, imagen). | M | CA-01 |
| RF-02 | Publicar una actividad para que aparezca en el catálogo. | M | CA-01 |
| RF-03 | Editar y cancelar una actividad según su estado y las reglas aprobadas. | M | CA-01 |
| RF-04 | Consultar el catálogo de eventos publicados con su disponibilidad de cupos. | M | CA-02 |
| RF-05 | Consultar el detalle de un evento. | M | CA-02 |
| RF-06 | Inscribir a un participante en un evento publicado. | M | CA-03 |
| RF-07 | Consultar las inscripciones de un participante y la lista de inscritos de un evento. | M | CA-03, CA-05 |
| RF-08 | Rechazar inscripciones que excedan el cupo, sean duplicadas, se crucen en horario o incumplan reglas, sin alterar los datos. | M | CA-04 |
| RF-09 | Cancelar una inscripción y liberar el cupo. | M | CA-04 |
| RF-10 | Registrar la asistencia de un inscrito a un evento. | M | CA-05 |
| RF-11 | Consultar la lista de participantes con su asistencia. | M | CA-05 |
| RF-12 | Consultar información consolidada por evento y totales generales. | M | CA-06 |
| RF-13 | Restringir la gestión de eventos, inscritos y asistencia según el rol y la propiedad del evento. | M | CA-01, CA-05 |
| RF-14 | Filtrar los consolidados por rango de fechas, tipo, estado y organizador. | S | CA-06 |
| RF-15 | Inscribir en el momento a una persona y marcar su asistencia en un solo paso. | S | CA-03, CA-05 |
| RF-16 | Iniciar sesión con correo y contraseña (organizador y coordinación), con expiración diaria del token. | M | CA-01, CA-05, CA-06 |
| RF-17 | Corregir una asistencia ya registrada dentro del plazo permitido. | M | CA-05 |
| RF-18 | Marcar automáticamente como `finalizado` los eventos cuya fecha de fin ya pasó. | S | CA-02, CA-06 |

## 6. Requisitos no funcionales

| ID | Requisito | Prioridad |
|---|---|---|
| RNF-01 | Persistencia en base de datos relacional; los datos sobreviven a reinicios. | M |
| RNF-02 | Validación de datos en el servidor, aunque la solicitud no venga de la interfaz. | M |
| RNF-03 | Respuestas HTTP con códigos adecuados y mensajes de error que no revelen información sensible. | M |
| RNF-04 | Sin credenciales reales en el repositorio; configuración mediante `.env` y `.env.example`. | M |
| RNF-05 | Uso exclusivo de datos ficticios. | M |
| RNF-06 | Control de concurrencia: dos inscripciones simultáneas no superan el cupo (transacción). | M |
| RNF-07 | Interfaz usable en escritorio y móvil (responsive). | C |
| RNF-08 | Instrucciones reproducibles de instalación y ejecución en más de un equipo. | M |
| RNF-09 | Interfaz en español; navegadores Chrome, Edge y Firefox recientes. | M |
| RNF-10 | Fechas mostradas en hora de Colombia (`America/Bogota`) y guardadas en UTC. | M |
| RNF-11 | Contraseñas guardadas con hash, nunca en texto plano. | M |

## 7. Historias de usuario y criterios de aceptación

**HU-01 - Publicar una actividad** (RF-01, RF-02, RF-13, RF-16 / CA-01)
Como organizador o coordinación, quiero crear y publicar una actividad para que los participantes la vean.
- Dado un usuario autorizado y datos válidos, cuando crea y publica el evento, entonces queda guardado y aparece en el catálogo.
- Dados datos inválidos (título vacío, cupo ≤ 0, inicio en el pasado, duración mayor a 8 horas), cuando intenta crearlo, entonces se rechaza y no se guarda nada.

**HU-02 - Consultar eventos** (RF-04, RF-05 / CA-02)
Como participante, quiero ver los eventos y sus cupos disponibles para decidir a cuál inscribirme.
- Dado un catálogo con eventos, cuando lo consulto, entonces veo solo los publicados con cupos coherentes con las inscripciones.
- Dado un identificador inexistente, cuando consulto el detalle, entonces recibo un error controlado.

**HU-03 - Inscribirse** (RF-06, RF-07 / CA-03)
Como participante, quiero inscribirme en una actividad para reservar mi cupo.
- Dados datos válidos y cupo disponible, cuando me inscribo, entonces la inscripción queda guardada y puedo consultarla.
- Dados datos inválidos, cuando me inscribo, entonces se rechaza con un mensaje claro.

**HU-04 - Control de cupos y duplicados** (RF-08, RF-09 / CA-04)
Como organizador, quiero que el sistema impida sobrecupos, duplicados y cruces de horario para mantener la información consistente.
- Dado un evento con cupo agotado, cuando alguien intenta inscribirse, entonces se rechaza y el cupo no cambia.
- Dado un participante ya inscrito, cuando intenta inscribirse de nuevo, entonces se rechaza según RN-02.
- Dado un participante inscrito en un evento que se cruza en horario, cuando intenta inscribirse en otro, entonces se rechaza según RN-10.

**HU-05 - Registrar y corregir asistencia** (RF-10, RF-11, RF-13, RF-17 / CA-05)
Como organizador o coordinación, quiero registrar y consultar la asistencia de los inscritos para tener el control real del evento.
- Dado un inscrito y una ventana de registro abierta, cuando registro su asistencia, entonces se guarda asociada al evento y al participante.
- Dado un usuario sin autorización (sin sesión, o un organizador sobre un evento ajeno), cuando intenta registrar asistencia, entonces la operación es impedida.
- Dada una asistencia registrada dentro de las 24 horas posteriores al fin, cuando la corrijo, entonces se actualiza; pasado ese plazo se rechaza.

**HU-06 - Consolidado** (RF-12, RF-14 / CA-06)
Como coordinación, quiero ver un resumen de eventos, inscripciones y asistencia para supervisar la programación.
- Dados varios eventos, cuando consulto el consolidado, entonces veo cupo, inscritos, asistentes y estado de cada uno, con totales coherentes.
- Dados filtros por fecha, tipo, estado u organizador, cuando los aplico, entonces el resultado respeta los filtros.

**HU-07 - Inscripción en el momento** (RF-15 / CA-03, CA-05)
Como organizador o coordinación, quiero inscribir a una persona que llega sin inscripción previa y registrar su asistencia, siempre que haya cupo.
- Dado un evento `publicado` en curso con cupo, cuando inscribo en el momento a una persona, entonces queda inscrita y con asistencia `presente`.
- Dado un evento sin cupo, `borrador`, `cancelado` o `finalizado`, cuando lo intento, entonces se rechaza.

## 8. Trazabilidad preliminar con las condiciones de aceptación

| Condición | Requisitos | Historias |
|---|---|---|
| CA-01 | RF-01, RF-02, RF-03, RF-13, RF-16 | HU-01 |
| CA-02 | RF-04, RF-05, RF-18 | HU-02 |
| CA-03 | RF-06, RF-07, RF-15 | HU-03, HU-07 |
| CA-04 | RF-08, RF-09 | HU-04 |
| CA-05 | RF-07, RF-10, RF-11, RF-13, RF-15, RF-17 | HU-05, HU-07 |
| CA-06 | RF-12, RF-14, RF-16, RF-18 | HU-06 |

## 9. Registro de decisiones y pendientes

| Fecha | Decisión / acuerdo | Fuente |
|---|---|---|
| 2026-11-23 | E1-E5 e I1 respondidas por el autor (sin sesión con el docente). | Autor |
| 2026-11-24 | I2-I7, A1-A4 y U1-U4 respondidas por el autor. Cambios respecto a la propuesta inicial: duración máxima de 8 horas; registro de asistencia hasta 2 horas tras el fin y corrección hasta 24 horas; inscripción en el momento permitida; token que expira a medianoche; la coordinación tiene los permisos del organizador sobre todos los eventos, incluida la creación; interfaz en inglés como mejora futura. | Autor |

**Pendiente:** confirmar con el docente las respuestas (todas son supuestos) y obtener la aprobación del alcance, las reglas de negocio (sección 4) y las prioridades (sección 5).
