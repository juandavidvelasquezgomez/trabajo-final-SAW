"""La base de datos rechaza por sí sola datos duplicados, sin normalizar o incoherentes,
aunque una validación de la API fallara (segunda línea de defensa)."""
import sqlite3

import pytest

from app import db
from ayudas import crear_usuario


def insertar(sql, params=()):
    with db.transaccion() as conn:
        return conn.execute(sql, params).lastrowid


def usuario():
    return crear_usuario("Ana Torres", "ana@ejemplo.test", "organizador")


def evento(org_id, **c):
    d = {"titulo": "Taller de Python", "tipo": "taller", "inicio": "2026-12-10T19:00:00Z",
         "fin": "2026-12-10T22:00:00Z", "lugar": "Aula 1", "cupo": 2, "organizador_id": org_id}
    d.update(c)
    cols = ", ".join(d)
    return insertar(f"INSERT INTO eventos ({cols}) VALUES ({', '.join('?' * len(d))})", tuple(d.values()))


def participante(n=1, **c):
    d = {"nombre_completo": f"Persona {n}", "correo": f"p{n}@ejemplo.test", "documento": f"10000000{n:02d}", "rol": "estudiante"}
    d.update(c)
    cols = ", ".join(d)
    return insertar(f"INSERT INTO participantes ({cols}) VALUES ({', '.join('?' * len(d))})", tuple(d.values()))


def test_correo_de_usuario_debe_estar_normalizado_y_ser_unico():
    usuario()
    for correo in ("Ana@ejemplo.test", " ana2@ejemplo.test", "sin-arroba", "a b@c.com"):
        with pytest.raises(sqlite3.IntegrityError):
            crear_usuario("Otra Persona", correo, "organizador")
    with pytest.raises(sqlite3.IntegrityError):
        crear_usuario("Otra Persona", "ana@ejemplo.test", "organizador")  # duplicado


def test_participante_correo_y_documento_unicos_y_normalizados():
    participante(1)
    for datos in ({"correo": "p1@ejemplo.test", "documento": "5555555555"},       # correo repetido
                  {"correo": "nuevo@ejemplo.test", "documento": "1000000001"},    # documento repetido
                  {"correo": "NUEVO@ejemplo.test", "documento": "5555555555"},    # correo sin normalizar
                  {"correo": "nuevo@ejemplo.test", "documento": "ab-12345"},      # documento con símbolo
                  {"correo": "nuevo@ejemplo.test", "documento": "ab12345"},       # documento en minúscula
                  {"correo": "nuevo@ejemplo.test", "documento": "123"},           # demasiado corto
                  {"correo": "nuevo@ejemplo.test", "documento": "5555555555", "rol": "admin"},
                  {"correo": "nuevo@ejemplo.test", "documento": "5555555555", "nombre_completo": " Con espacios "}):
        with pytest.raises(sqlite3.IntegrityError):
            participante(2, **datos)


@pytest.mark.parametrize("cambios", [
    {"cupo": 0}, {"cupo": -3}, {"cupo": 10001}, {"tipo": "fiesta"}, {"estado": "otro"},
    {"fin": "2026-12-10T19:00:00Z"},                    # fin = inicio
    {"fin": "2026-12-10T18:00:00Z"},                    # fin antes del inicio
    {"fin": "2026-12-11T03:00:01Z"},                    # más de 8 horas
    {"titulo": "ab"}, {"titulo": " espacios "}, {"lugar": "x"}, {"imagen_url": "javascript:alert(1)"},
    {"organizador_id": 9999},                           # organizador inexistente (clave foránea)
])
def test_evento_con_datos_incoherentes_es_rechazado(cambios):
    org = usuario()
    with pytest.raises(sqlite3.IntegrityError):
        evento(org, **cambios)


def test_duracion_de_exactamente_8_horas_es_valida():
    evento(usuario(), fin="2026-12-11T03:00:00Z")


def test_no_se_puede_repetir_el_mismo_evento_pero_si_tras_cancelarlo():
    org = usuario()
    evento(org)
    with pytest.raises(sqlite3.IntegrityError):
        evento(org, titulo="TALLER DE PYTHON")           # mismo título (sin distinguir mayúsculas) e inicio
    evento(org, inicio="2026-12-11T19:00:00Z", fin="2026-12-11T20:00:00Z")   # otra hora: permitido
    with db.transaccion() as conn:
        conn.execute("UPDATE eventos SET estado = 'cancelado' WHERE id = 1")
    evento(org)                                          # el cancelado no bloquea


def test_inscripcion_activa_unica_por_evento_y_participante():
    ev, p = evento(usuario()), participante(1)
    insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, p))
    with pytest.raises(sqlite3.IntegrityError):
        insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, p))
    insertar("UPDATE inscripciones SET estado = 'cancelada'")
    insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, p))   # tras cancelar, sí


def test_el_disparador_impide_superar_el_cupo():
    ev = evento(usuario(), cupo=2)
    for n in (1, 2):
        insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, participante(n)))
    with pytest.raises(sqlite3.IntegrityError, match="CUPO_AGOTADO"):
        insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, participante(3)))
    with db.lectura() as conn:
        assert conn.execute("SELECT count(*) FROM inscripciones").fetchone()[0] == 2


def test_no_se_puede_reactivar_una_inscripcion_con_el_cupo_lleno():
    ev = evento(usuario(), cupo=1)
    a = insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, participante(1)))
    insertar("UPDATE inscripciones SET estado = 'cancelada' WHERE id = ?", (a,))
    insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, participante(2)))
    with pytest.raises(sqlite3.IntegrityError, match="CUPO_AGOTADO"):
        insertar("UPDATE inscripciones SET estado = 'activa' WHERE id = ?", (a,))


def test_asistencia_solo_de_inscripciones_activas_y_una_por_inscripcion():
    org = usuario()
    ev = evento(org)
    ins = insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)", (ev, participante(1)))
    insertar("INSERT INTO asistencias (inscripcion_id, estado, registrado_por, registrado_en) "
             "VALUES (?, 'presente', ?, '2026-12-10T20:00:00Z')", (ins, org))
    with pytest.raises(sqlite3.IntegrityError):
        insertar("INSERT INTO asistencias (inscripcion_id, estado, registrado_por, registrado_en) "
                 "VALUES (?, 'ausente', ?, '2026-12-10T20:00:00Z')", (ins, org))            # duplicada
    with pytest.raises(sqlite3.IntegrityError):
        insertar("INSERT INTO asistencias (inscripcion_id, estado, registrado_por, registrado_en) "
                 "VALUES (?, 'tarde', ?, '2026-12-10T20:00:00Z')", (ins, org))               # estado inválido
    cancelada = insertar("INSERT INTO inscripciones (evento_id, participante_id, estado) VALUES (?, ?, 'cancelada')",
                         (ev, participante(2)))
    with pytest.raises(sqlite3.IntegrityError, match="PARTICIPANTE_NO_INSCRITO"):
        insertar("INSERT INTO asistencias (inscripcion_id, estado, registrado_por, registrado_en) "
                 "VALUES (?, 'presente', ?, '2026-12-10T20:00:00Z')", (cancelada, org))


def test_claves_foraneas_activas():
    with pytest.raises(sqlite3.IntegrityError):
        insertar("INSERT INTO inscripciones (evento_id, participante_id) VALUES (999, 999)")


def test_el_esquema_se_puede_aplicar_varias_veces():
    db.iniciar_bd()
    db.iniciar_bd()
