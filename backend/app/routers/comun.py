"""Piezas compartidas por los routers."""
from datetime import date, datetime
from typing import Annotated

from fastapi import Path

from .. import tiempo
from ..errores import ErrorApi

IdPath = Annotated[int, Path(ge=1, le=2147483647)]


def _error_campo(campo: str, mensaje: str) -> ErrorApi:
    return ErrorApi(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos.",
                    [{"campo": campo, "mensaje": mensaje}])


def fecha_consulta(valor: str | None, campo: str, fin_de_dia: bool = False) -> datetime | None:
    """Fecha AAAA-MM-DD de un filtro -> instante UTC (inicio o fin de ese día en Colombia)."""
    if valor is None:
        return None
    try:
        if len(valor) != 10:
            raise ValueError
        dia = date.fromisoformat(valor)
    except ValueError:
        raise _error_campo(campo, "Fecha inválida. Formato: AAAA-MM-DD.")
    return tiempo.fin_del_dia(dia) if fin_de_dia else tiempo.inicio_del_dia(dia)


def normalizar_consulta(funcion, valor: str, campo: str) -> str:
    try:
        return funcion(valor)
    except ValueError as exc:
        raise _error_campo(campo, str(exc))
