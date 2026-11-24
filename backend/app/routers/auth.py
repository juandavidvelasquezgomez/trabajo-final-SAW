from fastapi import APIRouter, Depends, Request

from .. import auth, tiempo
from ..schemas import LoginIn

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", summary="Iniciar sesión (organizador o coordinación)")
def login(datos: LoginIn, request: Request):
    ip = request.client.host if request.client else "desconocida"
    usuario = auth.autenticar(datos.correo, datos.password, ip)
    token, vence = auth.crear_token(usuario)
    return {"access_token": token, "token_type": "bearer",
            "expira_en": vence.astimezone(tiempo.BOGOTA).isoformat(), "usuario": usuario}


@router.get("/me", summary="Usuario autenticado")
def yo(usuario: dict = Depends(auth.usuario_actual)):
    return usuario
