from typing import Literal

from fastapi import APIRouter, Depends

from .. import auth, reglas
from ..schemas import TIPOS_EVENTO
from .comun import Desde, Hasta, IdPath, limites_de_dia, validar_rango_de_fechas

router = APIRouter(tags=["Consolidado"])


@router.get("/consolidado", summary="Información consolidada de eventos, inscripciones y asistencia")
def consolidado(desde: Desde = None, hasta: Hasta = None,
                tipo: Literal[TIPOS_EVENTO] | None = None,
                estado: Literal["borrador", "publicado", "cancelado", "finalizado"] | None = None,
                organizador_id: IdPath | None = None,
                _: dict = Depends(auth.exigir_coordinacion)):
    validar_rango_de_fechas(desde, hasta)
    return reglas.consolidado(limites_de_dia(desde), limites_de_dia(hasta, fin_de_dia=True),
                              tipo, estado, organizador_id)
