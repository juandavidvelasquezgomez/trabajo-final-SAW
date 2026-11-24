import os

os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-0123456789abcdef0123456789"

from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, config, db, tiempo  # noqa: E402
from app.main import app  # noqa: E402
from ayudas import crear_usuario, login  # noqa: E402


class Reloj:
    """Reloj controlable: las pruebas fijan 'ahora' para verificar fechas y plazos."""

    def __init__(self):
        self.valor = datetime(2026, 12, 1, 17, 0, 0, tzinfo=tiempo.UTC)  # 12:00 en Colombia
        self.sesiones = []  # (id de usuario, cabeceras) de los usuarios de las fixtures

    def __call__(self):
        return self.valor

    def _renovar_sesiones(self):
        """Los tokens vencen a medianoche (RN-14). Al mover el reloj, las fixtures 'vuelven a
        iniciar sesión' para que cada prueba pueda concentrarse en lo que verifica."""
        for usuario_id, cabeceras in self.sesiones:
            token, _ = auth.crear_token({"id": usuario_id})
            cabeceras["Authorization"] = f"Bearer {token}"

    def avanzar(self, **kwargs):
        self.valor += timedelta(**kwargs)
        self._renovar_sesiones()

    def fijar(self, dt):
        self.valor = dt
        self._renovar_sesiones()


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch, reloj):
    monkeypatch.setattr(config, "DATABASE_PATH", tmp_path / "prueba.db")
    monkeypatch.setattr(tiempo, "ahora", reloj)
    db.iniciar_bd()
    auth.reiniciar_bloqueos()


@pytest.fixture
def cliente():
    return TestClient(app)


def _usuario(cliente, reloj, nombre, correo, rol):
    uid = crear_usuario(nombre, correo, rol)
    cabeceras = login(cliente, correo)
    reloj.sesiones.append((uid, cabeceras))
    return {"id": uid, "correo": correo, "headers": cabeceras}


@pytest.fixture
def coord(cliente, reloj):
    return _usuario(cliente, reloj, "Carlos Ruiz", "coordinacion@ejemplo.test", "coordinacion")


@pytest.fixture
def org(cliente, reloj):
    return _usuario(cliente, reloj, "Ana Torres", "ana.torres@ejemplo.test", "organizador")


@pytest.fixture
def org2(cliente, reloj):
    return _usuario(cliente, reloj, "Luis Mora", "luis.mora@ejemplo.test", "organizador")
