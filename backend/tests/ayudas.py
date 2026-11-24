"""Funciones de apoyo para las pruebas."""
from datetime import timedelta

from app import db, tiempo
from app.auth import hash_password

PASSWORD = "Clave-Segura-123"


def crear_usuario(nombre, correo, rol, password=PASSWORD, activo=1) -> int:
    with db.transaccion() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nombre, correo, password_hash, rol, activo) VALUES (?, ?, ?, ?, ?)",
            (nombre, correo, hash_password(password), rol, activo))
        return cur.lastrowid


def login(cliente, correo, password=PASSWORD) -> dict:
    r = cliente.post("/api/auth/login", json={"correo": correo, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def iso(dt) -> str:
    return dt.astimezone(tiempo.BOGOTA).isoformat()


def payload_evento(**cambios) -> dict:
    """Evento válido que empieza en 2 días y dura 3 horas (respecto al reloj de la prueba)."""
    inicio = tiempo.ahora() + timedelta(days=2)
    base = {"titulo": "Taller de Python", "tipo": "taller", "inicio": iso(inicio),
            "fin": iso(inicio + timedelta(hours=3)), "lugar": "Aula 301", "cupo": 30,
            "descripcion": "Introducción práctica"}
    base.update(cambios)
    return base


def payload_participante(n=1, **cambios) -> dict:
    base = {"nombre_completo": f"Persona Número{'abcdefghij'[n % 10]}", "correo": f"persona{n}@ejemplo.test",
            "documento": str(1000000000 + n), "rol": "estudiante"}
    base.update(cambios)
    return base


def crear_evento(cliente, headers, **cambios) -> dict:
    r = cliente.post("/api/eventos", json=payload_evento(**cambios), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def publicar(cliente, headers, evento_id) -> dict:
    r = cliente.patch(f"/api/eventos/{evento_id}/estado", json={"estado": "publicado"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def evento_publicado(cliente, headers, **cambios) -> dict:
    ev = crear_evento(cliente, headers, **cambios)
    return publicar(cliente, headers, ev["id"])


def evento_en(cliente, headers, desde=timedelta(days=2), horas=3, publicado=True, **cambios) -> dict:
    """Evento que empieza dentro de `desde` y dura `horas`, respecto al reloj de la prueba."""
    inicio = tiempo.ahora() + desde
    ev = crear_evento(cliente, headers, inicio=iso(inicio), fin=iso(inicio + timedelta(hours=horas)), **cambios)
    return publicar(cliente, headers, ev["id"]) if publicado else ev


def instante(texto_iso):
    from datetime import datetime
    return datetime.fromisoformat(texto_iso)


def inscribir(cliente, evento_id, n=1, **cambios):
    return cliente.post(f"/api/eventos/{evento_id}/inscripciones", json=payload_participante(n, **cambios))


def codigo(respuesta) -> str:
    return respuesta.json()["error"]["codigo"]
