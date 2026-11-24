"""Autenticación: contraseñas con hash scrypt, tokens JWT diarios y control de roles."""
import base64
import hashlib
import hmac
import os
import re
import threading
import unicodedata
from datetime import datetime

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config, db, tiempo
from .errores import ErrorApi

# ---------------------------------------------------------------- contraseñas
_N, _R, _P, _LONGITUD = 2 ** 14, 8, 1, 32
_COMUNES = {"password", "contrasena", "contraseña", "1234567890", "qwertyuiop", "administrador"}


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def _normalizar(password: str) -> bytes:
    return unicodedata.normalize("NFKC", password).encode("utf-8")


def hash_password(password: str) -> str:
    """scrypt con sal aleatoria única por contraseña. Formato: scrypt$N$r$p$sal$hash."""
    sal = os.urandom(16)
    derivada = hashlib.scrypt(_normalizar(password), salt=sal, n=_N, r=_R, p=_P, dklen=_LONGITUD)
    return f"scrypt${_N}${_R}${_P}${_b64(sal)}${_b64(derivada)}"


def verificar_password(password: str, almacenado: str) -> bool:
    if not isinstance(almacenado, str):
        return False
    try:
        esquema, n, r, p, sal, esperado = almacenado.split("$")
        if esquema != "scrypt":
            return False
        esperado_bytes = base64.b64decode(esperado)
        derivada = hashlib.scrypt(_normalizar(password), salt=base64.b64decode(sal),
                                  n=int(n), r=int(r), p=int(p), dklen=len(esperado_bytes))
        return hmac.compare_digest(derivada, esperado_bytes)  # comparación en tiempo constante
    except (ValueError, TypeError):
        return False


def validar_politica_password(password: str) -> None:
    """Política de contraseñas para cuentas del personal. Lanza ValueError si no cumple."""
    if not 10 <= len(password) <= 128:
        raise ValueError("La contraseña debe tener entre 10 y 128 caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", password) or not re.search(r"\d", password):
        raise ValueError("La contraseña debe incluir al menos una letra y un número.")
    if password.strip() != password:
        raise ValueError("La contraseña no puede empezar ni terminar con espacios.")
    if password.lower() in _COMUNES:
        raise ValueError("La contraseña es demasiado común.")


_HASH_FALSO = None


def _hash_falso() -> str:
    global _HASH_FALSO
    if _HASH_FALSO is None:
        _HASH_FALSO = hash_password("contraseña-de-relleno-1")
    return _HASH_FALSO


# ------------------------------------------------- bloqueo por intentos fallidos
_fallos: dict[str, list[float]] = {}
_candado = threading.Lock()


def reiniciar_bloqueos() -> None:
    with _candado:
        _fallos.clear()


def _recientes(clave: str) -> list[float]:
    limite = tiempo.ahora().timestamp() - config.BLOQUEO_LOGIN_MINUTOS * 60
    vigentes = [t for t in _fallos.get(clave, []) if t > limite]
    _fallos[clave] = vigentes
    return vigentes


def _bloqueado(clave: str) -> bool:
    with _candado:
        return len(_recientes(clave)) >= config.INTENTOS_LOGIN_MAXIMOS


def _registrar_fallo(clave: str) -> None:
    with _candado:
        _recientes(clave).append(tiempo.ahora().timestamp())


def autenticar(correo: str, password: str, ip: str) -> dict:
    clave = f"{correo}|{ip}"
    if _bloqueado(clave):
        raise ErrorApi(429, "DEMASIADOS_INTENTOS",
                       f"Demasiados intentos fallidos. Espera {config.BLOQUEO_LOGIN_MINUTOS} minutos.",
                       cabeceras={"Retry-After": str(config.BLOQUEO_LOGIN_MINUTOS * 60)})
    with db.lectura() as conn:
        fila = conn.execute("SELECT * FROM usuarios WHERE correo = ?", (correo,)).fetchone()
    # Se calcula siempre un hash, exista o no el usuario, para que el tiempo de respuesta
    # no revele si el correo está registrado.
    almacenado = fila["password_hash"] if fila else _hash_falso()
    correcto = verificar_password(password, almacenado)
    if not (fila and fila["activo"] and correcto):
        _registrar_fallo(clave)
        raise ErrorApi(401, "CREDENCIALES_INVALIDAS", "Correo o contraseña incorrectos.",
                       cabeceras={"WWW-Authenticate": "Bearer"})
    with _candado:
        _fallos.pop(clave, None)
    return {"id": fila["id"], "nombre": fila["nombre"], "correo": fila["correo"], "rol": fila["rol"]}


# ---------------------------------------------------------------------- tokens
_ALGORITMO = "HS256"


def crear_token(usuario: dict) -> tuple[str, datetime]:
    """El token vence en la próxima medianoche de Colombia (RN-14). No incluye el rol:
    se consulta en la base de datos en cada solicitud, así un cambio de rol o una
    desactivación surten efecto de inmediato."""
    emitido = tiempo.ahora()
    vence = tiempo.proxima_medianoche_bogota(emitido)
    token = jwt.encode({"sub": str(usuario["id"]), "iat": emitido, "exp": vence},
                       config.obtener_secret_key(), algorithm=_ALGORITMO)
    return token, vence


def _sin_autenticar(codigo: str, mensaje: str) -> ErrorApi:
    return ErrorApi(401, codigo, mensaje, cabeceras={"WWW-Authenticate": "Bearer"})


def _usuario_desde_token(token: str) -> dict:
    try:
        datos = jwt.decode(token, config.obtener_secret_key(), algorithms=[_ALGORITMO],
                           options={"require": ["exp", "sub", "iat"], "verify_exp": False,
                                    "verify_iat": False})
        vence = datetime.fromtimestamp(datos["exp"], tz=tiempo.UTC)
        usuario_id = int(datos["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise _sin_autenticar("NO_AUTENTICADO", "Sesión no válida. Inicia sesión de nuevo.")
    if tiempo.ahora() >= vence:  # se compara con el reloj de la aplicación
        raise _sin_autenticar("TOKEN_EXPIRADO", "La sesión venció. Inicia sesión de nuevo.")
    with db.lectura() as conn:
        fila = conn.execute("SELECT id, nombre, correo, rol, activo FROM usuarios WHERE id = ?",
                            (usuario_id,)).fetchone()
    if not fila or not fila["activo"]:
        raise _sin_autenticar("NO_AUTENTICADO", "Sesión no válida. Inicia sesión de nuevo.")
    return {"id": fila["id"], "nombre": fila["nombre"], "correo": fila["correo"], "rol": fila["rol"]}


_esquema = HTTPBearer(auto_error=False)


def usuario_opcional(credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema)) -> dict | None:
    if credenciales is None:
        return None
    return _usuario_desde_token(credenciales.credentials)


def usuario_actual(usuario: dict | None = Depends(usuario_opcional)) -> dict:
    if usuario is None:
        raise _sin_autenticar("NO_AUTENTICADO", "Debes iniciar sesión para realizar esta acción.")
    return usuario


def exigir_coordinacion(usuario: dict = Depends(usuario_actual)) -> dict:
    if usuario["rol"] != "coordinacion":
        raise ErrorApi(403, "SIN_PERMISO", "No tienes permiso para realizar esta acción.")
    return usuario
