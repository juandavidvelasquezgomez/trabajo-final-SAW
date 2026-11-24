"""Validación de los datos de entrada: tipos, formatos, rangos, fechas, correos, números y
normalización. Se prueban los modelos directamente y también la respuesta HTTP."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app import tiempo
from app.schemas import (AsistenciaLoteIn, EventoCrear, EventoEditar, LoginIn, ParticipanteIn,
                         normalizar_correo, normalizar_documento)
from ayudas import codigo, payload_evento, payload_participante


def participante(**cambios):
    return ParticipanteIn(**payload_participante(1, **cambios))


def evento(**cambios):
    return EventoCrear(**payload_evento(**cambios))


# ------------------------------------------------------------------- correos
@pytest.mark.parametrize("entrada,esperado", [
    ("laura@ejemplo.test", "laura@ejemplo.test"),
    ("  Laura.Gomez@EJEMPLO.Test  ", "laura.gomez@ejemplo.test"),
    ("a+etiqueta@sub.dominio.co", "a+etiqueta@sub.dominio.co"),
    ("USUARIO_1@UNIVERSIDAD.EDU.CO", "usuario_1@universidad.edu.co"),
])
def test_correo_valido_se_normaliza(entrada, esperado):
    assert normalizar_correo(entrada) == esperado


@pytest.mark.parametrize("entrada", [
    "", "   ", "sin-arroba", "a@b", "@dominio.com", "a@@b.com", "a b@c.com", "a@b..com", ".a@b.com",
    "a.@b.com", "a..b@c.com", "a@-b.com", "a@b-.com", "a@.com", "ñandu@b.com", "<script>@b.com",
    "x" * 65 + "@b.com", "a@" + "b" * 250 + ".com", "a@b.c om", "a@b,com", "a;b@c.com",
])
def test_correo_invalido_se_rechaza(entrada):
    with pytest.raises(ValueError):
        normalizar_correo(entrada)


def test_correo_no_texto_se_rechaza():
    for valor in (None, 123, ["a@b.com"], {"x": 1}, True):
        with pytest.raises(ValidationError):
            participante(correo=valor)


# ---------------------------------------------------------------- documentos
@pytest.mark.parametrize("entrada,esperado", [
    ("1000000001", "1000000001"), ("1.000.000.001", "1000000001"), ("1 000 000 001", "1000000001"),
    ("ab-123 45", "AB12345"), ("  cc12345  ", "CC12345"),
])
def test_documento_se_normaliza(entrada, esperado):
    assert normalizar_documento(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "123", "1234", "X" * 21, "123$456", "12345€", "12;345", "123'456", "<12345>"])
def test_documento_invalido(entrada):
    with pytest.raises(ValueError):
        normalizar_documento(entrada)


def test_documento_numerico_no_texto_se_rechaza():
    with pytest.raises(ValidationError):
        participante(documento=1000000001)  # un número no es un texto


# ------------------------------------------------------------------- nombres
def test_nombre_se_limpia_y_colapsa_espacios():
    assert participante(nombre_completo="  María   José\tPérez  ").nombre_completo == "María José Pérez"
    assert participante(nombre_completo="Ana-María O'Brien Jr.").nombre_completo == "Ana-María O'Brien Jr."


@pytest.mark.parametrize("nombre", ["A", "  ", "12345", "Juan123", "<b>Juan</b>", "Ana\x00Perez", "'Ana", "x" * 101,
                                    "Ana; DROP TABLE x", "Ana‮Evil"])
def test_nombre_invalido(nombre):
    with pytest.raises(ValidationError):
        participante(nombre_completo=nombre)


def test_rol_y_programa():
    assert participante(rol="docente").rol == "docente"
    for rol in ("admin", "", "Estudiante ", None, 1):
        with pytest.raises(ValidationError):
            participante(rol=rol)
    with pytest.raises(ValidationError):
        participante(programa="x")
    assert participante(programa="  Desarrollo   de Software ").programa == "Desarrollo de Software"


def test_campos_desconocidos_se_rechazan():
    with pytest.raises(ValidationError):
        participante(es_admin=True)
    with pytest.raises(ValidationError):
        evento(estado="publicado")  # no se puede forzar el estado al crear
    with pytest.raises(ValidationError):
        evento(id=5)


# --------------------------------------------------------------------- cupo
@pytest.mark.parametrize("valor", [0, -1, 10001, "30", "treinta", 30.5, 30.0, True, False, None, [], {}])
def test_cupo_invalido(valor):
    with pytest.raises(ValidationError):
        evento(cupo=valor)


@pytest.mark.parametrize("valor", [1, 30, 10000])
def test_cupo_valido(valor):
    assert evento(cupo=valor).cupo == valor


# -------------------------------------------------------------------- fechas
def test_fecha_con_offset_se_convierte_a_utc():
    e = evento(inicio="2026-12-10T14:00:00-05:00", fin="2026-12-10T16:00:00-05:00")
    assert e.inicio == datetime(2026, 12, 10, 19, 0, tzinfo=tiempo.UTC)


def test_fecha_sin_zona_se_interpreta_como_hora_de_colombia():
    e = evento(inicio="2026-12-10T14:00:00", fin="2026-12-10T16:00")
    assert e.inicio == datetime(2026, 12, 10, 19, 0, tzinfo=tiempo.UTC)
    assert e.fin == datetime(2026, 12, 10, 21, 0, tzinfo=tiempo.UTC)


def test_fecha_en_utc_con_z():
    assert evento(inicio="2026-12-10T19:00:00Z", fin="2026-12-10T20:00:00Z").inicio.hour == 19


@pytest.mark.parametrize("valor", [
    "10/12/2026", "2026-12-10", "2026-12-10 14:00:00", "2026-02-30T10:00:00", "2026-13-01T10:00:00",
    "2026-12-10T25:00:00", "2026-12-10T14:61:00", "2026-12-10T14:00:00+25:00", "hoy", "", "  ", 20261210,
    None, [], "2019-12-10T10:00:00", "2101-01-01T10:00:00", "2026-12-10T14", "2026-12-10T14:00:00-5",
    "2026-12-10T14:00:00.1234567", "2025-02-29T10:00:00",
])
def test_fecha_invalida(valor):
    with pytest.raises(ValidationError):
        evento(inicio=valor)


# ------------------------------------------------------- título, tipo, imagen
@pytest.mark.parametrize("titulo", ["", "   ", "ab", "x" * 151, "\x00abc", "ab\u0007c", 123, None])
def test_titulo_invalido(titulo):
    with pytest.raises(ValidationError):
        evento(titulo=titulo)


def test_titulo_se_normaliza():
    assert evento(titulo="  Taller   de \n Python  ").titulo == "Taller de Python"


def test_tipo_invalido():
    for tipo in ("fiesta", "", "TALLER", None, 1):
        with pytest.raises(ValidationError):
            evento(tipo=tipo)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "ftp://x.com/a.png", "http://", "https://a b.com",
                                 "//x.com/a.png", "data:text/html,<script>1</script>", "x" * 501])
def test_url_de_imagen_invalida(url):
    with pytest.raises(ValidationError):
        evento(imagen_url=url)


def test_url_de_imagen_valida():
    assert evento(imagen_url="https://ejemplo.test/a.png").imagen_url == "https://ejemplo.test/a.png"


def test_descripcion_vacia_pasa_a_nulo_y_limite():
    assert evento(descripcion="   ").descripcion is None
    with pytest.raises(ValidationError):
        evento(descripcion="x" * 2001)


# ----------------------------------------------------------- otros modelos
def test_editar_exige_al_menos_un_campo_y_no_admite_nulos_obligatorios():
    with pytest.raises(ValidationError):
        EventoEditar()
    with pytest.raises(ValidationError):
        EventoEditar(titulo=None)
    assert EventoEditar(descripcion=None).model_fields_set == {"descripcion"}


def test_lote_de_asistencia():
    assert AsistenciaLoteIn(inscripcion_ids=[1, 2]).estado == "presente"
    for ids in ([], [1, 1], ["1"], [True], [0], [-1], [2147483648], "1", None):
        with pytest.raises(ValidationError):
            AsistenciaLoteIn(inscripcion_ids=ids)
    with pytest.raises(ValidationError):
        AsistenciaLoteIn(inscripcion_ids=list(range(1, 502)))


def test_login_normaliza_correo_y_exige_password():
    assert LoginIn(correo=" ANA@Ejemplo.test ", password="x").correo == "ana@ejemplo.test"
    for datos in ({"correo": "a@b.com", "password": ""}, {"correo": "a@b.com"}, {"password": "x"},
                  {"correo": "a@b.com", "password": "x" * 129}, {"correo": "a@b.com", "password": 123}):
        with pytest.raises(ValidationError):
            LoginIn(**datos)


# ------------------------------------------------------ respuesta HTTP de errores
def test_formato_de_error_de_validacion_no_repite_el_dato(cliente, org):
    ev = cliente.post("/api/eventos", json=payload_evento(), headers=org["headers"]).json()
    r = cliente.post(f"/api/eventos/{ev['id']}/inscripciones",
                     json=payload_participante(correo="no-es-correo-secreto", cupo=3))
    assert r.status_code == 422
    cuerpo = r.json()["error"]
    assert cuerpo["codigo"] == "DATOS_INVALIDOS"
    campos = {d["campo"] for d in cuerpo["detalles"]}
    assert {"correo", "cupo"} <= campos
    assert "no-es-correo-secreto" not in r.text


def test_cuerpo_vacio_o_json_malformado(cliente, org):
    assert cliente.post("/api/eventos", json={}, headers=org["headers"]).status_code == 422
    r = cliente.post("/api/eventos", content="{no es json", headers={**org["headers"], "Content-Type": "application/json"})
    assert r.status_code == 422 and codigo(r) == "DATOS_INVALIDOS"
    r = cliente.post("/api/eventos", json=[1, 2], headers=org["headers"])
    assert r.status_code == 422


@pytest.mark.parametrize("ruta", ["/api/eventos/0", "/api/eventos/-1", "/api/eventos/abc", "/api/eventos/1.5",
                                  "/api/eventos/99999999999999999999", "/api/eventos/2147483648"])
def test_identificadores_invalidos(cliente, ruta):
    r = cliente.get(ruta)
    assert r.status_code == 422 and codigo(r) == "DATOS_INVALIDOS"


def test_recurso_inexistente_y_metodo_no_permitido(cliente):
    r = cliente.get("/api/eventos/99999")
    assert r.status_code == 404 and codigo(r) == "EVENTO_NO_ENCONTRADO"
    r = cliente.get("/api/no-existe")
    assert r.status_code == 404 and codigo(r) == "RECURSO_NO_ENCONTRADO"
    r = cliente.delete("/api/eventos")
    assert r.status_code == 405 and codigo(r) == "METODO_NO_PERMITIDO"


def test_filtros_de_fecha_invalidos(cliente):
    for params in ({"desde": "10/12/2026"}, {"hasta": "2026-02-30"}, {"desde": "2026-1-1"}, {"tipo": "fiesta"},
                   {"desde": "1700000000"}, {"desde": "2026-12-01T10:30:00"}, {"hasta": "mañana"}, {"desde": "2026-13-01"},
                   {"desde": "20261201"}, {"hasta": "'; DROP TABLE eventos;--"}):
        r = cliente.get("/api/eventos", params=params)
        assert r.status_code == 422 and codigo(r) == "DATOS_INVALIDOS", params
    assert "Fecha inválida" in cliente.get("/api/eventos", params={"desde": "10/12/2026"}).json()["error"]["detalles"][0]["mensaje"]
    assert cliente.get("/api/eventos", params={"desde": "2026-12-01", "hasta": "2026-12-31"}).status_code == 200


def test_rango_de_fechas_invertido_se_rechaza_con_un_mensaje_claro(cliente, coord):
    mensaje = "La fecha «desde» no puede ser posterior a la fecha «hasta»."
    for ruta, cabeceras in (("/api/eventos", {}), ("/api/consolidado", coord["headers"])):
        r = cliente.get(ruta, params={"desde": "2028-05-22", "hasta": "1980-04-30"}, headers=cabeceras)
        assert r.status_code == 422 and codigo(r) == "DATOS_INVALIDOS", ruta
        assert r.json()["error"]["detalles"] == [{"campo": "desde", "mensaje": mensaje}], ruta
        # un solo día (desde = hasta) y un rango normal sí son válidos
        assert cliente.get(ruta, params={"desde": "2026-12-01", "hasta": "2026-12-01"}, headers=cabeceras).status_code == 200
        assert cliente.get(ruta, params={"desde": "2026-12-01", "hasta": "2026-12-31"}, headers=cabeceras).status_code == 200
        assert cliente.get(ruta, params={"desde": "2026-12-01"}, headers=cabeceras).status_code == 200   # un solo extremo


def test_texto_con_inyeccion_sql_o_html_se_guarda_como_texto(cliente, org):
    titulo = "x'); DROP TABLE eventos;-- <img src=x onerror=alert(1)>"
    r = cliente.post("/api/eventos", json=payload_evento(titulo=titulo), headers=org["headers"])
    assert r.status_code == 201
    assert r.json()["titulo"] == titulo                      # se almacena literal; el frontend lo muestra como texto
    assert cliente.get("/api/panel/eventos", headers=org["headers"]).json()[0]["titulo"] == titulo
