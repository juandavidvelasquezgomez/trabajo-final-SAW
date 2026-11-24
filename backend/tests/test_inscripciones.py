"""Inscripción, cupos, duplicados, cruces de horario y cancelación (CA-03, CA-04)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from app import db, reglas, tiempo
from app.errores import ErrorApi
from app.schemas import ParticipanteIn
from ayudas import (codigo, crear_evento, evento_en, evento_publicado, inscribir, instante, iso, payload_participante,
                    publicar)


def contar(tabla, donde="1 = 1"):
    with db.lectura() as conn:
        return conn.execute(f"SELECT count(*) FROM {tabla} WHERE {donde}").fetchone()[0]


# ---------------------------------------------------------------- casos válidos
def test_inscripcion_valida_se_guarda_y_se_puede_consultar(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    r = inscribir(cliente, ev["id"], 1)
    assert r.status_code == 201
    d = r.json()
    assert d["estado"] == "activa" and d["cupos_disponibles"] == 29 and d["participante"]["correo"] == "persona1@ejemplo.test"
    p = payload_participante(1)
    lista = cliente.get("/api/inscripciones", params={"correo": p["correo"], "documento": p["documento"]}).json()
    assert len(lista) == 1 and lista[0]["evento"]["id"] == ev["id"] and lista[0]["estado"] == "activa"
    assert cliente.get(f"/api/eventos/{ev['id']}").json()["cupos_disponibles"] == 29       # CA-02 coherente


def test_los_datos_del_participante_se_normalizan_al_guardar(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    r = inscribir(cliente, ev["id"], 1, correo="  LAURA.Gomez@Ejemplo.TEST ", documento="1.000.000.001",
                  nombre_completo="  Laura   Gómez ")
    assert r.status_code == 201
    with db.lectura() as conn:
        f = conn.execute("SELECT * FROM participantes").fetchone()
    assert (f["correo"], f["documento"], f["nombre_completo"]) == ("laura.gomez@ejemplo.test", "1000000001", "Laura Gómez")


def test_un_participante_se_guarda_una_sola_vez_aunque_se_inscriba_en_varios_eventos(cliente, org):
    a = evento_publicado(cliente, org["headers"], titulo="Evento A uno")
    b = evento_en(cliente, org["headers"], desde=timedelta(days=5), titulo="Evento B dos")
    assert inscribir(cliente, a["id"], 1).status_code == 201 and inscribir(cliente, b["id"], 1).status_code == 201
    assert contar("participantes") == 1 and contar("inscripciones") == 2


# -------------------------------------------------------------- datos inválidos
def test_inscripcion_con_datos_invalidos_se_rechaza_sin_guardar_nada(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    for cambios in ({"correo": "nope"}, {"documento": "12"}, {"nombre_completo": "A"}, {"rol": "admin"}, {"programa": "x"},
                    {"correo": None}, {"documento": 123456789}, {"cupo": 5}):
        r = inscribir(cliente, ev["id"], 1, **cambios)
        assert r.status_code == 422 and codigo(r) == "DATOS_INVALIDOS"
    assert cliente.post(f"/api/eventos/{ev['id']}/inscripciones", json={}).status_code == 422
    assert contar("participantes") == 0 and contar("inscripciones") == 0


# ------------------------------------------------------------------------ cupo
def test_cupo_agotado_se_rechaza_y_el_cupo_se_conserva(cliente, org):
    ev = evento_publicado(cliente, org["headers"], cupo=2)
    assert inscribir(cliente, ev["id"], 1).status_code == 201 and inscribir(cliente, ev["id"], 2).status_code == 201
    r = inscribir(cliente, ev["id"], 3)
    assert r.status_code == 409 and codigo(r) == "CUPO_AGOTADO"
    assert contar("inscripciones") == 2
    assert contar("participantes") == 2                                    # tampoco se creó el participante (rollback)
    assert cliente.get(f"/api/eventos/{ev['id']}").json()["cupos_disponibles"] == 0


def test_cancelar_libera_el_cupo(cliente, org):
    ev = evento_publicado(cliente, org["headers"], cupo=1)
    inscribir(cliente, ev["id"], 1)
    assert codigo(inscribir(cliente, ev["id"], 2)) == "CUPO_AGOTADO"
    p = payload_participante(1)
    r = cliente.post(f"/api/eventos/{ev['id']}/inscripciones/cancelar", json={"correo": p["correo"], "documento": p["documento"]})
    assert r.status_code == 200 and r.json()["estado"] == "cancelada" and r.json()["cupos_disponibles"] == 1
    assert inscribir(cliente, ev["id"], 2).status_code == 201


def test_concurrencia_nunca_supera_el_cupo(cliente, org):
    ev = evento_publicado(cliente, org["headers"], cupo=5)

    def intentar(n):
        try:
            reglas.inscribir(ev["id"], ParticipanteIn(**payload_participante(n)))
            return "ok"
        except ErrorApi as e:
            return e.codigo

    with ThreadPoolExecutor(max_workers=10) as pool:
        resultados = list(pool.map(intentar, range(1, 26)))
    assert resultados.count("ok") == 5 and resultados.count("CUPO_AGOTADO") == 20
    assert contar("inscripciones", "estado = 'activa'") == 5
    assert contar("participantes") == 5                                    # los rechazados no dejaron rastro


def test_concurrencia_no_crea_inscripciones_duplicadas(cliente, org):
    ev = evento_publicado(cliente, org["headers"])

    def intentar(_):
        try:
            reglas.inscribir(ev["id"], ParticipanteIn(**payload_participante(1)))
            return "ok"
        except ErrorApi as e:
            return e.codigo

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(intentar, range(12)))
    assert resultados.count("ok") == 1 and resultados.count("INSCRIPCION_DUPLICADA") == 11
    assert contar("inscripciones") == 1 and contar("participantes") == 1


# ------------------------------------------------------------------ duplicados
def test_inscripcion_duplicada_se_rechaza(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    assert inscribir(cliente, ev["id"], 1).status_code == 201
    r = inscribir(cliente, ev["id"], 1)
    assert r.status_code == 409 and codigo(r) == "INSCRIPCION_DUPLICADA"
    assert contar("inscripciones") == 1


def test_la_normalizacion_evita_duplicados_disfrazados(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    assert inscribir(cliente, ev["id"], 1).status_code == 201
    for variante in ({"correo": "PERSONA1@Ejemplo.TEST"}, {"correo": "  persona1@ejemplo.test  "},
                     {"documento": "1.000.000.001"}, {"documento": " 1000000001 "},
                     {"nombre_completo": "Otro Nombre Distinto"}):
        r = inscribir(cliente, ev["id"], 1, **variante)
        assert r.status_code == 409 and codigo(r) == "INSCRIPCION_DUPLICADA", variante
    assert contar("inscripciones") == 1 and contar("participantes") == 1


def test_correo_o_documento_con_datos_distintos_se_rechazan_como_conflicto(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    r = inscribir(cliente, ev["id"], 2, correo="persona1@ejemplo.test")            # mismo correo, otro documento
    assert r.status_code == 409 and codigo(r) == "DATOS_PARTICIPANTE_EN_CONFLICTO"
    r = inscribir(cliente, ev["id"], 2, documento="1000000001")                    # mismo documento, otro correo
    assert r.status_code == 409 and codigo(r) == "DATOS_PARTICIPANTE_EN_CONFLICTO"
    assert contar("participantes") == 1 and contar("inscripciones") == 1


def test_se_puede_volver_a_inscribir_tras_cancelar(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    p = payload_participante(1)
    cliente.post(f"/api/eventos/{ev['id']}/inscripciones/cancelar", json={"correo": p["correo"], "documento": p["documento"]})
    assert inscribir(cliente, ev["id"], 1).status_code == 201
    assert contar("inscripciones", "estado = 'activa'") == 1 and contar("inscripciones") == 2


# ------------------------------------------------------------ cruce de horarios
def test_cruce_de_horarios(cliente, org):
    base = timedelta(days=2)
    a = evento_en(cliente, org["headers"], desde=base, horas=3, titulo="Evento A 14 a 17")
    b = evento_en(cliente, org["headers"], desde=base + timedelta(hours=2), horas=3, titulo="Evento B se cruza")
    c = evento_en(cliente, org["headers"], desde=base + timedelta(hours=3), horas=2, titulo="Evento C contiguo")
    d = evento_en(cliente, org["headers"], desde=base + timedelta(days=1), horas=2, titulo="Evento D otro dia")
    assert inscribir(cliente, a["id"], 1).status_code == 201
    r = inscribir(cliente, b["id"], 1)
    assert r.status_code == 409 and codigo(r) == "CRUCE_DE_HORARIO" and "Evento A 14 a 17" in r.json()["error"]["mensaje"]
    assert inscribir(cliente, c["id"], 1).status_code == 201                       # termina justo cuando empieza otro: sin conflicto
    assert inscribir(cliente, d["id"], 1).status_code == 201
    assert inscribir(cliente, b["id"], 2).status_code == 201                       # otra persona sí puede
    assert contar("inscripciones", "participante_id = 1") == 3


def test_cancelar_una_inscripcion_elimina_el_cruce(cliente, org):
    a = evento_en(cliente, org["headers"], titulo="Evento A cruce")
    b = evento_en(cliente, org["headers"], desde=timedelta(days=2, hours=1), titulo="Evento B cruce")
    inscribir(cliente, a["id"], 1)
    assert codigo(inscribir(cliente, b["id"], 1)) == "CRUCE_DE_HORARIO"
    p = payload_participante(1)
    cliente.post(f"/api/eventos/{a['id']}/inscripciones/cancelar", json={"correo": p["correo"], "documento": p["documento"]})
    assert inscribir(cliente, b["id"], 1).status_code == 201


# ---------------------------------------------------- estado y momento del evento
def test_solo_se_inscribe_en_eventos_publicados_que_no_han_iniciado(cliente, org, reloj):
    borrador = crear_evento(cliente, org["headers"], titulo="Evento borrador")
    assert inscribir(cliente, borrador["id"], 1).status_code == 404
    cancelado = evento_publicado(cliente, org["headers"], titulo="Evento cancelado")
    cliente.patch(f"/api/eventos/{cancelado['id']}/estado", json={"estado": "cancelado"}, headers=org["headers"])
    r = inscribir(cliente, cancelado["id"], 1)
    assert r.status_code == 409 and codigo(r) == "EVENTO_NO_ABIERTO"
    en_curso = evento_publicado(cliente, org["headers"], titulo="Evento en curso", inicio=iso(tiempo.ahora() + timedelta(hours=1)),
                                fin=iso(tiempo.ahora() + timedelta(hours=3)))
    reloj.fijar(instante(en_curso["inicio"]) + timedelta(minutes=1))
    r = inscribir(cliente, en_curso["id"], 1)
    assert r.status_code == 409 and codigo(r) == "EVENTO_YA_INICIADO"
    assert inscribir(cliente, 99999, 1).status_code == 404
    assert contar("inscripciones") == 0 and contar("participantes") == 0


def test_inscripcion_hasta_el_ultimo_segundo_antes_del_inicio(cliente, org, reloj):
    ev = evento_publicado(cliente, org["headers"])
    reloj.fijar(instante(ev["inicio"]) - timedelta(seconds=1))
    assert inscribir(cliente, ev["id"], 1).status_code == 201
    reloj.avanzar(seconds=1)
    assert codigo(inscribir(cliente, ev["id"], 2)) == "EVENTO_YA_INICIADO"


# ------------------------------------------------------------------ cancelación
def test_cancelacion_exige_correo_y_documento_coincidentes(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    inscribir(cliente, ev["id"], 2)
    url, p = f"/api/eventos/{ev['id']}/inscripciones/cancelar", payload_participante(1)
    for cuerpo in ({"correo": p["correo"], "documento": "9999999999"},                       # documento ajeno
                   {"correo": "persona2@ejemplo.test", "documento": p["documento"]},         # mezcla de dos personas
                   {"correo": "nadie@ejemplo.test", "documento": p["documento"]}):
        r = cliente.post(url, json=cuerpo)
        assert r.status_code == 404 and codigo(r) == "INSCRIPCION_NO_ENCONTRADA"
    assert cliente.post(url, json={"correo": "nope", "documento": p["documento"]}).status_code == 422
    assert cliente.post(url, json={}).status_code == 422
    assert contar("inscripciones", "estado = 'activa'") == 2
    assert cliente.post(url, json={"correo": p["correo"], "documento": "1.000.000.001"}).status_code == 200
    assert cliente.post(url, json={"correo": p["correo"], "documento": p["documento"]}).status_code == 404   # ya cancelada


def test_no_se_cancela_una_vez_iniciado_el_evento(cliente, org, reloj):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    reloj.fijar(instante(ev["inicio"]) + timedelta(minutes=1))
    p = payload_participante(1)
    r = cliente.post(f"/api/eventos/{ev['id']}/inscripciones/cancelar", json={"correo": p["correo"], "documento": p["documento"]})
    assert r.status_code == 409 and codigo(r) == "EVENTO_YA_INICIADO"


def test_consulta_de_inscripciones_exige_ambos_datos_y_no_revela_mas(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    p = payload_participante(1)
    assert cliente.get("/api/inscripciones").status_code == 422
    assert cliente.get("/api/inscripciones", params={"correo": p["correo"]}).status_code == 422
    assert cliente.get("/api/inscripciones", params={"correo": "nope", "documento": p["documento"]}).status_code == 422
    assert cliente.get("/api/inscripciones", params={"correo": p["correo"], "documento": "9999999999"}).json() == []
    assert cliente.get("/api/inscripciones", params={"correo": "otro@ejemplo.test", "documento": p["documento"]}).json() == []


# --------------------------------------------------------- vista del personal
def test_lista_de_inscritos_solo_para_el_personal_autorizado(cliente, org, org2, coord):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    url = f"/api/eventos/{ev['id']}/inscripciones"
    assert cliente.get(url).status_code == 401
    assert cliente.get(url, headers=org2["headers"]).status_code == 403
    for h in (org["headers"], coord["headers"]):
        d = cliente.get(url, headers=h).json()
        assert len(d["inscripciones"]) == 1 and d["inscripciones"][0]["asistencia"] == "ausente"
        assert d["ventana_asistencia"]["estado"] == "no_abierta" and d["evento"]["id"] == ev["id"]
    assert cliente.get(url, headers=org["headers"], params={"estado": "cancelada"}).json()["inscripciones"] == []
    assert cliente.get(url, headers=org["headers"], params={"estado": "otra"}).status_code == 422


def test_el_personal_puede_cancelar_una_inscripcion(cliente, org, org2, coord):
    ev = evento_publicado(cliente, org["headers"], cupo=1)
    ins = inscribir(cliente, ev["id"], 1).json()
    url = f"/api/inscripciones/{ins['id']}"
    assert cliente.patch(url, json={"estado": "cancelada"}).status_code == 401
    assert cliente.patch(url, json={"estado": "cancelada"}, headers=org2["headers"]).status_code == 403
    assert cliente.patch(url, json={"estado": "activa"}, headers=org["headers"]).status_code == 422
    r = cliente.patch(url, json={"estado": "cancelada"}, headers=org["headers"])
    assert r.status_code == 200 and r.json()["cupos_disponibles"] == 1
    r = cliente.patch(url, json={"estado": "cancelada"}, headers=coord["headers"])
    assert r.status_code == 409 and codigo(r) == "INSCRIPCION_NO_ACTIVA"
    assert cliente.patch("/api/inscripciones/99999", json={"estado": "cancelada"}, headers=org["headers"]).status_code == 404
