"""Aplicación FastAPI: API REST bajo /api, documentación en /docs y la interfaz web en /."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config, db
from .errores import registrar_manejadores
from .routers import asistencia, auth, consolidado, eventos, inscripciones

_RUTAS_DOCUMENTACION = ("/docs", "/redoc", "/openapi.json")


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    config.obtener_secret_key()  # falla al arrancar si la clave falta o es débil
    db.iniciar_bd()
    yield


def crear_app() -> FastAPI:
    app = FastAPI(title="Eventos Académicos - API", version="1.0.0", lifespan=ciclo_de_vida,
                  description="Organización de eventos y actividades académicas: eventos, inscripciones, "
                              "cupos, asistencia y consolidados.")
    registrar_manejadores(app)

    @app.middleware("http")
    async def cabeceras_de_seguridad(request, call_next):
        respuesta = await call_next(request)
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api"):
            respuesta.headers["Cache-Control"] = "no-store"
        if not request.url.path.startswith(_RUTAS_DOCUMENTACION):  # /docs carga recursos de un CDN
            respuesta.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline'; "
                "frame-ancestors 'none'")
        return respuesta

    @app.get("/api/salud", tags=["Sistema"], summary="Comprobación de estado")
    def salud():
        return {"estado": "ok"}

    for modulo in (auth, eventos, inscripciones, asistencia, consolidado):
        app.include_router(modulo.router, prefix="/api")

    if config.FRONTEND_DIR.is_dir():  # se monta al final para no tapar la API
        app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
    return app


app = crear_app()
