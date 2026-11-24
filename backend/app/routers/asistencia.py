from fastapi import APIRouter, Depends

from .. import auth, reglas
from ..schemas import AsistenciaIn, AsistenciaLoteIn
from .comun import IdPath

router = APIRouter(tags=["Asistencia"])


@router.put("/eventos/{evento_id}/asistencia/{inscripcion_id}", summary="Registrar o corregir asistencia")
def registrar(evento_id: IdPath, inscripcion_id: IdPath, datos: AsistenciaIn,
              usuario: dict = Depends(auth.usuario_actual)):
    return reglas.registrar_asistencia(usuario, evento_id, inscripcion_id, datos.estado)


@router.post("/eventos/{evento_id}/asistencia/lote", summary="Registrar asistencia de varios inscritos")
def registrar_lote(evento_id: IdPath, datos: AsistenciaLoteIn, usuario: dict = Depends(auth.usuario_actual)):
    return reglas.registrar_asistencia_lote(usuario, evento_id, datos.inscripcion_ids, datos.estado)
