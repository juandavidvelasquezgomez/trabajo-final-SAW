"""Información consolidada para la coordinación (CA-06): totales coherentes con los datos reales."""
from datetime import timedelta

from app import db
from ayudas import codigo, crear_evento, evento_en, evento_publicado, inscribir, instante


def consolidado(cliente, headers, **params):
    r = cliente.get("/api/consolidado", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def preparar(cliente, org, org2, reloj):
    """Tres eventos: uno ya finalizado con asistencia, uno próximo con inscritos y uno cancelado."""
    pasado = evento_en(cliente, org["headers"], desde=timedelta(days=1), horas=2, titulo="Taller finalizado", tipo="taller", cupo=4)
    ids = [inscribir(cliente, pasado["id"], n).json()["id"] for n in (1, 2, 3, 4)]
    reloj.fijar(instante(pasado["inicio"]) + timedelta(minutes=5))
    for ins in ids[:3]:                                                                # 3 de 4 asistieron
        assert cliente.put(f"/api/eventos/{pasado['id']}/asistencia/{ins}", json={"estado": "presente"},
                           headers=org["headers"]).status_code == 200
    reloj.fijar(instante(pasado["fin"]) + timedelta(hours=1))
    proximo = evento_en(cliente, org2["headers"], desde=timedelta(days=3), titulo="Seminario próximo", tipo="seminario", cupo=10)
    for n in (11, 12):
        inscribir(cliente, proximo["id"], n)
    cancelado = evento_en(cliente, org["headers"], desde=timedelta(days=5), titulo="Conferencia cancelada", tipo="conferencia", cupo=5)
    inscribir(cliente, cancelado["id"], 21)
    cliente.patch(f"/api/eventos/{cancelado['id']}/estado", json={"estado": "cancelado"}, headers=org["headers"])
    crear_evento(cliente, org["headers"], titulo="Evento en borrador", cupo=7)
    return pasado, proximo, cancelado


def test_solo_la_coordinacion_accede(cliente, org, coord):
    r = cliente.get("/api/consolidado")
    assert r.status_code == 401 and codigo(r) == "NO_AUTENTICADO"
    r = cliente.get("/api/consolidado", headers=org["headers"])
    assert r.status_code == 403 and codigo(r) == "SIN_PERMISO"
    assert cliente.get("/api/consolidado", headers=coord["headers"]).status_code == 200


def test_sin_eventos_los_totales_son_cero(cliente, coord):
    d = consolidado(cliente, coord["headers"])
    assert d["totales"] == {"eventos": 0, "por_estado": {"borrador": 0, "publicado": 0, "cancelado": 0, "finalizado": 0},
                            "inscripciones_activas": 0, "asistentes": 0, "porcentaje_asistencia_finalizados": None}
    assert d["eventos"] == []


def test_totales_y_detalle_son_coherentes_con_las_inscripciones_y_la_asistencia(cliente, org, org2, coord, reloj):
    pasado, proximo, cancelado = preparar(cliente, org, org2, reloj)
    d = consolidado(cliente, coord["headers"])
    por_id = {e["id"]: e for e in d["eventos"]}
    assert d["totales"]["eventos"] == 4
    assert d["totales"]["por_estado"] == {"borrador": 1, "publicado": 1, "cancelado": 1, "finalizado": 1}
    assert d["totales"]["inscripciones_activas"] == 6 and d["totales"]["asistentes"] == 3
    assert d["totales"]["porcentaje_asistencia_finalizados"] == 75.0

    f = por_id[pasado["id"]]
    assert (f["estado"], f["cupo"], f["inscritos_activos"], f["cupos_disponibles"], f["asistentes"]) == ("finalizado", 4, 4, 0, 3)
    assert f["porcentaje_asistencia"] == 75.0 and f["organizador"]["nombre"] == "Ana Torres"
    p = por_id[proximo["id"]]
    assert (p["inscritos_activos"], p["cupos_disponibles"], p["asistentes"], p["porcentaje_asistencia"]) == (2, 8, 0, None)
    c = por_id[cancelado["id"]]
    assert (c["estado"], c["inscritos_activos"], c["cupos_disponibles"]) == ("cancelado", 0, 5)   # sus inscripciones no cuentan

    # coherencia interna: cupos y totales salen de los mismos datos que ve el organizador
    assert sum(e["inscritos_activos"] for e in d["eventos"]) == d["totales"]["inscripciones_activas"]
    assert all(e["cupos_disponibles"] == e["cupo"] - e["inscritos_activos"] for e in d["eventos"])
    detalle = cliente.get(f"/api/eventos/{pasado['id']}/inscripciones", headers=org["headers"]).json()["inscripciones"]
    assert sum(1 for i in detalle if i["asistencia"] == "presente") == f["asistentes"]
    with db.lectura() as conn:
        assert conn.execute("SELECT count(*) FROM inscripciones WHERE estado = 'activa'").fetchone()[0] == d["totales"]["inscripciones_activas"]


def test_la_asistencia_corregida_se_refleja(cliente, org, org2, coord, reloj):
    pasado, *_ = preparar(cliente, org, org2, reloj)
    ins = cliente.get(f"/api/eventos/{pasado['id']}/inscripciones", headers=org["headers"]).json()["inscripciones"]
    presente = next(i["id"] for i in ins if i["asistencia"] == "presente")
    assert cliente.put(f"/api/eventos/{pasado['id']}/asistencia/{presente}", json={"estado": "ausente"}, headers=org["headers"]).status_code == 200
    assert consolidado(cliente, coord["headers"])["totales"]["asistentes"] == 2


def test_filtros(cliente, org, org2, coord, reloj):
    pasado, proximo, cancelado = preparar(cliente, org, org2, reloj)
    ids = lambda **p: sorted(e["id"] for e in consolidado(cliente, coord["headers"], **p)["eventos"])
    assert ids(tipo="seminario") == [proximo["id"]]
    assert ids(estado="finalizado") == [pasado["id"]] and ids(estado="cancelado") == [cancelado["id"]]
    assert ids(organizador_id=org2["id"]) == [proximo["id"]]
    assert len(ids(organizador_id=org["id"])) == 3
    dia = instante(proximo["inicio"]).date().isoformat()
    assert ids(desde=dia, hasta=dia) == [proximo["id"]]
    assert ids(desde="2030-01-01") == [] and ids(hasta="2020-01-01") == []
    assert ids(tipo="taller", estado="publicado") == []
    filtrado = consolidado(cliente, coord["headers"], tipo="seminario")
    assert filtrado["totales"]["eventos"] == 1 and filtrado["totales"]["inscripciones_activas"] == 2   # totales respetan el filtro


def test_filtros_invalidos(cliente, coord):
    for params in ({"desde": "10/12/2026"}, {"hasta": "2026-02-30"}, {"desde": "2026-12-31", "hasta": "2026-12-01"},
                   {"tipo": "fiesta"}, {"estado": "otro"}, {"organizador_id": 0}, {"organizador_id": "abc"}):
        r = cliente.get("/api/consolidado", headers=coord["headers"], params=params)
        assert r.status_code == 422 and codigo(r) == "DATOS_INVALIDOS", params
