from typing import Literal

from fastapi import APIRouter, Depends

from .. import auth, reglas
from ..schemas import (CancelarInscripcionIn, InscripcionEstadoIn, ParticipanteIn, normalizar_correo,
                       normalizar_documento)
from .comun import IdPath, normalizar_consulta

router = APIRouter(tags=["Inscripciones"])


@router.post("/eventos/{evento_id}/inscripciones", status_code=201, summary="Inscribirse en un evento")
def inscribir(evento_id: IdPath, datos: ParticipanteIn):
    return reglas.inscribir(evento_id, datos)


@router.post("/eventos/{evento_id}/inscripciones/cancelar", summary="Cancelar la propia inscripción")
def cancelar(evento_id: IdPath, datos: CancelarInscripcionIn):
    return reglas.cancelar_inscripcion(evento_id, datos.correo, datos.documento)


@router.post("/eventos/{evento_id}/inscripciones/en-el-momento", status_code=201,
             summary="Inscribir y marcar presente durante el evento")
def en_el_momento(evento_id: IdPath, datos: ParticipanteIn, usuario: dict = Depends(auth.usuario_actual)):
    return reglas.inscribir_en_el_momento(usuario, evento_id, datos)


@router.get("/eventos/{evento_id}/inscripciones", summary="Inscritos de un evento y su asistencia")
def inscritos(evento_id: IdPath, estado: Literal["activa", "cancelada", "cancelada_por_evento"] | None = None,
              usuario: dict = Depends(auth.usuario_actual)):
    return reglas.listar_inscritos(usuario, evento_id, estado)


@router.get("/inscripciones", summary="Consultar las inscripciones de un participante")
def consultar(correo: str, documento: str):
    return reglas.consultar_inscripciones(normalizar_consulta(normalizar_correo, correo, "correo"),
                                          normalizar_consulta(normalizar_documento, documento, "documento"))


@router.patch("/inscripciones/{inscripcion_id}", summary="Cancelar una inscripción (personal)")
def cambiar_estado(inscripcion_id: IdPath, datos: InscripcionEstadoIn, usuario: dict = Depends(auth.usuario_actual)):
    return reglas.cancelar_inscripcion_personal(usuario, inscripcion_id)
