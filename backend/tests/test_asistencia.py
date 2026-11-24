"""Registro y corrección de asistencia, ventanas de tiempo e inscripción en el momento (CA-05)."""
from datetime import timedelta

from app import db
from ayudas import codigo, crear_evento, evento_en, evento_publicado, inscribir, instante, payload_participante


def escenario(cliente, org, inscritos=3, **cambios):
    """Evento publicado con `inscritos` personas inscritas. Devuelve (evento, [ids de inscripción])."""
    ev = evento_publicado(cliente, org["headers"], **cambios)
    ids = [inscribir(cliente, ev["id"], n).json()["id"] for n in range(1, inscritos + 1)]
    return ev, ids


def marcar(cliente, headers, ev, ins, estado="presente"):
    return cliente.put(f"/api/eventos/{ev['id']}/asistencia/{ins}", json={"estado": estado}, headers=headers)


def lista(cliente, headers, ev):
    return {i["id"]: i for i in cliente.get(f"/api/eventos/{ev['id']}/inscripciones", headers=headers).json()["inscripciones"]}


def abrir(reloj, ev, minutos=10):
    reloj.fijar(instante(ev["inicio"]) + timedelta(minutes=minutos))


# ------------------------------------------------------------- registro básico
def test_registrar_asistencia_la_asocia_al_evento_y_al_participante(cliente, org, reloj):
    ev, (a, b, c) = escenario(cliente, org)
    abrir(reloj, ev)
    r = marcar(cliente, org["headers"], ev, a)
    assert r.status_code == 200 and r.json()["estado"] == "presente" and r.json()["registrado_por"] == org["id"]
    filas = lista(cliente, org["headers"], ev)
    assert filas[a]["asistencia"] == "presente" and filas[a]["asistencia_registrada_en"]
    assert filas[b]["asistencia"] == filas[c]["asistencia"] == "ausente"            # por defecto
    with db.lectura() as conn:
        fila = conn.execute("SELECT i.evento_id, p.correo FROM asistencias a JOIN inscripciones i ON i.id = a.inscripcion_id "
                            "JOIN participantes p ON p.id = i.participante_id").fetchone()
    assert (fila["evento_id"], fila["correo"]) == (ev["id"], "persona1@ejemplo.test")


def test_la_coordinacion_tambien_registra_asistencia(cliente, org, coord, reloj):
    ev, (a, *_) = escenario(cliente, org)
    abrir(reloj, ev)
    r = marcar(cliente, coord["headers"], ev, a)
    assert r.status_code == 200 and r.json()["registrado_por"] == coord["id"]


def test_permisos_de_asistencia(cliente, org, org2, reloj):
    ev, (a, *_) = escenario(cliente, org)
    abrir(reloj, ev)
    assert marcar(cliente, {}, ev, a).status_code == 401
    r = marcar(cliente, org2["headers"], ev, a)
    assert r.status_code == 403 and codigo(r) == "SIN_PERMISO"
    assert cliente.post(f"/api/eventos/{ev['id']}/asistencia/lote", json={"inscripcion_ids": [a]}, headers=org2["headers"]).status_code == 403
    assert cliente.post(f"/api/eventos/{ev['id']}/asistencia/lote", json={"inscripcion_ids": [a]}).status_code == 401
    assert lista(cliente, org["headers"], ev)[a]["asistencia"] == "ausente"          # nada cambió


def test_datos_invalidos_en_asistencia(cliente, org, reloj):
    ev, (a, *_) = escenario(cliente, org)
    abrir(reloj, ev)
    for cuerpo in ({"estado": "tarde"}, {"estado": ""}, {}, {"estado": None}, {"estado": "presente", "extra": 1}):
        assert cliente.put(f"/api/eventos/{ev['id']}/asistencia/{a}", json=cuerpo, headers=org["headers"]).status_code == 422
    assert cliente.put(f"/api/eventos/{ev['id']}/asistencia/0", json={"estado": "presente"}, headers=org["headers"]).status_code == 422


def test_inscripciones_que_no_corresponden(cliente, org, reloj):
    ev, (a, *_) = escenario(cliente, org)
    otro = evento_en(cliente, org["headers"], desde=timedelta(days=5), titulo="Otro evento aparte")
    x = inscribir(cliente, otro["id"], 1).json()["id"]
    abrir(reloj, ev)
    r = marcar(cliente, org["headers"], ev, x)                                       # inscripción de otro evento
    assert r.status_code == 404 and codigo(r) == "INSCRIPCION_NO_ENCONTRADA"
    assert marcar(cliente, org["headers"], ev, 99999).status_code == 404
    p = payload_participante(1)
    cliente.patch(f"/api/inscripciones/{a}", json={"estado": "cancelada"}, headers=org["headers"])
    r = marcar(cliente, org["headers"], ev, a)                                       # inscripción cancelada
    assert r.status_code == 422 and codigo(r) == "PARTICIPANTE_NO_INSCRITO"
    assert cliente.put("/api/eventos/99999/asistencia/1", json={"estado": "presente"}, headers=org["headers"]).status_code == 404


def test_solo_en_eventos_publicados_o_finalizados(cliente, org, reloj):
    borrador = crear_evento(cliente, org["headers"], titulo="Evento en borrador")
    abrir(reloj, borrador)
    assert marcar(cliente, org["headers"], borrador, 1).status_code in (404, 409)
    ev, (a, *_) = escenario(cliente, org, titulo="Evento a cancelar")
    cliente.patch(f"/api/eventos/{ev['id']}/estado", json={"estado": "cancelado"}, headers=org["headers"])
    r = marcar(cliente, org["headers"], ev, a)
    assert r.status_code == 409 and codigo(r) == "EVENTO_NO_ABIERTO"


# ------------------------------------------------------------------- ventanas
def test_no_se_registra_antes_del_inicio(cliente, org, reloj):
    ev, (a, *_) = escenario(cliente, org)
    reloj.fijar(instante(ev["inicio"]) - timedelta(seconds=1))
    r = marcar(cliente, org["headers"], ev, a)
    assert r.status_code == 422 and codigo(r) == "VENTANA_ASISTENCIA_NO_ABIERTA"
    reloj.avanzar(seconds=1)
    assert marcar(cliente, org["headers"], ev, a).status_code == 200


def test_el_primer_registro_cierra_2_horas_despues_del_fin(cliente, org, reloj):
    ev, (a, b, c) = escenario(cliente, org)
    reloj.fijar(instante(ev["fin"]) + timedelta(hours=2))                            # justo en el límite
    assert marcar(cliente, org["headers"], ev, a).status_code == 200                 # el evento ya está 'finalizado'
    reloj.avanzar(seconds=1)
    r = marcar(cliente, org["headers"], ev, b)
    assert r.status_code == 422 and codigo(r) == "VENTANA_ASISTENCIA_CERRADA"


def test_la_correccion_se_permite_hasta_24_horas_despues_del_fin(cliente, org, reloj):
    ev, (a, b, c) = escenario(cliente, org)
    abrir(reloj, ev)
    marcar(cliente, org["headers"], ev, a, "presente")
    reloj.fijar(instante(ev["fin"]) + timedelta(hours=23, minutes=59))               # fuera de la ventana de registro
    assert marcar(cliente, org["headers"], ev, a, "ausente").status_code == 200      # pero aún se puede corregir
    assert lista(cliente, org["headers"], ev)[a]["asistencia"] == "ausente"
    r = marcar(cliente, org["headers"], ev, b)                                       # un registro NUEVO ya no
    assert codigo(r) == "VENTANA_ASISTENCIA_CERRADA"
    reloj.fijar(instante(ev["fin"]) + timedelta(hours=24, seconds=1))
    r = marcar(cliente, org["headers"], ev, a, "presente")
    assert r.status_code == 422 and codigo(r) == "VENTANA_ASISTENCIA_CERRADA"
    assert lista(cliente, org["headers"], ev)[a]["asistencia"] == "ausente"          # quedó cerrada


def test_marcar_dos_veces_actualiza_en_lugar_de_duplicar(cliente, org, reloj):
    ev, (a, *_) = escenario(cliente, org)
    abrir(reloj, ev)
    marcar(cliente, org["headers"], ev, a, "presente")
    marcar(cliente, org["headers"], ev, a, "ausente")
    marcar(cliente, org["headers"], ev, a, "presente")
    with db.lectura() as conn:
        assert conn.execute("SELECT count(*) FROM asistencias").fetchone()[0] == 1


def test_estado_de_la_ventana_en_la_lista(cliente, org, reloj):
    ev, _ = escenario(cliente, org)
    estado = lambda: cliente.get(f"/api/eventos/{ev['id']}/inscripciones", headers=org["headers"]).json()["ventana_asistencia"]["estado"]
    assert estado() == "no_abierta"
    abrir(reloj, ev); assert estado() == "abierta"
    reloj.fijar(instante(ev["fin"]) + timedelta(hours=3)); assert estado() == "solo_correccion"
    reloj.fijar(instante(ev["fin"]) + timedelta(hours=25)); assert estado() == "cerrada"


# ----------------------------------------------------------------------- lote
def test_registro_en_lote(cliente, org, reloj):
    ev, (a, b, c) = escenario(cliente, org)
    abrir(reloj, ev)
    r = cliente.post(f"/api/eventos/{ev['id']}/asistencia/lote", json={"inscripcion_ids": [a, b, c]}, headers=org["headers"])
    assert r.status_code == 200 and r.json()["actualizadas"] == 3
    assert {i["asistencia"] for i in lista(cliente, org["headers"], ev).values()} == {"presente"}
    cliente.post(f"/api/eventos/{ev['id']}/asistencia/lote", json={"inscripcion_ids": [a], "estado": "ausente"}, headers=org["headers"])
    assert lista(cliente, org["headers"], ev)[a]["asistencia"] == "ausente"


def test_el_lote_es_atomico_si_uno_falla_no_se_guarda_ninguno(cliente, org, reloj):
    ev, (a, b, c) = escenario(cliente, org)
    abrir(reloj, ev)
    r = cliente.post(f"/api/eventos/{ev['id']}/asistencia/lote", json={"inscripcion_ids": [a, b, 99999]}, headers=org["headers"])
    assert r.status_code == 404 and r.json()["error"]["detalles"][0]["mensaje"] == "99999"
    with db.lectura() as conn:
        assert conn.execute("SELECT count(*) FROM asistencias").fetchone()[0] == 0
    for cuerpo in ({"inscripcion_ids": []}, {"inscripcion_ids": [a, a]}, {"inscripcion_ids": ["x"]}, {}):
        assert cliente.post(f"/api/eventos/{ev['id']}/asistencia/lote", json=cuerpo, headers=org["headers"]).status_code == 422


def test_no_se_cancela_una_inscripcion_con_asistencia_presente(cliente, org, reloj):
    ev, (a, *_) = escenario(cliente, org)
    abrir(reloj, ev)
    marcar(cliente, org["headers"], ev, a)
    r = cliente.patch(f"/api/inscripciones/{a}", json={"estado": "cancelada"}, headers=org["headers"])
    assert r.status_code == 409 and codigo(r) == "INSCRIPCION_CON_ASISTENCIA"


# ------------------------------------------------------- inscripción en el momento
def en_el_momento(cliente, headers, ev, n=50, **cambios):
    return cliente.post(f"/api/eventos/{ev['id']}/inscripciones/en-el-momento",
                        json=payload_participante(n, **cambios), headers=headers)


def test_inscripcion_en_el_momento_inscribe_y_marca_presente(cliente, org, reloj):
    ev, _ = escenario(cliente, org, inscritos=1)
    abrir(reloj, ev)
    r = en_el_momento(cliente, org["headers"], ev)
    assert r.status_code == 201
    d = r.json()
    assert d["en_el_momento"] is True and d["cupos_disponibles"] == 28 and d["participante"]["correo"] == "persona50@ejemplo.test"
    fila = lista(cliente, org["headers"], ev)[d["id"]]
    assert fila["asistencia"] == "presente" and fila["en_el_momento"] is True


def db_cuenta(tabla):
    with db.lectura() as conn:
        return conn.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]


def test_en_el_momento_respeta_el_cupo(cliente, org, reloj):
    ev, _ = escenario(cliente, org, inscritos=2, cupo=2)
    abrir(reloj, ev)
    r = en_el_momento(cliente, org["headers"], ev)
    assert r.status_code == 409 and codigo(r) == "CUPO_AGOTADO"
    assert db_cuenta("participantes") == 2 and db_cuenta("inscripciones") == 2       # sin rastro del rechazado


def test_en_el_momento_respeta_el_cruce_de_horarios(cliente, org, reloj):
    ev, _ = escenario(cliente, org, inscritos=1)
    otro = evento_publicado(cliente, org["headers"], titulo="Evento que se cruza",
                            inicio=ev["inicio"], fin=ev["fin"])
    assert inscribir(cliente, otro["id"], 50).status_code == 201                      # la persona ya está en otro evento a la misma hora
    abrir(reloj, ev)
    r = en_el_momento(cliente, org["headers"], ev, n=50)
    assert r.status_code == 409 and codigo(r) == "CRUCE_DE_HORARIO"
    assert db_cuenta("inscripciones") == 2


def test_en_el_momento_rechaza_duplicados(cliente, org, reloj):
    ev, _ = escenario(cliente, org, inscritos=1)
    abrir(reloj, ev)
    r = en_el_momento(cliente, org["headers"], ev, n=1)                               # ya estaba inscrito
    assert r.status_code == 409 and codigo(r) == "INSCRIPCION_DUPLICADA"
    assert en_el_momento(cliente, org["headers"], ev, n=60, correo="persona1@ejemplo.test").status_code == 409


def test_en_el_momento_solo_mientras_el_evento_esta_en_curso(cliente, org, reloj):
    ev, _ = escenario(cliente, org, inscritos=1)
    r = en_el_momento(cliente, org["headers"], ev)                                    # aún no empieza
    assert r.status_code == 409 and codigo(r) == "EVENTO_NO_EN_CURSO"
    reloj.fijar(instante(ev["fin"]) + timedelta(minutes=1))                          # ya terminó (queda finalizado)
    assert en_el_momento(cliente, org["headers"], ev).status_code == 409
    borrador = crear_evento(cliente, org["headers"], titulo="Evento borrador dos")
    assert en_el_momento(cliente, org["headers"], borrador).status_code == 409


def test_en_el_momento_exige_permisos_y_datos_validos(cliente, org, org2, coord, reloj):
    ev, _ = escenario(cliente, org, inscritos=1)
    abrir(reloj, ev)
    assert en_el_momento(cliente, {}, ev).status_code == 401
    assert en_el_momento(cliente, org2["headers"], ev).status_code == 403
    assert en_el_momento(cliente, org["headers"], ev, correo="nope").status_code == 422
    assert en_el_momento(cliente, coord["headers"], ev, n=70).status_code == 201
    assert db_cuenta("inscripciones") == 2
