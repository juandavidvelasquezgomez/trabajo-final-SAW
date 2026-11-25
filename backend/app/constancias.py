"""Extensión: constancia de asistencia (RF-19). NO es un certificado con firma digital.

Se emite solo si la inscripción está activa, la asistencia quedó como 'presente' y el evento
finalizó. El código de verificación es un HMAC (con SECRET_KEY) del identificador de la
inscripción: no se puede inventar sin la clave. La verificación consulta la base de datos, así que
si la asistencia se corrige, la constancia deja de ser válida."""
import hashlib
import hmac
import re

from . import config, db, reglas, tiempo
from .errores import ErrorApi

_FORMATO = re.compile(r"^EA-([1-9]\d{0,9})-[0-9A-F]{16}$")

_SQL = """
SELECT i.id, p.nombre_completo, p.documento, e.titulo, e.tipo, e.inicio, e.fin, e.lugar, u.nombre AS organizador
  FROM inscripciones i
  JOIN participantes p ON p.id = i.participante_id
  JOIN eventos e ON e.id = i.evento_id
  JOIN usuarios u ON u.id = e.organizador_id
  JOIN asistencias a ON a.inscripcion_id = i.id
 WHERE i.estado = 'activa' AND a.estado = 'presente' AND e.estado = 'finalizado'
"""


def codigo_de(inscripcion_id: int) -> str:
    firma = hmac.new(config.obtener_secret_key().encode(), f"constancia:{inscripcion_id}".encode(),
                     hashlib.sha256).hexdigest()[:16].upper()
    return f"EA-{inscripcion_id}-{firma}"


def _constancia(fila, documento: str) -> dict:
    segundos = (tiempo.de_texto(fila["fin"]) - tiempo.de_texto(fila["inicio"])).total_seconds()
    return {
        "codigo": codigo_de(fila["id"]),
        "participante": {"nombre_completo": fila["nombre_completo"], "documento": documento},
        "evento": {"titulo": fila["titulo"], "tipo": fila["tipo"], "lugar": fila["lugar"],
                   "organizador": fila["organizador"], "inicio": tiempo.a_bogota_iso(fila["inicio"]),
                   "fin": tiempo.a_bogota_iso(fila["fin"]), "duracion_horas": round(segundos / 3600, 2)},
    }


def de_participante(correo: str, documento: str) -> list[dict]:
    reglas.actualizar_estados()
    with db.lectura() as conn:
        filas = conn.execute(_SQL + " AND p.correo = ? AND p.documento = ? ORDER BY e.inicio DESC",
                             (correo, documento)).fetchall()
    if not filas:  # misma respuesta si los datos no coinciden o si aún no hay constancia
        raise ErrorApi(404, "CONSTANCIA_NO_DISPONIBLE",
                       "No hay constancias con esos datos. Se requiere inscripción activa, asistencia "
                       "registrada como presente y que el evento haya finalizado.")
    return [_constancia(f, f["documento"]) for f in filas]


def verificar(codigo: str) -> dict:
    """Comprueba un código. Muestra el documento enmascarado: quien verifica solo lo coteja."""
    invalida = ErrorApi(404, "CONSTANCIA_NO_VALIDA", "El código no corresponde a una constancia válida.")
    codigo = codigo.strip().upper()
    coincidencia = _FORMATO.match(codigo)
    if not coincidencia or int(coincidencia[1]) > 2147483647:
        raise invalida
    inscripcion_id = int(coincidencia[1])
    if not hmac.compare_digest(codigo, codigo_de(inscripcion_id)):
        raise invalida
    reglas.actualizar_estados()
    with db.lectura() as conn:
        fila = conn.execute(_SQL + " AND i.id = ?", (inscripcion_id,)).fetchone()
    if not fila:
        raise invalida
    oculto = "•" * max(len(fila["documento"]) - 4, 0) + fila["documento"][-4:]
    return {"valida": True, **_constancia(fila, oculto)}
