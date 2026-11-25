"""Extensiones: constancia de asistencia (RF-19) y códigos QR (RF-20)."""
from datetime import timedelta

import pytest

from app import constancias, qr
from ayudas import codigo, crear_evento, evento_publicado, inscribir, instante, payload_participante

P1 = payload_participante(1)
DATOS = {"correo": P1["correo"], "documento": P1["documento"]}


def preparar(cliente, org, reloj, asistencia="presente", finalizar=True):
    ev = evento_publicado(cliente, org["headers"])
    ins = inscribir(cliente, ev["id"], 1).json()["id"]
    reloj.fijar(instante(ev["inicio"]) + timedelta(minutes=5))
    if asistencia:
        r = cliente.put(f"/api/eventos/{ev['id']}/asistencia/{ins}", json={"estado": asistencia}, headers=org["headers"])
        assert r.status_code == 200
    if finalizar:
        reloj.fijar(instante(ev["fin"]) + timedelta(minutes=1))
    return ev, ins


# ---------------------------------------------------------------- constancias
def test_constancia_con_asistencia_presente_y_evento_finalizado(cliente, org, reloj):
    ev, ins = preparar(cliente, org, reloj)
    r = cliente.post("/api/constancias", json=DATOS)
    assert r.status_code == 200 and len(r.json()) == 1
    c = r.json()[0]
    assert c["codigo"] == constancias.codigo_de(ins) and c["codigo"].startswith(f"EA-{ins}-")
    assert c["participante"] == {"nombre_completo": P1["nombre_completo"], "documento": P1["documento"]}
    assert c["evento"]["titulo"] == ev["titulo"] and c["evento"]["duracion_horas"] == 3.0
    assert c["evento"]["organizador"] == "Ana Torres" and c["evento"]["inicio"].endswith("-05:00")


def test_los_datos_se_normalizan_al_pedir_la_constancia(cliente, org, reloj):
    preparar(cliente, org, reloj)
    r = cliente.post("/api/constancias", json={"correo": "  PERSONA1@Ejemplo.TEST ", "documento": "1.000.000.001"})
    assert r.status_code == 200


@pytest.mark.parametrize("asistencia,finalizar", [("presente", False), ("ausente", True), (None, True)])
def test_no_hay_constancia_si_no_asistio_o_el_evento_no_termino(cliente, org, reloj, asistencia, finalizar):
    preparar(cliente, org, reloj, asistencia, finalizar)
    r = cliente.post("/api/constancias", json=DATOS)
    assert r.status_code == 404 and codigo(r) == "CONSTANCIA_NO_DISPONIBLE"


def test_datos_que_no_coinciden_dan_la_misma_respuesta(cliente, org, reloj):
    preparar(cliente, org, reloj)
    mal = cliente.post("/api/constancias", json={**DATOS, "documento": "9999999999"})
    nadie = cliente.post("/api/constancias", json={"correo": "nadie@ejemplo.test", "documento": "9999999999"})
    assert mal.status_code == nadie.status_code == 404 and mal.json() == nadie.json()


@pytest.mark.parametrize("cuerpo", [{}, {"correo": "x", "documento": "12345"}, {"correo": "a@b.com"},
                                    {"correo": "a@b.com", "documento": "12"}, {**DATOS, "extra": 1}])
def test_constancia_con_datos_invalidos(cliente, cuerpo):
    assert cliente.post("/api/constancias", json=cuerpo).status_code == 422


def test_los_datos_personales_no_viajan_en_la_direccion(cliente):
    # No existe un GET para pedir constancias con datos en la URL: solo POST
    r = cliente.get("/api/constancias", params=DATOS)
    assert r.status_code in (404, 405) and "error" in r.json()


def test_verificar_un_codigo_valido_oculta_el_documento(cliente, org, reloj):
    _, ins = preparar(cliente, org, reloj)
    cod = constancias.codigo_de(ins)
    r = cliente.get(f"/api/constancias/{cod.lower()}")             # se acepta en minúsculas
    assert r.status_code == 200 and r.json()["valida"] is True and r.json()["codigo"] == cod
    assert r.json()["participante"]["documento"] == "••••••0001"
    assert P1["documento"] not in r.text and P1["correo"] not in r.text


def test_codigos_falsos_o_manipulados_se_rechazan(cliente, org, reloj):
    _, ins = preparar(cliente, org, reloj)
    cod = constancias.codigo_de(ins)
    firma = cod.split("-")[2]
    cambiada = firma[:-1] + ("0" if firma[-1] != "0" else "1")
    for falso in (f"EA-{ins}-{cambiada}", f"EA-{ins + 1}-{firma}", f"EA-{ins}-{'0' * 16}", "EA-1", "abc",
                  f"EA-0-{firma}", f"EA-9999999999-{firma}", "' OR 1=1 --"):
        r = cliente.get(f"/api/constancias/{falso}")
        assert r.status_code == 404 and codigo(r) == "CONSTANCIA_NO_VALIDA", falso
    assert cliente.get(f"/api/constancias/{'A' * 41}").status_code == 422


def test_si_se_corrige_la_asistencia_la_constancia_deja_de_ser_valida(cliente, org, reloj):
    ev, ins = preparar(cliente, org, reloj)
    cod = constancias.codigo_de(ins)
    assert cliente.get(f"/api/constancias/{cod}").status_code == 200
    cliente.put(f"/api/eventos/{ev['id']}/asistencia/{ins}", json={"estado": "ausente"}, headers=org["headers"])
    assert cliente.get(f"/api/constancias/{cod}").status_code == 404
    assert cliente.post("/api/constancias", json=DATOS).status_code == 404


def test_el_codigo_depende_de_la_clave_secreta(cliente, org, reloj, monkeypatch):
    _, ins = preparar(cliente, org, reloj)
    cod = constancias.codigo_de(ins)
    monkeypatch.setenv("SECRET_KEY", "otra-clave-distinta-de-mas-de-32-caracteres-0000")
    assert constancias.codigo_de(ins) != cod
    assert cliente.get(f"/api/constancias/{cod}").status_code == 404


# -------------------------------------------------------------------- QR
def test_qr_de_un_evento_publicado_codifica_su_direccion(cliente, org, monkeypatch):
    monkeypatch.delenv("URL_PUBLICA", raising=False)
    ev = evento_publicado(cliente, org["headers"])
    r = cliente.get(f"/api/eventos/{ev['id']}/qr")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert r.content == qr.svg_de(f"http://testserver/evento.html?id={ev['id']}") and b"<svg" in r.content


def test_qr_con_direccion_publica_configurada(cliente, org, monkeypatch):
    ev = evento_publicado(cliente, org["headers"])
    monkeypatch.setenv("URL_PUBLICA", "http://192.168.1.20:8000/")
    assert cliente.get(f"/api/eventos/{ev['id']}/qr").content == qr.svg_de(f"http://192.168.1.20:8000/evento.html?id={ev['id']}")
    monkeypatch.setenv("URL_PUBLICA", "javascript:alert(1)")       # un valor no web se ignora
    assert cliente.get(f"/api/eventos/{ev['id']}/qr").content == qr.svg_de(f"http://testserver/evento.html?id={ev['id']}")


def test_qr_solo_para_eventos_publicados(cliente, org):
    borrador = crear_evento(cliente, org["headers"])
    assert cliente.get(f"/api/eventos/{borrador['id']}/qr").status_code == 404
    assert cliente.get("/api/eventos/99999/qr").status_code == 404
    assert cliente.get("/api/eventos/abc/qr").status_code == 422


def test_qr_de_una_constancia(cliente, org, reloj, monkeypatch):
    monkeypatch.delenv("URL_PUBLICA", raising=False)
    _, ins = preparar(cliente, org, reloj)
    cod = constancias.codigo_de(ins)
    r = cliente.get(f"/api/constancias/{cod}/qr")
    assert r.status_code == 200 and r.content == qr.svg_de(f"http://testserver/constancia.html?codigo={cod}")
    assert cliente.get(f"/api/constancias/EA-{ins}-{'0' * 16}/qr").status_code == 404
