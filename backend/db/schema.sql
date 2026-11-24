-- Esquema de la base de datos (SQLite). Es idempotente: se puede ejecutar varias veces.
-- Las restricciones son la última línea de defensa: aunque falle una validación de la
-- API, la base de datos rechaza datos duplicados, sin normalizar o incoherentes.
-- Las fechas se guardan en UTC con el formato AAAA-MM-DDTHH:MM:SSZ.

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL
                  CHECK (nombre = trim(nombre) AND length(nombre) BETWEEN 3 AND 100),
    correo        TEXT    NOT NULL UNIQUE
                  CHECK (correo = lower(trim(correo)) AND length(correo) BETWEEN 6 AND 254
                         AND instr(correo, '@') > 1 AND instr(correo, ' ') = 0),
    password_hash TEXT    NOT NULL CHECK (password_hash LIKE 'scrypt$%'),
    rol           TEXT    NOT NULL CHECK (rol IN ('organizador', 'coordinacion')),
    activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS participantes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL
                    CHECK (nombre_completo = trim(nombre_completo)
                           AND length(nombre_completo) BETWEEN 3 AND 100),
    -- correo y documento normalizados y únicos: una persona = un registro
    correo          TEXT NOT NULL UNIQUE
                    CHECK (correo = lower(trim(correo)) AND length(correo) BETWEEN 6 AND 254
                           AND instr(correo, '@') > 1 AND instr(correo, ' ') = 0),
    documento       TEXT NOT NULL UNIQUE
                    CHECK (documento = upper(documento) AND length(documento) BETWEEN 5 AND 20
                           AND documento NOT GLOB '*[^A-Z0-9]*'),
    rol             TEXT NOT NULL CHECK (rol IN ('estudiante', 'docente', 'externo')),
    programa        TEXT CHECK (programa IS NULL OR length(programa) BETWEEN 2 AND 100),
    creado_en       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS eventos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo          TEXT NOT NULL CHECK (titulo = trim(titulo) AND length(titulo) BETWEEN 3 AND 150),
    descripcion     TEXT CHECK (descripcion IS NULL OR length(descripcion) <= 2000),
    tipo            TEXT NOT NULL CHECK (tipo IN ('conferencia', 'taller', 'seminario', 'capacitacion')),
    inicio          TEXT NOT NULL,
    fin             TEXT NOT NULL,
    lugar           TEXT NOT NULL CHECK (lugar = trim(lugar) AND length(lugar) BETWEEN 2 AND 200),
    cupo            INTEGER NOT NULL CHECK (cupo BETWEEN 1 AND 10000),
    imagen_url      TEXT CHECK (imagen_url IS NULL
                                OR (length(imagen_url) <= 500
                                    AND (imagen_url LIKE 'http://%' OR imagen_url LIKE 'https://%'))),
    estado          TEXT NOT NULL DEFAULT 'borrador'
                    CHECK (estado IN ('borrador', 'publicado', 'cancelado', 'finalizado')),
    organizador_id  INTEGER NOT NULL REFERENCES usuarios (id),
    creado_en       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    actualizado_en  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- RN-09: el fin es posterior al inicio y la duración máxima es de 8 horas (28800 s)
    CHECK (CAST(strftime('%s', fin) AS INTEGER) - CAST(strftime('%s', inicio) AS INTEGER)
           BETWEEN 1 AND 28800)
);

CREATE TABLE IF NOT EXISTS inscripciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id       INTEGER NOT NULL REFERENCES eventos (id),
    participante_id INTEGER NOT NULL REFERENCES participantes (id),
    estado          TEXT NOT NULL DEFAULT 'activa'
                    CHECK (estado IN ('activa', 'cancelada', 'cancelada_por_evento')),
    en_el_momento   INTEGER NOT NULL DEFAULT 0 CHECK (en_el_momento IN (0, 1)),
    creada_en       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    cancelada_en    TEXT
);

CREATE TABLE IF NOT EXISTS asistencias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inscripcion_id  INTEGER NOT NULL UNIQUE REFERENCES inscripciones (id),
    estado          TEXT NOT NULL CHECK (estado IN ('presente', 'ausente')),
    registrado_por  INTEGER NOT NULL REFERENCES usuarios (id),
    registrado_en   TEXT NOT NULL
);

-- RN-02: como máximo UNA inscripción activa por participante y evento.
CREATE UNIQUE INDEX IF NOT EXISTS ux_inscripcion_activa
    ON inscripciones (evento_id, participante_id) WHERE estado = 'activa';

-- Evita crear dos veces el mismo evento (mismo organizador, título e inicio).
CREATE UNIQUE INDEX IF NOT EXISTS ux_evento_repetido
    ON eventos (organizador_id, lower(titulo), inicio) WHERE estado <> 'cancelado';

CREATE INDEX IF NOT EXISTS ix_inscripciones_evento ON inscripciones (evento_id, estado);
CREATE INDEX IF NOT EXISTS ix_inscripciones_participante ON inscripciones (participante_id, estado);
CREATE INDEX IF NOT EXISTS ix_eventos_estado_inicio ON eventos (estado, inicio);

-- RN-01: segunda línea de defensa contra el sobrecupo.
CREATE TRIGGER IF NOT EXISTS trg_cupo_insert
BEFORE INSERT ON inscripciones
WHEN NEW.estado = 'activa'
BEGIN
    SELECT RAISE(ABORT, 'CUPO_AGOTADO')
    WHERE (SELECT count(*) FROM inscripciones
           WHERE evento_id = NEW.evento_id AND estado = 'activa')
          >= (SELECT cupo FROM eventos WHERE id = NEW.evento_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_cupo_update
BEFORE UPDATE OF estado ON inscripciones
WHEN NEW.estado = 'activa' AND OLD.estado <> 'activa'
BEGIN
    SELECT RAISE(ABORT, 'CUPO_AGOTADO')
    WHERE (SELECT count(*) FROM inscripciones
           WHERE evento_id = NEW.evento_id AND estado = 'activa')
          >= (SELECT cupo FROM eventos WHERE id = NEW.evento_id);
END;

-- RN-06: solo una inscripción activa puede tener asistencia.
CREATE TRIGGER IF NOT EXISTS trg_asistencia_inscripcion_activa
BEFORE INSERT ON asistencias
WHEN (SELECT estado FROM inscripciones WHERE id = NEW.inscripcion_id) <> 'activa'
BEGIN
    SELECT RAISE(ABORT, 'PARTICIPANTE_NO_INSCRITO');
END;
