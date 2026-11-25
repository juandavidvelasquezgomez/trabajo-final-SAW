"""Extensión: códigos QR (RF-20). Se generan en el servidor como imagen SVG con la librería segno."""
import io
import os

import segno

from . import config  # noqa: F401  (al importarlo se carga el archivo .env)


def direccion_publica(base_de_la_solicitud: str) -> str:
    """Dirección que se codifica en el QR. Por defecto, la usada para abrir la aplicación;
    con URL_PUBLICA se fija otra (por ejemplo la IP de la red local, para escanear desde un celular)."""
    configurada = os.getenv("URL_PUBLICA", "").strip().rstrip("/")
    if configurada.startswith(("http://", "https://")):
        return configurada
    return base_de_la_solicitud.rstrip("/")


def svg_de(texto: str) -> bytes:
    salida = io.BytesIO()
    segno.make(texto, error="m", micro=False).save(salida, kind="svg", scale=6, border=3,
                                                    dark="#0f172a", light="#ffffff")
    return salida.getvalue()
