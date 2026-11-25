"""Creación, publicación, edición, cancelación y consulta de eventos (CA-01, CA-02)."""
from datetime import timedelta

import pytest

from app import db, tiempo
from ayudas import (codigo, crear_evento, crear_usuario, evento_en, evento_publicado, inscribir, instante, iso,
                    login, payload_evento, payload_participante, publicar)


# ------------------------------------------------------------------ creación
def test_crear_evento_queda_en_borrador_con_datos_completos(cliente, org):
    r = cliente.post("/api/eventos", json=payload_evento(imagen_url="https://ejemplo.test/a.png"), headers=org["headers"])
    assert r.status_code == 201
    e = r.json()
    assert e["estado"] == "borrador" and e["cupo"] == 30 and e["cupos_disponibles"] == 30 and e["inscritos_activos"] == 0
    assert e["organizador"] == {"id": org["id"], "nombre": "Ana Torres"}
    assert e["inicio"].endswith("-05:00")                     # se muestra en hora de Colombia
    with db.lectura() as conn:
        assert conn.execute("SELECT count(*) FROM eventos").fetchone()[0] == 1


def test_crear_evento_requiere_sesion(cliente):
    r = cliente.post("/api/eventos", json=payload_evento())
    assert r.status_code == 401 and codigo(r) == "NO_AUTENTICADO"


def test_crear_evento_con_datos_invalidos_no_guarda_nada(cliente, org):
    for cambios in ({"titulo": ""}, {"cupo": 0}, {"cupo": "30"}, {"tipo": "fiesta"}, {"inicio": "mañana"},
                    {"estado": "publicado"}):
        assert cliente.post("/api/eventos", json=payload_evento(**cambios), headers=org["headers"]).status_code == 422
    with db.lectura() as conn:
        assert conn.execute("SELECT count(*) FROM eventos").fetchone()[0] == 0


def test_fechas_del_evento(cliente, org, reloj):
    ahora = tiempo.ahora()
    def crear(inicio, fin):
        return cliente.post("/api/eventos", json=payload_evento(inicio=iso(inicio), fin=iso(fin)), headers=org["headers"])
    r = crear(ahora - timedelta(hours=1), ahora + timedelta(hours=1))
    assert r.status_code == 422 and codigo(r) == "FECHA_EN_PASADO"
    r = crear(ahora, ahora + timedelta(hours=1))                          # empezar justo ahora tampoco
    assert r.status_code == 422 and codigo(r) == "FECHA_EN_PASADO"
    inicio = ahora + timedelta(days=1)
    for fin, cod in ((inicio, "FECHAS_INVALIDAS"), (inicio - timedelta(hours=1), "FECHAS_INVALIDAS"),
                     (inicio + timedelta(hours=8, seconds=1), "DURACION_EXCEDIDA")):
        r = crear(inicio, fin)
        assert r.status_code == 422 and codigo(r) == cod
    assert crear(inicio, inicio + timedelta(hours=8)).status_code == 201     # exactamente 8 horas: permitido


def test_no_se_puede_crear_dos_veces_el_mismo_evento(cliente, org):
    crear_evento(cliente, org["headers"])
    r = cliente.post("/api/eventos", json=payload_evento(titulo="  TALLER  de python "), headers=org["headers"])
    assert r.status_code == 409 and codigo(r) == "EVENTO_DUPLICADO"


def test_asignacion_de_organizador(cliente, org, org2, coord):
    r = cliente.post("/api/eventos", json=payload_evento(organizador_id=org2["id"]), headers=org["headers"])
    assert r.status_code == 403 and codigo(r) == "SIN_PERMISO"                       # un organizador no asigna a otro
    assert cliente.post("/api/eventos", json=payload_evento(organizador_id=org["id"]), headers=org["headers"]).status_code == 201
    r = cliente.post("/api/eventos", json=payload_evento(titulo="Evento de coordinación", organizador_id=org2["id"]),
                     headers=coord["headers"])
    assert r.status_code == 201 and r.json()["organizador"]["id"] == org2["id"]
    assert [e["titulo"] for e in cliente.get("/api/panel/eventos", headers=org2["headers"]).json()] == ["Evento de coordinación"]
    r = cliente.post("/api/eventos", json=payload_evento(titulo="Por defecto"), headers=coord["headers"])
    assert r.json()["organizador"]["id"] == coord["id"]                                # por defecto, ella misma
    for malo in (99999, ):
        r = cliente.post("/api/eventos", json=payload_evento(titulo="X evento", organizador_id=malo), headers=coord["headers"])
        assert r.status_code == 422 and codigo(r) == "ORGANIZADOR_INVALIDO"
    inactivo = crear_usuario("Inactivo Uno", "inactivo@ejemplo.test", "organizador", activo=0)
    r = cliente.post("/api/eventos", json=payload_evento(titulo="Y evento", organizador_id=inactivo), headers=coord["headers"])
    assert r.status_code == 422 and codigo(r) == "ORGANIZADOR_INVALIDO"


# ----------------------------------------------------- visibilidad y catálogo
def test_borrador_solo_lo_ven_su_organizador_y_la_coordinacion(cliente, org, org2, coord):
    ev = crear_evento(cliente, org["headers"])
    url = f"/api/eventos/{ev['id']}"
    assert cliente.get(url).status_code == 404                                       # anónimo
    assert cliente.get(url, headers=org2["headers"]).status_code == 404              # otro organizador
    assert cliente.get(url, headers=org["headers"]).status_code == 200
    assert cliente.get(url, headers=coord["headers"]).status_code == 200
    assert cliente.get("/api/eventos").json() == []                                   # no está en el catálogo


def test_publicar_hace_visible_el_evento_con_sus_cupos(cliente, org):
    ev = crear_evento(cliente, org["headers"])
    pub = publicar(cliente, org["headers"], ev["id"])
    assert pub["estado"] == "publicado"
    catalogo = cliente.get("/api/eventos").json()
    assert [e["id"] for e in catalogo] == [ev["id"]] and catalogo[0]["cupos_disponibles"] == 30
    assert cliente.get(f"/api/eventos/{ev['id']}").json()["titulo"] == "Taller de Python"


def test_catalogo_ordenado_y_con_filtros(cliente, org):
    tarde = evento_en(cliente, org["headers"], desde=timedelta(days=5), titulo="Seminario tarde", tipo="seminario")
    pronto = evento_en(cliente, org["headers"], desde=timedelta(days=2), titulo="Taller pronto", tipo="taller")
    assert [e["id"] for e in cliente.get("/api/eventos").json()] == [pronto["id"], tarde["id"]]
    assert [e["id"] for e in cliente.get("/api/eventos", params={"tipo": "seminario"}).json()] == [tarde["id"]]
    assert cliente.get("/api/eventos", params={"desde": "2026-12-04"}).json()[0]["id"] == tarde["id"]
    assert [e["id"] for e in cliente.get("/api/eventos", params={"desde": "2026-12-03", "hasta": "2026-12-03"}).json()] == [pronto["id"]]
    assert cliente.get("/api/eventos", params={"hasta": "2026-12-02"}).json() == []


def test_publicar_un_evento_que_ya_inicio_se_rechaza(cliente, org, reloj):
    ev = evento_en(cliente, org["headers"], publicado=False)
    reloj.fijar(instante(ev["inicio"]) + timedelta(minutes=1))
    r = cliente.patch(f"/api/eventos/{ev['id']}/estado", json={"estado": "publicado"}, headers=org["headers"])
    assert r.status_code == 422 and codigo(r) == "FECHA_EN_PASADO"


def test_transiciones_de_estado(cliente, org):
    ev = crear_evento(cliente, org["headers"])
    estado = lambda nuevo: cliente.patch(f"/api/eventos/{ev['id']}/estado", json={"estado": nuevo}, headers=org["headers"])
    assert estado("publicado").status_code == 200
    r = estado("publicado")
    assert r.status_code == 409 and codigo(r) == "TRANSICION_INVALIDA"
    assert estado("cancelado").status_code == 200
    for nuevo in ("cancelado", "publicado"):
        r = estado(nuevo)
        assert r.status_code == 409 and codigo(r) == "TRANSICION_INVALIDA"
    for invalido in ("finalizado", "borrador", "", None, 1):
        assert estado(invalido).status_code == 422                  # el cliente no puede fijar otros estados


def test_cancelar_evento_conserva_inscripciones_y_lo_saca_del_catalogo(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    assert inscribir(cliente, ev["id"], 1).status_code == 201 and inscribir(cliente, ev["id"], 2).status_code == 201
    r = cliente.patch(f"/api/eventos/{ev['id']}/estado", json={"estado": "cancelado"}, headers=org["headers"])
    assert r.status_code == 200 and r.json()["estado"] == "cancelado" and r.json()["inscritos_activos"] == 0
    assert cliente.get("/api/eventos").json() == []
    ins = cliente.get(f"/api/eventos/{ev['id']}/inscripciones", headers=org["headers"]).json()["inscripciones"]
    assert sorted(i["estado"] for i in ins) == ["cancelada_por_evento"] * 2          # se conservan, no se borran


def test_solo_el_dueno_o_la_coordinacion_cambian_el_estado(cliente, org, org2, coord):
    ev = crear_evento(cliente, org["headers"])
    url, cuerpo = f"/api/eventos/{ev['id']}/estado", {"estado": "publicado"}
    assert cliente.patch(url, json=cuerpo).status_code == 401
    assert cliente.patch(url, json=cuerpo, headers=org2["headers"]).status_code == 403
    assert cliente.patch(url, json=cuerpo, headers=coord["headers"]).status_code == 200


def test_el_evento_pasa_a_finalizado_automaticamente(cliente, org, reloj):
    ev = evento_publicado(cliente, org["headers"])
    reloj.fijar(instante(ev["fin"]) + timedelta(minutes=1))
    assert cliente.get(f"/api/eventos/{ev['id']}").status_code == 404                # ya no es público
    assert cliente.get("/api/panel/eventos", headers=org["headers"]).json()[0]["estado"] == "finalizado"
    assert cliente.get("/api/eventos").json() == []
    r = inscribir(cliente, ev["id"])
    assert r.status_code == 409 and codigo(r) == "EVENTO_NO_ABIERTO"


def test_el_detalle_y_el_catalogo_no_revelan_quienes_se_inscribieron(cliente, org, org2):
    """El público ve solo cifras. Los datos de los inscritos únicamente salen por la lista del personal."""
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1)
    p = payload_participante(1)
    for ruta, cabeceras in ((f"/api/eventos/{ev['id']}", {}), ("/api/eventos", {}),
                            (f"/api/eventos/{ev['id']}", org2["headers"]),       # otro organizador: tampoco
                            (f"/api/eventos/{ev['id']}", org["headers"])):       # ni siquiera el dueño, en el detalle
        texto = cliente.get(ruta, headers=cabeceras).text
        for dato in (p["correo"], p["documento"], p["nombre_completo"]):
            assert dato not in texto, f"{ruta} expone {dato}"
        assert "participante" not in texto
    assert cliente.get(f"/api/eventos/{ev['id']}")  .json()["inscritos_activos"] == 1       # sí las cifras
    assert cliente.get(f"/api/eventos/{ev['id']}/inscripciones").status_code == 401           # la lista exige sesión
    assert cliente.get(f"/api/eventos/{ev['id']}/inscripciones", headers=org2["headers"]).status_code == 403
    assert p["correo"] in cliente.get(f"/api/eventos/{ev['id']}/inscripciones", headers=org["headers"]).text


# ------------------------------------------------------------------- edición
def test_editar_evento(cliente, org, org2, coord):
    ev = evento_publicado(cliente, org["headers"])
    url = f"/api/eventos/{ev['id']}"
    r = cliente.put(url, json={"titulo": "Taller avanzado", "lugar": "Aula 2", "cupo": 40}, headers=org["headers"])
    assert r.status_code == 200 and r.json()["titulo"] == "Taller avanzado" and r.json()["cupo"] == 40
    assert cliente.put(url, json={"lugar": "X sitio"}, headers=org2["headers"]).status_code == 403
    assert cliente.put(url, json={"lugar": "Sala B"}, headers=coord["headers"]).json()["lugar"] == "Sala B"
    assert cliente.put(url, json={"lugar": "Sala C"}).status_code == 401
    assert cliente.put(url, json={}, headers=org["headers"]).status_code == 422
    assert cliente.put(url, json={"titulo": None}, headers=org["headers"]).status_code == 422
    assert cliente.put(url, json={"descripcion": None}, headers=org["headers"]).json()["descripcion"] is None
    assert cliente.put(url, json={"estado": "cancelado"}, headers=org["headers"]).status_code == 422   # no por esta vía
    assert cliente.put(f"/api/eventos/99999", json={"lugar": "Sala D"}, headers=org["headers"]).status_code == 404


def test_cupo_no_puede_ser_menor_que_los_inscritos(cliente, org):
    ev = evento_publicado(cliente, org["headers"])
    inscribir(cliente, ev["id"], 1); inscribir(cliente, ev["id"], 2)
    r = cliente.put(f"/api/eventos/{ev['id']}", json={"cupo": 1}, headers=org["headers"])
    assert r.status_code == 422 and codigo(r) == "CUPO_MENOR_A_INSCRITOS"
    assert cliente.put(f"/api/eventos/{ev['id']}", json={"cupo": 2}, headers=org["headers"]).json()["cupos_disponibles"] == 0


def test_cambio_de_fechas(cliente, org, reloj):
    ev = evento_publicado(cliente, org["headers"])
    url = f"/api/eventos/{ev['id']}"
    nuevo = tiempo.ahora() + timedelta(days=4)
    cuerpo = {"inicio": iso(nuevo), "fin": iso(nuevo + timedelta(hours=2))}
    assert cliente.put(url, json={"inicio": iso(nuevo), "fin": iso(nuevo)}, headers=org["headers"]).status_code == 422
    pasado = tiempo.ahora() - timedelta(days=1)
    r = cliente.put(url, json={"inicio": iso(pasado), "fin": iso(pasado + timedelta(hours=1))}, headers=org["headers"])
    assert r.status_code == 422 and codigo(r) == "FECHA_EN_PASADO"
    assert cliente.put(url, json=cuerpo, headers=org["headers"]).status_code == 200          # sin inscritos: se puede
    inscribir(cliente, ev["id"], 1)
    r = cliente.put(url, json={"inicio": iso(nuevo + timedelta(days=1)), "fin": iso(nuevo + timedelta(days=1, hours=2))},
                    headers=org["headers"])
    assert r.status_code == 409 and codigo(r) == "FECHAS_BLOQUEADAS"                          # con inscritos: no
    reloj.fijar(nuevo + timedelta(minutes=5))
    r = cliente.put(url, json={"fin": iso(nuevo + timedelta(hours=3))}, headers=org["headers"])
    assert r.status_code == 409 and codigo(r) == "EVENTO_YA_INICIADO"
    assert cliente.put(url, json={"lugar": "Otro salón"}, headers=org["headers"]).status_code == 200  # lo demás sí


def test_un_borrador_vencido_se_puede_reprogramar_y_publicar(cliente, org, reloj):
    ev = evento_en(cliente, org["headers"], desde=timedelta(hours=2), publicado=False)
    reloj.avanzar(hours=5)                                                     # la fecha pasó sin publicarlo
    url = f"/api/eventos/{ev['id']}"
    r = cliente.patch(f"{url}/estado", json={"estado": "publicado"}, headers=org["headers"])
    assert r.status_code == 422 and codigo(r) == "FECHA_EN_PASADO"
    pasado = tiempo.ahora() - timedelta(hours=1)
    r = cliente.put(url, json={"inicio": iso(pasado), "fin": iso(pasado + timedelta(hours=2))}, headers=org["headers"])
    assert r.status_code == 422 and codigo(r) == "FECHA_EN_PASADO"            # no a otra fecha pasada
    nuevo = tiempo.ahora() + timedelta(days=1)
    r = cliente.put(url, json={"inicio": iso(nuevo), "fin": iso(nuevo + timedelta(hours=2))}, headers=org["headers"])
    assert r.status_code == 200
    assert publicar(cliente, org["headers"], ev["id"])["estado"] == "publicado"


def test_no_se_edita_un_evento_cancelado_o_finalizado(cliente, org, reloj):
    cancelado = evento_publicado(cliente, org["headers"], titulo="Evento A cancelar")
    cliente.patch(f"/api/eventos/{cancelado['id']}/estado", json={"estado": "cancelado"}, headers=org["headers"])
    r = cliente.put(f"/api/eventos/{cancelado['id']}", json={"lugar": "Sala E"}, headers=org["headers"])
    assert r.status_code == 409 and codigo(r) == "EVENTO_NO_EDITABLE"
    reloj.fijar(instante(cancelado["fin"]) + timedelta(hours=1))
    fin = evento_en(cliente, org["headers"], titulo="Evento a finalizar")
    reloj.fijar(instante(fin["fin"]) + timedelta(hours=1))
    r = cliente.put(f"/api/eventos/{fin['id']}", json={"lugar": "Sala F"}, headers=org["headers"])
    assert r.status_code == 409 and codigo(r) == "EVENTO_NO_EDITABLE"


# --------------------------------------------------- panel y organizadores
def test_panel_muestra_los_eventos_segun_el_rol(cliente, org, org2, coord):
    a = crear_evento(cliente, org["headers"], titulo="Evento de Ana")
    b = crear_evento(cliente, org2["headers"], titulo="Evento de Luis")
    publicar(cliente, org["headers"], a["id"])
    titulos = lambda h, **p: sorted(e["titulo"] for e in cliente.get("/api/panel/eventos", headers=h, params=p).json())
    assert titulos(org["headers"]) == ["Evento de Ana"] and titulos(org2["headers"]) == ["Evento de Luis"]
    assert titulos(coord["headers"]) == ["Evento de Ana", "Evento de Luis"]
    assert titulos(coord["headers"], estado="borrador") == ["Evento de Luis"]
    assert cliente.get("/api/panel/eventos").status_code == 401
    assert cliente.get("/api/panel/eventos", params={"estado": "otro"}, headers=coord["headers"]).status_code == 422


def test_lista_de_organizadores_solo_para_la_coordinacion(cliente, org, coord):
    assert cliente.get("/api/organizadores").status_code == 401
    assert cliente.get("/api/organizadores", headers=org["headers"]).status_code == 403
    r = cliente.get("/api/organizadores", headers=coord["headers"])
    assert r.status_code == 200 and {u["nombre"] for u in r.json()} == {"Ana Torres", "Carlos Ruiz"}
    assert "password" not in r.text and "correo" not in r.text
