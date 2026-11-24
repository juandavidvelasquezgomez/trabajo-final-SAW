from typing import Literal

from fastapi import APIRouter, Depends

from .. import auth, reglas
from ..schemas import TIPOS_EVENTO, EstadoEventoIn, EventoCrear, EventoEditar
from .comun import Desde, Hasta, IdPath, limites_de_dia

router = APIRouter(tags=["Eventos"])


@router.get("/eventos", summary="Catálogo de eventos publicados")
def catalogo(tipo: Literal[TIPOS_EVENTO] | None = None, desde: Desde = None, hasta: Hasta = None):
    return reglas.catalogo(tipo, limites_de_dia(desde), limites_de_dia(hasta, fin_de_dia=True))


@router.get("/eventos/{evento_id}", summary="Detalle de un evento")
def detalle(evento_id: IdPath, usuario: dict | None = Depends(auth.usuario_opcional)):
    return reglas.detalle_evento(usuario, evento_id)


@router.post("/eventos", status_code=201, summary="Crear un evento (queda en borrador)")
def crear(datos: EventoCrear, usuario: dict = Depends(auth.usuario_actual)):
    return reglas.crear_evento(usuario, datos)


@router.put("/eventos/{evento_id}", summary="Editar un evento")
def editar(evento_id: IdPath, datos: EventoEditar, usuario: dict = Depends(auth.usuario_actual)):
    return reglas.editar_evento(usuario, evento_id, datos)


@router.patch("/eventos/{evento_id}/estado", summary="Publicar o cancelar un evento")
def cambiar_estado(evento_id: IdPath, datos: EstadoEventoIn, usuario: dict = Depends(auth.usuario_actual)):
    return reglas.cambiar_estado_evento(usuario, evento_id, datos.estado)


@router.get("/panel/eventos", summary="Eventos que gestiona el usuario (todos, si es coordinación)")
def panel(estado: Literal["borrador", "publicado", "cancelado", "finalizado"] | None = None,
          usuario: dict = Depends(auth.usuario_actual)):
    return reglas.panel_eventos(usuario, estado)


@router.get("/organizadores", summary="Usuarios que pueden ser organizadores (coordinación)")
def organizadores(_: dict = Depends(auth.exigir_coordinacion)):
    return reglas.listar_organizadores()
