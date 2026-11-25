"""Extensiones del alcance: constancias de asistencia y códigos QR."""
from typing import Annotated

from fastapi import APIRouter, Path, Request, Response

from .. import constancias, qr, reglas
from ..schemas import IdentificacionIn
from .comun import IdPath

router = APIRouter()
CodigoPath = Annotated[str, Path(min_length=1, max_length=40, description="Código de la constancia (EA-...)")]


def _imagen(texto: str) -> Response:
    return Response(content=qr.svg_de(texto), media_type="image/svg+xml")


@router.post("/constancias", tags=["Constancias"], summary="Constancias de asistencia de un participante")
def obtener(datos: IdentificacionIn):
    # POST: el correo y el documento viajan en el cuerpo y no quedan en la dirección ni en los registros
    return constancias.de_participante(datos.correo, datos.documento)


@router.get("/constancias/{codigo}", tags=["Constancias"], summary="Verificar una constancia por su código")
def verificar(codigo: CodigoPath):
    return constancias.verificar(codigo)


@router.get("/constancias/{codigo}/qr", tags=["Códigos QR"], summary="QR con el enlace de verificación",
            response_class=Response)
def qr_constancia(codigo: CodigoPath, solicitud: Request):
    valida = constancias.verificar(codigo)
    base = qr.direccion_publica(str(solicitud.base_url))
    return _imagen(f"{base}/constancia.html?codigo={valida['codigo']}")


@router.get("/eventos/{evento_id}/qr", tags=["Códigos QR"], summary="QR con el enlace a un evento publicado",
            response_class=Response)
def qr_evento(evento_id: IdPath, solicitud: Request):
    reglas.detalle_evento(None, evento_id)  # solo eventos publicados; si no, 404
    base = qr.direccion_publica(str(solicitud.base_url))
    return _imagen(f"{base}/evento.html?id={evento_id}")
