"""Formato único de errores. Nunca se devuelven rastros internos ni datos sensibles (RNF-03)."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("eventos")


class ErrorApi(Exception):
    def __init__(self, status: int, codigo: str, mensaje: str, detalles: list | None = None,
                 cabeceras: dict | None = None):
        super().__init__(mensaje)
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or []
        self.cabeceras = cabeceras


def respuesta_error(status: int, codigo: str, mensaje: str, detalles: list | None = None,
                    cabeceras: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or []}},
        headers=cabeceras,
    )


_TRADUCCIONES = {
    "missing": "Campo obligatorio.",
    "string_too_short": "Es demasiado corto.",
    "string_too_long": "Es demasiado largo.",
    "string_type": "Debe ser un texto.",
    "int_type": "Debe ser un número entero.",
    "int_parsing": "Debe ser un número entero.",
    "int_from_float": "Debe ser un número entero, sin decimales.",
    "greater_than_equal": "Es menor que el mínimo permitido.",
    "less_than_equal": "Supera el máximo permitido.",
    "extra_forbidden": "Campo no permitido.",
    "literal_error": "Valor no permitido.",
    "json_invalid": "El cuerpo no es un JSON válido.",
    "model_attributes_type": "Se esperaba un objeto JSON.",
    "dict_type": "Se esperaba un objeto JSON.",
    "list_type": "Debe ser una lista.",
    "too_short": "Debe tener al menos un elemento.",
    "too_long": "Tiene demasiados elementos.",
    "bool_type": "Debe ser verdadero o falso.",
}


def _detalles_validacion(errores: list[dict]) -> list[dict]:
    detalles = []
    for e in errores:
        campo = ".".join(str(p) for p in e.get("loc", ())[1:])
        if e.get("type") == "value_error":
            mensaje = str(e.get("msg", "")).removeprefix("Value error, ")
        else:
            mensaje = _TRADUCCIONES.get(e.get("type", ""), "Valor inválido.")
        detalles.append({"campo": campo or "cuerpo", "mensaje": mensaje})  # sin eco del valor recibido
    return detalles


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorApi)
    async def _api(_: Request, exc: ErrorApi):
        return respuesta_error(exc.status, exc.codigo, exc.mensaje, exc.detalles, exc.cabeceras)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        return respuesta_error(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos.",
                               _detalles_validacion(exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        codigos = {404: ("RECURSO_NO_ENCONTRADO", "El recurso solicitado no existe."),
                   405: ("METODO_NO_PERMITIDO", "Método no permitido para este recurso.")}
        codigo, mensaje = codigos.get(exc.status_code, ("ERROR_HTTP", "No se pudo procesar la solicitud."))
        return respuesta_error(exc.status_code, codigo, mensaje, cabeceras=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception):
        log.exception("Error no controlado")  # el detalle queda en el log del servidor, no en la respuesta
        return respuesta_error(500, "ERROR_INTERNO", "Ocurrió un error inesperado. Inténtalo de nuevo.")
