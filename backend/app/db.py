"""Acceso a SQLite. Cada operación usa su propia conexión (los endpoints corren en hilos)."""
import sqlite3
from contextlib import contextmanager

from . import config


def conectar() -> sqlite3.Connection:
    # isolation_level=None: las transacciones se controlan explícitamente.
    conn = sqlite3.connect(config.DATABASE_PATH, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@contextmanager
def lectura():
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaccion():
    """BEGIN IMMEDIATE: toma el bloqueo de escritura desde el inicio, de modo que
    verificar el cupo y guardar la inscripción es una operación atómica (RNF-06).
    Ante cualquier excepción se revierte todo."""
    conn = conectar()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def iniciar_bd() -> None:
    """Crea tablas, restricciones, índices y triggers si no existen (idempotente)."""
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = conectar()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(config.SCHEMA_SQL.read_text(encoding="utf-8"))
    finally:
        conn.close()
