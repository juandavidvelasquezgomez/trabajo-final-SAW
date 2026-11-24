"""Manejo de fechas: se guarda en UTC y se muestra en hora de Colombia (RNF-10).

Colombia no tiene horario de verano, por lo que UTC-5 es constante todo el año.
`ahora()` es el único reloj de la aplicación: las pruebas lo reemplazan.
"""
from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc
BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")
FORMATO_BD = "%Y-%m-%dT%H:%M:%SZ"


def ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def a_texto(dt: datetime) -> str:
    """datetime con zona horaria -> texto UTC como se guarda en la base de datos."""
    return dt.astimezone(UTC).strftime(FORMATO_BD)


def de_texto(texto: str) -> datetime:
    return datetime.strptime(texto, FORMATO_BD).replace(tzinfo=UTC)


def a_bogota_iso(texto: str) -> str:
    """Texto UTC de la base de datos -> ISO 8601 con offset de Colombia."""
    return de_texto(texto).astimezone(BOGOTA).isoformat()


def proxima_medianoche_bogota(referencia: datetime) -> datetime:
    """Próxima 00:00 hora de Colombia (en UTC) posterior a `referencia` (RN-14)."""
    local = referencia.astimezone(BOGOTA)
    manana = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return manana.astimezone(UTC)


def inicio_del_dia(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=BOGOTA).astimezone(UTC)


def fin_del_dia(d: date) -> datetime:
    return inicio_del_dia(d) + timedelta(days=1) - timedelta(seconds=1)
