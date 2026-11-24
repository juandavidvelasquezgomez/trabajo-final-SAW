"""Reglas de negocio (RN-01..RN-14). Todo lo que modifica datos ocurre dentro de una
transacción: si una regla falla, no se guarda nada (CA-04). Los routers solo llaman aquí."""
import sqlite3
from datetime import datetime, timedelta

from . import config, db, tiempo
from .errores import ErrorApi
from .schemas import EventoCrear, EventoEditar, ParticipanteIn

COLUMNAS_EDITABLES = ("titulo", "descripcion", "tipo", "inicio", "fin", "lugar", "cupo",
                      "imagen_url", "organizador_id")


# ------------------------------------------------------------------ utilidades
def _traducir_integridad(exc: sqlite3.IntegrityError) -> ErrorApi:
    """Convierte un rechazo de la base de datos en un error claro, sin exponer su mensaje."""
    msg = str(exc)
    if "CUPO_AGOTADO" in msg:
        return ErrorApi(409, "CUPO_AGOTADO", "El evento no tiene cupos disponibles.")
    if "PARTICIPANTE_NO_INSCRITO" in msg:
        return ErrorApi(422, "PARTICIPANTE_NO_INSCRITO", "El participante no tiene una inscripción activa.")
    if "ux_inscripcion_activa" in msg:
        return ErrorApi(409, "INSCRIPCION_DUPLICADA", "El participante ya tiene una inscripción activa en este evento.")
    if "ux_evento_repetido" in msg:
        return ErrorApi(409, "EVENTO_DUPLICADO", "Ya existe un evento igual (mismo organizador, título e inicio).")
    if "participantes" in msg:
        return ErrorApi(409, "DATOS_PARTICIPANTE_EN_CONFLICTO",
                        "El correo o el documento ya están registrados con datos diferentes.")
    return ErrorApi(422, "DATOS_INVALIDOS", "Los datos no cumplen las restricciones permitidas.")


def finalizar_vencidos(conn) -> None:
    """RF-18: los eventos publicados cuya fecha de fin ya pasó pasan a 'finalizado'."""
    ahora = tiempo.a_texto(tiempo.ahora())
    conn.execute("UPDATE eventos SET estado = 'finalizado', actualizado_en = ? "
                 "WHERE estado = 'publicado' AND fin <= ?", (ahora, ahora))


def actualizar_estados() -> None:
    with db.transaccion() as conn:
        finalizar_vencidos(conn)


_SQL_EVENTO = """
SELECT e.*, u.nombre AS organizador_nombre,
       (SELECT count(*) FROM inscripciones i
         WHERE i.evento_id = e.id AND i.estado = 'activa') AS inscritos_activos
  FROM eventos e JOIN usuarios u ON u.id = e.organizador_id
"""


def _fila_evento(conn, evento_id: int):
    fila = conn.execute(_SQL_EVENTO + " WHERE e.id = ?", (evento_id,)).fetchone()
    if not fila:
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", "El evento no existe.")
    return fila


def a_evento(f) -> dict:
    return {
        "id": f["id"], "titulo": f["titulo"], "descripcion": f["descripcion"], "tipo": f["tipo"],
        "inicio": tiempo.a_bogota_iso(f["inicio"]), "fin": tiempo.a_bogota_iso(f["fin"]),
        "lugar": f["lugar"], "cupo": f["cupo"], "imagen_url": f["imagen_url"], "estado": f["estado"],
        "inscritos_activos": f["inscritos_activos"],
        "cupos_disponibles": max(f["cupo"] - f["inscritos_activos"], 0),
        "organizador": {"id": f["organizador_id"], "nombre": f["organizador_nombre"]},
    }


def puede_gestionar(usuario: dict | None, evento) -> bool:
    return bool(usuario) and (usuario["rol"] == "coordinacion" or evento["organizador_id"] == usuario["id"])


def _exigir_gestion(usuario: dict, evento) -> None:
    if not puede_gestionar(usuario, evento):
        raise ErrorApi(403, "SIN_PERMISO", "No tienes permiso para gestionar este evento.")


def validar_fechas(inicio: datetime, fin: datetime, exigir_futuro: bool) -> None:
    if fin <= inicio:
        raise ErrorApi(422, "FECHAS_INVALIDAS", "La fecha de fin debe ser posterior a la de inicio.")
    if fin - inicio > timedelta(hours=config.DURACION_MAXIMA_HORAS):
        raise ErrorApi(422, "DURACION_EXCEDIDA",
                       f"La duración máxima de un evento es de {config.DURACION_MAXIMA_HORAS} horas.")
    if exigir_futuro and inicio <= tiempo.ahora():
        raise ErrorApi(422, "FECHA_EN_PASADO", "La fecha de inicio debe ser posterior al momento actual.")


def _organizador_valido(conn, organizador_id: int) -> None:
    fila = conn.execute("SELECT activo FROM usuarios WHERE id = ?", (organizador_id,)).fetchone()
    if not fila or not fila["activo"]:
        raise ErrorApi(422, "ORGANIZADOR_INVALIDO", "El organizador indicado no existe o está inactivo.")


# --------------------------------------------------------------------- eventos
def crear_evento(usuario: dict, d: EventoCrear) -> dict:
    validar_fechas(d.inicio, d.fin, exigir_futuro=True)
    organizador_id = usuario["id"]
    if d.organizador_id is not None and d.organizador_id != usuario["id"]:
        if usuario["rol"] != "coordinacion":
            raise ErrorApi(403, "SIN_PERMISO", "Solo la coordinación puede asignar otro organizador.")
        organizador_id = d.organizador_id
    try:
        with db.transaccion() as conn:
            _organizador_valido(conn, organizador_id)
            ahora = tiempo.a_texto(tiempo.ahora())
            cur = conn.execute(
                "INSERT INTO eventos (titulo, descripcion, tipo, inicio, fin, lugar, cupo, imagen_url, "
                "estado, organizador_id, creado_en, actualizado_en) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'borrador', ?, ?, ?)",
                (d.titulo, d.descripcion, d.tipo, tiempo.a_texto(d.inicio), tiempo.a_texto(d.fin),
                 d.lugar, d.cupo, d.imagen_url, organizador_id, ahora, ahora))
            return a_evento(_fila_evento(conn, cur.lastrowid))
    except sqlite3.IntegrityError as exc:
        raise _traducir_integridad(exc)


def editar_evento(usuario: dict, evento_id: int, d: EventoEditar) -> dict:
    cambios = {c: getattr(d, c) for c in d.model_fields_set}
    try:
        with db.transaccion() as conn:
            finalizar_vencidos(conn)
            ev = _fila_evento(conn, evento_id)
            _exigir_gestion(usuario, ev)
            if ev["estado"] not in ("borrador", "publicado"):
                raise ErrorApi(409, "EVENTO_NO_EDITABLE", "Un evento cancelado o finalizado no se puede editar.")
            ahora = tiempo.ahora()

            inicio_actual, fin_actual = tiempo.de_texto(ev["inicio"]), tiempo.de_texto(ev["fin"])
            nuevo_inicio = cambios.get("inicio", inicio_actual)
            nuevo_fin = cambios.get("fin", fin_actual)
            if nuevo_inicio != inicio_actual or nuevo_fin != fin_actual:
                if ahora >= inicio_actual:
                    raise ErrorApi(409, "EVENTO_YA_INICIADO", "No se pueden cambiar las fechas de un evento que ya inició.")
                validar_fechas(nuevo_inicio, nuevo_fin, exigir_futuro=nuevo_inicio != inicio_actual)
                if ev["inscritos_activos"] > 0:
                    raise ErrorApi(409, "FECHAS_BLOQUEADAS",
                                   "No se pueden cambiar las fechas de un evento con inscripciones activas.")
            if "cupo" in cambios and cambios["cupo"] < ev["inscritos_activos"]:
                raise ErrorApi(422, "CUPO_MENOR_A_INSCRITOS",
                               f"El cupo no puede ser menor que los inscritos activos ({ev['inscritos_activos']}).")
            if "organizador_id" in cambios and cambios["organizador_id"] != ev["organizador_id"]:
                if usuario["rol"] != "coordinacion":
                    raise ErrorApi(403, "SIN_PERMISO", "Solo la coordinación puede cambiar el organizador.")
                _organizador_valido(conn, cambios["organizador_id"])

            asignaciones, valores = [], []
            for col in COLUMNAS_EDITABLES:  # lista blanca: nunca se arma SQL con datos del usuario
                if col in cambios:
                    valor = cambios[col]
                    if col in ("inicio", "fin") and valor is not None:
                        valor = tiempo.a_texto(valor)
                    asignaciones.append(f"{col} = ?")
                    valores.append(valor)
            asignaciones.append("actualizado_en = ?")
            valores.append(tiempo.a_texto(ahora))
            conn.execute(f"UPDATE eventos SET {', '.join(asignaciones)} WHERE id = ?", (*valores, evento_id))
            return a_evento(_fila_evento(conn, evento_id))
    except sqlite3.IntegrityError as exc:
        raise _traducir_integridad(exc)


def cambiar_estado_evento(usuario: dict, evento_id: int, nuevo: str) -> dict:
    with db.transaccion() as conn:
        finalizar_vencidos(conn)
        ev = _fila_evento(conn, evento_id)
        _exigir_gestion(usuario, ev)
        ahora = tiempo.ahora()
        if nuevo == "publicado":
            if ev["estado"] != "borrador":
                raise ErrorApi(409, "TRANSICION_INVALIDA", "Solo se puede publicar un evento en borrador.")
            if ahora >= tiempo.de_texto(ev["inicio"]):
                raise ErrorApi(422, "FECHA_EN_PASADO", "No se puede publicar un evento que ya inició.")
        elif nuevo == "cancelado":
            if ev["estado"] not in ("borrador", "publicado"):
                raise ErrorApi(409, "TRANSICION_INVALIDA", "El evento ya está cancelado o finalizado.")
            # RN-13: las inscripciones se conservan, marcadas como canceladas por el evento
            conn.execute("UPDATE inscripciones SET estado = 'cancelada_por_evento', cancelada_en = ? "
                         "WHERE evento_id = ? AND estado = 'activa'", (tiempo.a_texto(ahora), evento_id))
        conn.execute("UPDATE eventos SET estado = ?, actualizado_en = ? WHERE id = ?",
                     (nuevo, tiempo.a_texto(ahora), evento_id))
        return a_evento(_fila_evento(conn, evento_id))


def catalogo(tipo: str | None, desde: datetime | None, hasta: datetime | None) -> list[dict]:
    actualizar_estados()
    sql = _SQL_EVENTO + " WHERE e.estado = 'publicado' AND e.fin > ?"
    params: list = [tiempo.a_texto(tiempo.ahora())]
    if tipo:
        sql += " AND e.tipo = ?"; params.append(tipo)
    if desde:
        sql += " AND e.inicio >= ?"; params.append(tiempo.a_texto(desde))
    if hasta:
        sql += " AND e.inicio <= ?"; params.append(tiempo.a_texto(hasta))
    with db.lectura() as conn:
        return [a_evento(f) for f in conn.execute(sql + " ORDER BY e.inicio, e.id", params)]


def detalle_evento(usuario: dict | None, evento_id: int) -> dict:
    actualizar_estados()
    with db.lectura() as conn:
        ev = _fila_evento(conn, evento_id)
    if ev["estado"] != "publicado" and not puede_gestionar(usuario, ev):
        raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", "El evento no existe.")  # no se revela su existencia
    return a_evento(ev)


def panel_eventos(usuario: dict, estado: str | None) -> list[dict]:
    actualizar_estados()
    sql, params = _SQL_EVENTO + " WHERE 1 = 1", []
    if usuario["rol"] != "coordinacion":
        sql += " AND e.organizador_id = ?"; params.append(usuario["id"])
    if estado:
        sql += " AND e.estado = ?"; params.append(estado)
    with db.lectura() as conn:
        return [a_evento(f) for f in conn.execute(sql + " ORDER BY e.inicio DESC, e.id DESC", params)]


def listar_organizadores() -> list[dict]:
    with db.lectura() as conn:
        return [dict(f) for f in conn.execute(
            "SELECT id, nombre, rol FROM usuarios WHERE activo = 1 ORDER BY nombre")]


# ----------------------------------------------------------------- inscripciones
def _asegurar_participante(conn, d: ParticipanteIn) -> int:
    """Una persona = un registro. El correo y el documento (ya normalizados) identifican a la
    persona; si uno existe asociado a datos distintos, se rechaza para no mezclar identidades."""
    por_correo = conn.execute("SELECT id FROM participantes WHERE correo = ?", (d.correo,)).fetchone()
    por_documento = conn.execute("SELECT id FROM participantes WHERE documento = ?", (d.documento,)).fetchone()
    if por_correo is None and por_documento is None:
        cur = conn.execute(
            "INSERT INTO participantes (nombre_completo, correo, documento, rol, programa, creado_en) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (d.nombre_completo, d.correo, d.documento, d.rol, d.programa, tiempo.a_texto(tiempo.ahora())))
        return cur.lastrowid
    if por_correo is not None and por_documento is not None and por_correo["id"] == por_documento["id"]:
        return por_correo["id"]
    raise ErrorApi(409, "DATOS_PARTICIPANTE_EN_CONFLICTO",
                   "El correo o el documento ya están registrados con datos diferentes.")


def _crear_inscripcion(conn, ev, participante_id: int, en_el_momento: bool) -> int:
    if conn.execute("SELECT 1 FROM inscripciones WHERE evento_id = ? AND participante_id = ? "
                    "AND estado = 'activa'", (ev["id"], participante_id)).fetchone():
        raise ErrorApi(409, "INSCRIPCION_DUPLICADA", "El participante ya tiene una inscripción activa en este evento.")
    cruce = conn.execute(
        "SELECT e.titulo FROM inscripciones i JOIN eventos e ON e.id = i.evento_id "
        "WHERE i.participante_id = ? AND i.estado = 'activa' AND e.id <> ? "
        "AND e.inicio < ? AND ? < e.fin LIMIT 1",
        (participante_id, ev["id"], ev["fin"], ev["inicio"])).fetchone()
    if cruce:
        raise ErrorApi(409, "CRUCE_DE_HORARIO",
                       f"El horario se cruza con otro evento en el que ya está inscrito: {cruce['titulo']}.")
    activas = conn.execute("SELECT count(*) FROM inscripciones WHERE evento_id = ? AND estado = 'activa'",
                           (ev["id"],)).fetchone()[0]
    if activas >= ev["cupo"]:
        raise ErrorApi(409, "CUPO_AGOTADO", "El evento no tiene cupos disponibles.")
    try:
        cur = conn.execute("INSERT INTO inscripciones (evento_id, participante_id, estado, en_el_momento, creada_en) "
                           "VALUES (?, ?, 'activa', ?, ?)",
                           (ev["id"], participante_id, int(en_el_momento), tiempo.a_texto(tiempo.ahora())))
    except sqlite3.IntegrityError as exc:
        raise _traducir_integridad(exc)
    return cur.lastrowid


def _respuesta_inscripcion(conn, inscripcion_id: int) -> dict:
    f = conn.execute(
        "SELECT i.id, i.evento_id, i.estado, i.en_el_momento, p.id AS pid, p.nombre_completo, p.correo, "
        "e.cupo, (SELECT count(*) FROM inscripciones x WHERE x.evento_id = e.id AND x.estado = 'activa') AS activas "
        "FROM inscripciones i JOIN participantes p ON p.id = i.participante_id "
        "JOIN eventos e ON e.id = i.evento_id WHERE i.id = ?", (inscripcion_id,)).fetchone()
    return {"id": f["id"], "evento_id": f["evento_id"], "estado": f["estado"],
            "en_el_momento": bool(f["en_el_momento"]), "cupos_disponibles": max(f["cupo"] - f["activas"], 0),
            "participante": {"id": f["pid"], "nombre_completo": f["nombre_completo"], "correo": f["correo"]}}


def inscribir(evento_id: int, d: ParticipanteIn) -> dict:
    with db.transaccion() as conn:  # una sola operación atómica: verificar cupo + guardar (RNF-06)
        finalizar_vencidos(conn)
        ev = _fila_evento(conn, evento_id)
        if ev["estado"] == "borrador":
            raise ErrorApi(404, "EVENTO_NO_ENCONTRADO", "El evento no existe.")
        if ev["estado"] in ("cancelado", "finalizado"):
            raise ErrorApi(409, "EVENTO_NO_ABIERTO", "El evento no admite inscripciones.")
        if tiempo.ahora() >= tiempo.de_texto(ev["inicio"]):
            raise ErrorApi(409, "EVENTO_YA_INICIADO", "Las inscripciones cierran cuando el evento inicia.")
        participante_id = _asegurar_participante(conn, d)
        return _respuesta_inscripcion(conn, _crear_inscripcion(conn, ev, participante_id, False))


def cancelar_inscripcion(evento_id: int, correo: str, documento: str) -> dict:
    with db.transaccion() as conn:
        finalizar_vencidos(conn)
        ev = _fila_evento(conn, evento_id)
        ins = conn.execute(
            "SELECT i.id FROM inscripciones i JOIN participantes p ON p.id = i.participante_id "
            "WHERE i.evento_id = ? AND i.estado = 'activa' AND p.correo = ? AND p.documento = ?",
            (evento_id, correo, documento)).fetchone()
        if not ins:  # misma respuesta si no existe o si los datos no coinciden
            raise ErrorApi(404, "INSCRIPCION_NO_ENCONTRADA", "No se encontró una inscripción activa con esos datos.")
        if tiempo.ahora() >= tiempo.de_texto(ev["inicio"]):
            raise ErrorApi(409, "EVENTO_YA_INICIADO", "Ya no se puede cancelar: el evento ya inició.")
        conn.execute("UPDATE inscripciones SET estado = 'cancelada', cancelada_en = ? WHERE id = ?",
                     (tiempo.a_texto(tiempo.ahora()), ins["id"]))
        return _respuesta_inscripcion(conn, ins["id"])


def consultar_inscripciones(correo: str, documento: str) -> list[dict]:
    with db.lectura() as conn:
        filas = conn.execute(
            "SELECT i.id, i.estado, e.id AS evento_id, e.titulo, e.inicio, e.fin, e.lugar, e.estado AS evento_estado "
            "FROM inscripciones i JOIN participantes p ON p.id = i.participante_id "
            "JOIN eventos e ON e.id = i.evento_id WHERE p.correo = ? AND p.documento = ? "
            "ORDER BY e.inicio DESC", (correo, documento)).fetchall()
    return [{"id": f["id"], "estado": f["estado"],
             "evento": {"id": f["evento_id"], "titulo": f["titulo"], "lugar": f["lugar"],
                        "inicio": tiempo.a_bogota_iso(f["inicio"]), "fin": tiempo.a_bogota_iso(f["fin"]),
                        "estado": f["evento_estado"]}} for f in filas]


def _estado_ventana(ev, ahora: datetime) -> dict:
    inicio, fin = tiempo.de_texto(ev["inicio"]), tiempo.de_texto(ev["fin"])
    registro = fin + timedelta(hours=config.VENTANA_REGISTRO_HORAS)
    correccion = fin + timedelta(hours=config.VENTANA_CORRECCION_HORAS)
    if ahora < inicio:
        estado = "no_abierta"
    elif ahora <= registro:
        estado = "abierta"
    elif ahora <= correccion:
        estado = "solo_correccion"
    else:
        estado = "cerrada"
    return {"estado": estado, "abre": tiempo.a_bogota_iso(tiempo.a_texto(inicio)),
            "registro_hasta": tiempo.a_bogota_iso(tiempo.a_texto(registro)),
            "correccion_hasta": tiempo.a_bogota_iso(tiempo.a_texto(correccion))}


def listar_inscritos(usuario: dict, evento_id: int, estado: str | None) -> dict:
    actualizar_estados()
    with db.lectura() as conn:
        ev = _fila_evento(conn, evento_id)
        _exigir_gestion(usuario, ev)
        sql = ("SELECT i.id, i.estado, i.en_el_momento, i.creada_en, p.nombre_completo, p.correo, p.documento, "
               "p.rol, p.programa, COALESCE(a.estado, 'ausente') AS asistencia, a.registrado_en "
               "FROM inscripciones i JOIN participantes p ON p.id = i.participante_id "
               "LEFT JOIN asistencias a ON a.inscripcion_id = i.id WHERE i.evento_id = ?")
        params: list = [evento_id]
        if estado:
            sql += " AND i.estado = ?"; params.append(estado)
        filas = conn.execute(sql + " ORDER BY p.nombre_completo", params).fetchall()
    return {"evento": a_evento(ev), "ventana_asistencia": _estado_ventana(ev, tiempo.ahora()),
            "inscripciones": [{"id": f["id"], "estado": f["estado"], "en_el_momento": bool(f["en_el_momento"]),
                               "asistencia": f["asistencia"],
                               "asistencia_registrada_en": tiempo.a_bogota_iso(f["registrado_en"]) if f["registrado_en"] else None,
                               "participante": {"nombre_completo": f["nombre_completo"], "correo": f["correo"],
                                                "documento": f["documento"], "rol": f["rol"], "programa": f["programa"]}}
                              for f in filas]}


def cancelar_inscripcion_personal(usuario: dict, inscripcion_id: int) -> dict:
    with db.transaccion() as conn:
        ins = conn.execute("SELECT id, evento_id, estado FROM inscripciones WHERE id = ?", (inscripcion_id,)).fetchone()
        if not ins:
            raise ErrorApi(404, "INSCRIPCION_NO_ENCONTRADA", "La inscripción no existe.")
        _exigir_gestion(usuario, _fila_evento(conn, ins["evento_id"]))
        if ins["estado"] != "activa":
            raise ErrorApi(409, "INSCRIPCION_NO_ACTIVA", "La inscripción ya no está activa.")
        if conn.execute("SELECT 1 FROM asistencias WHERE inscripcion_id = ? AND estado = 'presente'",
                        (inscripcion_id,)).fetchone():
            raise ErrorApi(409, "INSCRIPCION_CON_ASISTENCIA", "No se puede cancelar: ya tiene asistencia registrada.")
        conn.execute("UPDATE inscripciones SET estado = 'cancelada', cancelada_en = ? WHERE id = ?",
                     (tiempo.a_texto(tiempo.ahora()), inscripcion_id))
        return _respuesta_inscripcion(conn, inscripcion_id)


def _guardar_asistencia(conn, usuario_id: int, inscripcion_id: int, estado: str) -> dict:
    ahora = tiempo.a_texto(tiempo.ahora())
    if conn.execute("SELECT 1 FROM asistencias WHERE inscripcion_id = ?", (inscripcion_id,)).fetchone():
        conn.execute("UPDATE asistencias SET estado = ?, registrado_por = ?, registrado_en = ? "
                     "WHERE inscripcion_id = ?", (estado, usuario_id, ahora, inscripcion_id))
    else:
        conn.execute("INSERT INTO asistencias (inscripcion_id, estado, registrado_por, registrado_en) "
                     "VALUES (?, ?, ?, ?)", (inscripcion_id, estado, usuario_id, ahora))
    return {"inscripcion_id": inscripcion_id, "estado": estado, "registrado_por": usuario_id,
            "registrado_en": tiempo.a_bogota_iso(ahora)}


def _aplicar_asistencia(conn, ev, usuario: dict, inscripcion_id: int, estado: str) -> dict:
    ins = conn.execute("SELECT id, estado FROM inscripciones WHERE id = ? AND evento_id = ?",
                       (inscripcion_id, ev["id"])).fetchone()
    if not ins:
        raise ErrorApi(404, "INSCRIPCION_NO_ENCONTRADA", "La inscripción no existe en este evento.",
                       [{"campo": "inscripcion_id", "mensaje": str(inscripcion_id)}])
    if ins["estado"] != "activa":
        raise ErrorApi(422, "PARTICIPANTE_NO_INSCRITO", "El participante no tiene una inscripción activa.",
                       [{"campo": "inscripcion_id", "mensaje": str(inscripcion_id)}])
    existente = conn.execute("SELECT 1 FROM asistencias WHERE inscripcion_id = ?", (inscripcion_id,)).fetchone()
    ahora = tiempo.ahora()
    inicio, fin = tiempo.de_texto(ev["inicio"]), tiempo.de_texto(ev["fin"])
    if ahora < inicio:
        raise ErrorApi(422, "VENTANA_ASISTENCIA_NO_ABIERTA", "La asistencia se puede registrar desde el inicio del evento.")
    horas = config.VENTANA_CORRECCION_HORAS if existente else config.VENTANA_REGISTRO_HORAS
    if ahora > fin + timedelta(hours=horas):
        raise ErrorApi(422, "VENTANA_ASISTENCIA_CERRADA",
                       "El plazo para modificar la asistencia de este evento terminó." if existente
                       else "El plazo para registrar la asistencia de este evento terminó.")
    return _guardar_asistencia(conn, usuario["id"], inscripcion_id, estado)


def _evento_para_asistencia(conn, usuario: dict, evento_id: int):
    finalizar_vencidos(conn)
    ev = _fila_evento(conn, evento_id)
    _exigir_gestion(usuario, ev)
    if ev["estado"] not in ("publicado", "finalizado"):
        raise ErrorApi(409, "EVENTO_NO_ABIERTO", "Solo se registra asistencia en eventos publicados o finalizados.")
    return ev


def registrar_asistencia(usuario: dict, evento_id: int, inscripcion_id: int, estado: str) -> dict:
    with db.transaccion() as conn:
        ev = _evento_para_asistencia(conn, usuario, evento_id)
        return _aplicar_asistencia(conn, ev, usuario, inscripcion_id, estado)


def registrar_asistencia_lote(usuario: dict, evento_id: int, ids: list[int], estado: str) -> dict:
    with db.transaccion() as conn:  # todo o nada
        ev = _evento_para_asistencia(conn, usuario, evento_id)
        for inscripcion_id in ids:
            _aplicar_asistencia(conn, ev, usuario, inscripcion_id, estado)
        return {"actualizadas": len(ids), "estado": estado}


def inscribir_en_el_momento(usuario: dict, evento_id: int, d: ParticipanteIn) -> dict:
    with db.transaccion() as conn:
        finalizar_vencidos(conn)
        ev = _fila_evento(conn, evento_id)
        _exigir_gestion(usuario, ev)
        if ev["estado"] != "publicado":
            raise ErrorApi(409, "EVENTO_NO_ABIERTO", "Solo se puede inscribir en el momento en un evento publicado.")
        ahora = tiempo.ahora()
        if not tiempo.de_texto(ev["inicio"]) <= ahora < tiempo.de_texto(ev["fin"]):
            raise ErrorApi(409, "EVENTO_NO_EN_CURSO", "Solo se puede inscribir en el momento mientras el evento está en curso.")
        participante_id = _asegurar_participante(conn, d)
        inscripcion_id = _crear_inscripcion(conn, ev, participante_id, True)
        _guardar_asistencia(conn, usuario["id"], inscripcion_id, "presente")
        return _respuesta_inscripcion(conn, inscripcion_id)


# ------------------------------------------------------------------ consolidado
def consolidado(desde: datetime | None, hasta: datetime | None, tipo: str | None,
                estado: str | None, organizador_id: int | None) -> dict:
    actualizar_estados()
    sql = ("SELECT e.id, e.titulo, e.tipo, e.inicio, e.fin, e.estado, e.cupo, u.id AS organizador_id, "
           "u.nombre AS organizador, "
           "COALESCE(SUM(CASE WHEN i.estado = 'activa' THEN 1 ELSE 0 END), 0) AS inscritos, "
           "COALESCE(SUM(CASE WHEN i.estado = 'activa' AND a.estado = 'presente' THEN 1 ELSE 0 END), 0) AS asistentes "
           "FROM eventos e JOIN usuarios u ON u.id = e.organizador_id "
           "LEFT JOIN inscripciones i ON i.evento_id = e.id "
           "LEFT JOIN asistencias a ON a.inscripcion_id = i.id WHERE 1 = 1")
    params: list = []
    for condicion, valor in (("e.inicio >= ?", desde and tiempo.a_texto(desde)),
                             ("e.inicio <= ?", hasta and tiempo.a_texto(hasta)),
                             ("e.tipo = ?", tipo), ("e.estado = ?", estado),
                             ("e.organizador_id = ?", organizador_id)):
        if valor is not None:
            sql += f" AND {condicion}"; params.append(valor)
    with db.lectura() as conn:
        filas = conn.execute(sql + " GROUP BY e.id ORDER BY e.inicio, e.id", params).fetchall()

    ahora = tiempo.a_texto(tiempo.ahora())
    eventos, por_estado = [], {"borrador": 0, "publicado": 0, "cancelado": 0, "finalizado": 0}
    tot_insc = tot_asist = fin_insc = fin_asist = 0
    for f in filas:
        por_estado[f["estado"]] += 1
        tot_insc += f["inscritos"]; tot_asist += f["asistentes"]
        if f["estado"] == "finalizado":
            fin_insc += f["inscritos"]; fin_asist += f["asistentes"]
        iniciado = f["inicio"] <= ahora and f["estado"] in ("publicado", "finalizado")
        eventos.append({
            "id": f["id"], "titulo": f["titulo"], "tipo": f["tipo"], "estado": f["estado"],
            "inicio": tiempo.a_bogota_iso(f["inicio"]), "fin": tiempo.a_bogota_iso(f["fin"]),
            "organizador": {"id": f["organizador_id"], "nombre": f["organizador"]},
            "cupo": f["cupo"], "inscritos_activos": f["inscritos"],
            "cupos_disponibles": max(f["cupo"] - f["inscritos"], 0), "asistentes": f["asistentes"],
            "porcentaje_asistencia": round(f["asistentes"] * 100 / f["inscritos"], 1)
            if iniciado and f["inscritos"] else None})
    return {"totales": {"eventos": len(eventos), "por_estado": por_estado, "inscripciones_activas": tot_insc,
                        "asistentes": tot_asist,
                        "porcentaje_asistencia_finalizados": round(fin_asist * 100 / fin_insc, 1) if fin_insc else None},
            "eventos": eventos}
