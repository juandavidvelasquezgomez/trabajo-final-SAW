from typing import Literal

from fastapi import APIRouter, Depends

from .. import auth, reglas
from ..errores import ErrorApi
from ..schemas import TIPOS_EVENTO
from .comun import IdPath, fecha_consulta

router = APIRouter(tags=["Consolidado"])


@router.get("/consolidado", summary="Información consolidada de eventos, inscripciones y asistencia")
def consolidado(desde: str | None = None, hasta: str | None = None,
                tipo: Literal[TIPOS_EVENTO] | None = None,
                estado: Literal["borrador", "publicado", "cancelado", "finalizado"] | None = None,
                organizador_id: IdPath | None = None,
                _: dict = Depends(auth.exigir_coordinacion)):
    d, h = fecha_consulta(desde, "desde"), fecha_consulta(hasta, "hasta", fin_de_dia=True)
    if d and h and d > h:
        raise ErrorApi(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos.",
                       [{"campo": "desde", "mensaje": "La fecha inicial no puede ser posterior a la final."}])
    return reglas.consolidado(d, h, tipo, estado, organizador_id)
