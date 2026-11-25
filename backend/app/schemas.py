"""Modelos de entrada. Validan tipos, formatos y rangos y NORMALIZAN los datos antes de
tocar la base de datos (correos en minúscula, documentos sin separadores, espacios
colapsados...). Se rechazan campos desconocidos para evitar asignaciones no previstas."""
import re
import unicodedata
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from . import config, tiempo

TIPOS_EVENTO = ("conferencia", "taller", "seminario", "capacitacion")
ROLES_PARTICIPANTE = ("estudiante", "docente", "externo")


# ------------------------------------------------------------------ texto básico
def _linea(valor: str) -> str:
    valor = unicodedata.normalize("NFC", valor)
    if any(not c.isprintable() and not c.isspace() for c in valor):
        raise ValueError("Contiene caracteres no permitidos.")
    return " ".join(valor.split())  # recorta y colapsa espacios, tabulaciones y saltos


def _texto(minimo: int, maximo: int):
    def validar(valor: str) -> str:
        valor = _linea(valor)
        if not minimo <= len(valor) <= maximo:
            raise ValueError(f"Debe tener entre {minimo} y {maximo} caracteres.")
        return valor
    return Annotated[str, Field(max_length=maximo * 4), AfterValidator(validar)]


Titulo = _texto(3, 150)
Lugar = _texto(2, 200)
Programa = _texto(2, 100)

_RE_NOMBRE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿÑñ][A-Za-zÀ-ÖØ-öø-ÿÑñ .'-]*$")


def _nombre(valor: str) -> str:
    valor = _linea(valor)
    if not 3 <= len(valor) <= 100:
        raise ValueError("Debe tener entre 3 y 100 caracteres.")
    if not _RE_NOMBRE.match(valor):
        raise ValueError("Solo puede contener letras, espacios, puntos, apóstrofes y guiones.")
    return valor


NombrePersona = Annotated[str, Field(max_length=400), AfterValidator(_nombre)]


def _descripcion(valor: str) -> str | None:
    valor = unicodedata.normalize("NFC", valor).strip()
    if any(not c.isprintable() and c not in "\n\t" for c in valor):
        raise ValueError("Contiene caracteres no permitidos.")
    if len(valor) > 2000:
        raise ValueError("Debe tener como máximo 2000 caracteres.")
    return valor or None


Descripcion = Annotated[str, Field(max_length=8000), AfterValidator(_descripcion)]


# ----------------------------------------------------------- correo y documento
_RE_CORREO = re.compile(
    r"^[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")


def normalizar_correo(valor: str) -> str:
    valor = valor.strip().lower()
    local = valor.split("@")[0]
    if (len(valor) > 254 or len(local) > 64 or ".." in local or local.startswith(".")
            or local.endswith(".") or not _RE_CORREO.match(valor)):
        raise ValueError("Correo electrónico inválido.")
    return valor


def normalizar_documento(valor: str) -> str:
    valor = re.sub(r"[\s.\-]", "", valor).upper()
    if not re.fullmatch(r"[A-Z0-9]{5,20}", valor):
        raise ValueError("El documento debe tener entre 5 y 20 letras o números.")
    return valor


Correo = Annotated[str, Field(max_length=400), AfterValidator(normalizar_correo)]
Documento = Annotated[str, Field(max_length=60), AfterValidator(normalizar_documento)]


# ------------------------------------------------------------- números y fechas
Cupo = Annotated[int, Field(strict=True, ge=1, le=config.CUPO_MAXIMO)]
IdEntero = Annotated[int, Field(strict=True, ge=1, le=2147483647)]

_RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$")


def _fecha_hora(valor) -> datetime:
    """Texto ISO 8601 -> datetime en UTC. Sin zona horaria se asume hora de Colombia."""
    if not isinstance(valor, str):
        raise ValueError("Debe ser un texto con fecha y hora (AAAA-MM-DDTHH:MM:SS).")
    valor = valor.strip()
    if not _RE_FECHA.match(valor):
        raise ValueError("Fecha y hora inválidas. Formato: AAAA-MM-DDTHH:MM:SS, "
                         "por ejemplo 2026-12-10T14:00:00-05:00.")
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("La fecha u hora indicada no existe en el calendario.")
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=tiempo.BOGOTA)
    fecha = fecha.astimezone(tiempo.UTC).replace(microsecond=0)
    if not 2020 <= fecha.year <= 2100:
        raise ValueError("El año debe estar entre 2020 y 2100.")
    return fecha


FechaHora = Annotated[datetime, BeforeValidator(_fecha_hora)]


def _url(valor: str) -> str:
    valor = valor.strip()
    partes = urlparse(valor)
    if (len(valor) > 500 or partes.scheme not in ("http", "https") or not partes.netloc
            or any(c.isspace() for c in valor)):
        raise ValueError("Debe ser una dirección web válida que empiece por http:// o https://.")
    return valor


UrlImagen = Annotated[str, Field(max_length=2000), AfterValidator(_url)]


# --------------------------------------------------------------------- modelos
class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginIn(Base):
    correo: Correo
    password: Annotated[str, Field(min_length=1, max_length=128)]


class EventoCrear(Base):
    titulo: Titulo
    descripcion: Descripcion | None = None
    tipo: Literal[TIPOS_EVENTO]
    inicio: FechaHora
    fin: FechaHora
    lugar: Lugar
    cupo: Cupo
    imagen_url: UrlImagen | None = None
    organizador_id: IdEntero | None = None


class EventoEditar(Base):
    titulo: Titulo | None = None
    descripcion: Descripcion | None = None
    tipo: Literal[TIPOS_EVENTO] | None = None
    inicio: FechaHora | None = None
    fin: FechaHora | None = None
    lugar: Lugar | None = None
    cupo: Cupo | None = None
    imagen_url: UrlImagen | None = None
    organizador_id: IdEntero | None = None

    @model_validator(mode="after")
    def _al_menos_un_campo(self):
        if not self.model_fields_set:
            raise ValueError("Indica al menos un campo para modificar.")
        for campo in self.model_fields_set:
            if getattr(self, campo) is None and campo not in ("descripcion", "imagen_url"):
                raise ValueError(f"El campo '{campo}' no puede ser nulo.")
        return self


class EstadoEventoIn(Base):
    estado: Literal["publicado", "cancelado"]


class ParticipanteIn(Base):
    nombre_completo: NombrePersona
    correo: Correo
    documento: Documento
    rol: Literal[ROLES_PARTICIPANTE]
    programa: Programa | None = None


class CancelarInscripcionIn(Base):
    correo: Correo
    documento: Documento


class IdentificacionIn(Base):
    """Identifica a un participante sin cuenta. Se envía en el cuerpo (POST), no en la dirección."""
    correo: Correo
    documento: Documento


class InscripcionEstadoIn(Base):
    estado: Literal["cancelada"]


class AsistenciaIn(Base):
    estado: Literal["presente", "ausente"]


class AsistenciaLoteIn(Base):
    inscripcion_ids: Annotated[list[IdEntero], Field(min_length=1, max_length=500)]
    estado: Literal["presente", "ausente"] = "presente"

    @model_validator(mode="after")
    def _sin_repetidos(self):
        if len(set(self.inscripcion_ids)) != len(self.inscripcion_ids):
            raise ValueError("La lista contiene inscripciones repetidas.")
        return self
