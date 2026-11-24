"""Piezas compartidas por los routers."""
from datetime import date, datetime
from typing import Annotated

from fastapi import Path, Query

from .. import tiempo
from ..errores import ErrorApi

IdPath = Annotated[int, Path(ge=1, le=2147483647)]


def _error_campo(campo: str, mensaje: str) -> ErrorApi:
    return ErrorApi(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos.",
                    [{"campo": campo, "mensaje": mensaje}])


Desde = Annotated[date | None, Query(description="Fecha inicial, inclusive (AAAA-MM-DD, hora de Colombia). "
                                                 "No puede ser posterior a «hasta».", examples=["2026-12-01"])]
Hasta = Annotated[date | None, Query(description="Fecha final, inclusive (AAAA-MM-DD, hora de Colombia). "
                                                 "No puede ser anterior a «desde».", examples=["2026-12-31"])]


def validar_rango_de_fechas(desde: date | None, hasta: date | None) -> None:
    """Un rango invertido se rechaza con un mensaje claro, en lugar de devolver una lista vacía.
    Fechas iguales son válidas: así se consulta un solo día."""
    if desde and hasta and desde > hasta:
        mensaje = "La fecha «desde» no puede ser posterior a la fecha «hasta»."
        raise ErrorApi(422, "DATOS_INVALIDOS", mensaje, [{"campo": "desde", "mensaje": mensaje}])


def limites_de_dia(valor: date | None, fin_de_dia: bool = False) -> datetime | None:
    """Fecha de un filtro -> instante UTC (inicio o fin de ese día en Colombia)."""
    if valor is None:
        return None
    return tiempo.fin_del_dia(valor) if fin_de_dia else tiempo.inicio_del_dia(valor)


def normalizar_consulta(funcion, valor: str, campo: str) -> str:
    try:
        return funcion(valor)
    except ValueError as exc:
        raise _error_campo(campo, str(exc))
