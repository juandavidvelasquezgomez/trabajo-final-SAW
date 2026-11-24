"""Configuración. Los secretos salen de variables de entorno (.env), nunca del código."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent.parent
load_dotenv(RAIZ / ".env")

# Plazos y límites acordados en docs/requisitos.md
DURACION_MAXIMA_HORAS = 8          # RN-09
VENTANA_REGISTRO_HORAS = 2         # RN-11: registrar asistencia hasta fin + 2 h
VENTANA_CORRECCION_HORAS = 24      # RN-11: corregir asistencia hasta fin + 24 h
CUPO_MAXIMO = 10000
INTENTOS_LOGIN_MAXIMOS = 5
BLOQUEO_LOGIN_MINUTOS = 15
LONGITUD_MINIMA_SECRET = 32

DATABASE_PATH = Path(os.getenv("DATABASE_PATH") or (RAIZ / "backend" / "db" / "eventos.db"))
SCHEMA_SQL = RAIZ / "backend" / "db" / "schema.sql"
FRONTEND_DIR = RAIZ / "frontend"


def obtener_secret_key() -> str:
    """Devuelve la clave de firma o falla con un mensaje claro si es insegura."""
    clave = os.getenv("SECRET_KEY", "")
    if len(clave) < LONGITUD_MINIMA_SECRET:
        raise RuntimeError(
            f"SECRET_KEY no configurada o demasiado corta (mínimo {LONGITUD_MINIMA_SECRET} caracteres). "
            "Defínela en el archivo .env; consulta .env.example."
        )
    return clave
