"""Contraseñas, inicio de sesión, tokens, roles y cabeceras de seguridad."""
import base64
import json
from datetime import timedelta

import jwt
import pytest

from app import auth, config, db, tiempo
from ayudas import PASSWORD, codigo, crear_usuario, login, payload_evento


# --------------------------------------------------------------- contraseñas
def test_hash_usa_scrypt_con_sal_unica():
    h1, h2 = auth.hash_password(PASSWORD), auth.hash_password(PASSWORD)
    assert h1.startswith("scrypt$16384$8$1$") and PASSWORD not in h1
    assert h1 != h2                                       # sal aleatoria distinta cada vez
    assert auth.verificar_password(PASSWORD, h1) and auth.verificar_password(PASSWORD, h2)


def test_verificar_rechaza_incorrectas_y_formatos_corruptos():
    h = auth.hash_password(PASSWORD)
    assert not auth.verificar_password(PASSWORD + "x", h)
    assert not auth.verificar_password("", h)
    for roto in ("", "texto-plano", "scrypt$1$2$3", "md5$16384$8$1$AAAA$AAAA", "scrypt$x$8$1$AAAA$AAAA",
                 "scrypt$16384$8$1$!!!$AAAA", None):
        assert not auth.verificar_password(PASSWORD, roto)


def test_la_base_de_datos_no_guarda_contrasenas_en_texto_plano():
    crear_usuario("Ana Torres", "ana@ejemplo.test", "organizador")
    with db.lectura() as conn:
        almacenado = conn.execute("SELECT password_hash FROM usuarios").fetchone()[0]
    assert PASSWORD not in almacenado and almacenado.startswith("scrypt$")


def test_la_base_de_datos_rechaza_hashes_que_no_son_scrypt():
    with pytest.raises(Exception):
        with db.transaccion() as conn:
            conn.execute("INSERT INTO usuarios (nombre, correo, password_hash, rol) "
                         "VALUES ('Ana Torres', 'a@ejemplo.test', 'Clave-Segura-123', 'organizador')")


@pytest.mark.parametrize("clave", ["Clave-Segura-123", "UnaFraseLarga con espacios 9", "ñandú-Ñoño-2026x"])
def test_politica_acepta_contrasenas_fuertes(clave):
    auth.validar_politica_password(clave)


@pytest.mark.parametrize("clave", ["", "Ab1", "SoloLetrasLargas", "12345678901234", " Clave-Segura-123",
                                   "Clave-Segura-123 ", "a1" * 70])
def test_politica_rechaza_contrasenas_debiles(clave):
    with pytest.raises(ValueError):
        auth.validar_politica_password(clave)


# --------------------------------------------------------------- inicio de sesión
def test_login_correcto_devuelve_token_y_usuario_sin_datos_sensibles(cliente, org):
    r = cliente.post("/api/auth/login", json={"correo": org["correo"], "password": PASSWORD})
    assert r.status_code == 200
    d = r.json()
    assert d["token_type"] == "bearer" and d["usuario"]["rol"] == "organizador"
    assert "password" not in r.text and "scrypt" not in r.text
    assert cliente.get("/api/auth/me", headers={"Authorization": f"Bearer {d['access_token']}"}).json()["id"] == org["id"]


def test_login_normaliza_el_correo(cliente, org):
    r = cliente.post("/api/auth/login", json={"correo": "  ANA.TORRES@Ejemplo.TEST ", "password": PASSWORD})
    assert r.status_code == 200


def test_login_fallido_no_revela_si_el_correo_existe(cliente, org):
    mala = cliente.post("/api/auth/login", json={"correo": org["correo"], "password": "incorrecta-123"})
    inexistente = cliente.post("/api/auth/login", json={"correo": "nadie@ejemplo.test", "password": "incorrecta-123"})
    assert mala.status_code == inexistente.status_code == 401
    assert mala.json() == inexistente.json() and codigo(mala) == "CREDENCIALES_INVALIDAS"


def test_login_de_usuario_inactivo(cliente):
    crear_usuario("Inactivo Uno", "inactivo@ejemplo.test", "organizador", activo=0)
    r = cliente.post("/api/auth/login", json={"correo": "inactivo@ejemplo.test", "password": PASSWORD})
    assert r.status_code == 401 and codigo(r) == "CREDENCIALES_INVALIDAS"


@pytest.mark.parametrize("cuerpo", [{}, {"correo": "a@b.com"}, {"password": "x"}, {"correo": "no-es-correo", "password": "x"},
                                    {"correo": "' OR 1=1 --", "password": "x"}, {"correo": "a@b.com", "password": ""},
                                    {"correo": "a@b.com", "password": 123}, {"correo": None, "password": None}])
def test_login_con_datos_invalidos(cliente, org, cuerpo):
    assert cliente.post("/api/auth/login", json=cuerpo).status_code == 422


def test_inyeccion_sql_en_la_contrasena_no_funciona(cliente, org):
    r = cliente.post("/api/auth/login", json={"correo": org["correo"], "password": "' OR '1'='1"})
    assert r.status_code == 401


def test_bloqueo_tras_cinco_intentos_fallidos(cliente, org, reloj):
    for _ in range(config.INTENTOS_LOGIN_MAXIMOS):
        assert cliente.post("/api/auth/login", json={"correo": org["correo"], "password": "mala-123456"}).status_code == 401
    r = cliente.post("/api/auth/login", json={"correo": org["correo"], "password": PASSWORD})  # ni la correcta
    assert r.status_code == 429 and codigo(r) == "DEMASIADOS_INTENTOS" and "retry-after" in r.headers
    otro = crear_usuario("Otro Usuario", "otro@ejemplo.test", "organizador")
    assert cliente.post("/api/auth/login", json={"correo": "otro@ejemplo.test", "password": PASSWORD}).status_code == 200
    reloj.avanzar(minutes=config.BLOQUEO_LOGIN_MINUTOS + 1)
    assert cliente.post("/api/auth/login", json={"correo": org["correo"], "password": PASSWORD}).status_code == 200


def test_un_login_exitoso_reinicia_el_conteo_de_fallos(cliente, org):
    for _ in range(config.INTENTOS_LOGIN_MAXIMOS - 1):
        cliente.post("/api/auth/login", json={"correo": org["correo"], "password": "mala-123456"})
    assert cliente.post("/api/auth/login", json={"correo": org["correo"], "password": PASSWORD}).status_code == 200
    for _ in range(config.INTENTOS_LOGIN_MAXIMOS - 1):
        assert cliente.post("/api/auth/login", json={"correo": org["correo"], "password": "mala-123456"}).status_code == 401


# --------------------------------------------------------------------- tokens
def test_el_token_vence_a_la_medianoche_de_colombia(cliente, org, reloj):
    r = cliente.post("/api/auth/login", json={"correo": org["correo"], "password": PASSWORD})
    assert r.json()["expira_en"] == "2026-12-02T00:00:00-05:00"
    cab = {"Authorization": f"Bearer {r.json()['access_token']}"}
    exp = jwt.decode(r.json()["access_token"], options={"verify_signature": False})["exp"]
    assert exp == int(tiempo.proxima_medianoche_bogota(reloj()).timestamp())
    reloj.fijar(tiempo.proxima_medianoche_bogota(reloj()) - timedelta(seconds=1))   # 23:59:59
    assert cliente.get("/api/auth/me", headers=cab).status_code == 200
    reloj.avanzar(seconds=1)                                                          # 00:00:00
    r2 = cliente.get("/api/auth/me", headers=cab)
    assert r2.status_code == 401 and codigo(r2) == "TOKEN_EXPIRADO"


def test_token_emitido_poco_antes_de_medianoche_dura_poco(reloj):
    reloj.fijar(tiempo.inicio_del_dia(reloj().astimezone(tiempo.BOGOTA).date() + timedelta(days=1)) - timedelta(minutes=10))
    _, vence = auth.crear_token({"id": 1})
    assert vence - reloj() == timedelta(minutes=10)


def _token(**cambios):
    datos = {"sub": "1", "iat": tiempo.ahora(), "exp": tiempo.ahora() + timedelta(hours=1)}
    datos.update(cambios)
    return jwt.encode(datos, config.obtener_secret_key(), algorithm="HS256")


def _con(token):
    return {"Authorization": f"Bearer {token}"}


def test_tokens_manipulados_o_invalidos_se_rechazan(cliente, org):
    valido = _token(sub=str(org["id"]))
    assert cliente.get("/api/auth/me", headers=_con(valido)).status_code == 200
    sin_firma = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode() + "." + \
        base64.urlsafe_b64encode(json.dumps({"sub": str(org["id"]), "exp": 4102444800, "iat": 1}).encode()).rstrip(b"=").decode() + "."
    otra_clave = jwt.encode({"sub": str(org["id"]), "iat": tiempo.ahora(), "exp": tiempo.ahora() + timedelta(hours=1)},
                            "otra-clave-distinta-de-32-caracteres-o-mas!!", algorithm="HS256")
    for token in (valido[:-3] + "AAA", valido + "x", "abc", "", "a.b.c", sin_firma, otra_clave,
                  _token(sub="abc"), _token(sub=str(org["id"]) + "; DROP TABLE usuarios"), _token(sub="999999"),
                  jwt.encode({"sub": "1", "iat": tiempo.ahora()}, config.obtener_secret_key(), algorithm="HS256")):  # sin exp
        r = cliente.get("/api/auth/me", headers=_con(token))
        assert r.status_code == 401, token
        assert codigo(r) in ("NO_AUTENTICADO", "TOKEN_EXPIRADO")


def test_algoritmo_distinto_se_rechaza(cliente, org):
    token = jwt.encode({"sub": str(org["id"]), "iat": tiempo.ahora(), "exp": tiempo.ahora() + timedelta(hours=1)},
                       config.obtener_secret_key(), algorithm="HS512")
    assert cliente.get("/api/auth/me", headers=_con(token)).status_code == 401


def test_sin_cabecera_o_con_esquema_distinto(cliente):
    assert cliente.get("/api/auth/me").status_code == 401
    r = cliente.get("/api/auth/me", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401 and codigo(r) == "NO_AUTENTICADO"
    r = cliente.post("/api/eventos", json=payload_evento())
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_usuario_desactivado_pierde_acceso_de_inmediato(cliente, org):
    assert cliente.get("/api/auth/me", headers=org["headers"]).status_code == 200
    with db.transaccion() as conn:
        conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (org["id"],))
    assert cliente.get("/api/auth/me", headers=org["headers"]).status_code == 401


def test_el_rol_se_lee_de_la_base_de_datos_no_del_token(cliente, org):
    assert cliente.get("/api/organizadores", headers=org["headers"]).status_code == 403
    with db.transaccion() as conn:
        conn.execute("UPDATE usuarios SET rol = 'coordinacion' WHERE id = ?", (org["id"],))
    assert cliente.get("/api/organizadores", headers=org["headers"]).status_code == 200  # cambio inmediato


def test_la_aplicacion_exige_una_clave_secreta_fuerte(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "corta")
    with pytest.raises(RuntimeError):
        config.obtener_secret_key()
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(RuntimeError):
        config.obtener_secret_key()


# ------------------------------------------------------------------- cabeceras
def test_cabeceras_de_seguridad(cliente):
    r = cliente.get("/api/salud")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store" and "default-src 'self'" in r.headers["content-security-policy"]
    assert "content-security-policy" not in cliente.get("/docs").headers   # /docs usa recursos de un CDN
