"""Carga datos de prueba FICTICIOS (usuarios, participantes, eventos, inscripciones y asistencia).

Uso (desde la carpeta backend):
    python db/seed.py              # crea la base si no existe y la llena (no toca una base con datos)
    python db/seed.py --reiniciar  # borra la base y la vuelve a llenar

La contraseña de las cuentas de prueba sale de SEED_PASSWORD (archivo .env). Si no está
definida, se genera una aleatoria y se muestra una sola vez. Nunca se guarda en el repositorio.
"""
import argparse
import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import auth, config, db, tiempo  # noqa: E402

USUARIOS = [
    ("Carlos Ruiz", "coordinacion@ejemplo.test", "coordinacion"),
    ("Ana Torres", "ana.torres@ejemplo.test", "organizador"),
    ("Luis Mora", "luis.mora@ejemplo.test", "organizador"),
]
PARTICIPANTES = [
    ("Laura Gómez", "estudiante"), ("Andrés Díaz", "estudiante"), ("María Pérez", "estudiante"),
    ("Sofía Herrera", "estudiante"), ("Camilo Rojas", "docente"), ("Valentina Cruz", "estudiante"),
    ("Julián Castro", "externo"), ("Daniela Ortiz", "estudiante"), ("Santiago Vega", "docente"),
    ("Paula Medina", "estudiante"), ("Felipe Rincón", "externo"), ("Natalia Pardo", "estudiante"),
]


def _contrasena() -> tuple[str, bool]:
    definida = os.getenv("SEED_PASSWORD")
    if definida:
        auth.validar_politica_password(definida)
        return definida, False
    while True:
        candidata = f"{secrets.token_urlsafe(9)}-{secrets.randbelow(900) + 100}"
        try:
            auth.validar_politica_password(candidata)
            return candidata, True
        except ValueError:
            continue


def _correo(nombre: str) -> str:
    base = nombre.lower().replace(" ", ".")
    for a, b in zip("áéíóúñ", "aeioun"):
        base = base.replace(a, b)
    return f"{base}@ejemplo.test"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reiniciar", action="store_true", help="borra la base de datos antes de cargar")
    args = parser.parse_args()

    if args.reiniciar:
        for sufijo in ("", "-wal", "-shm"):
            Path(str(config.DATABASE_PATH) + sufijo).unlink(missing_ok=True)
    db.iniciar_bd()

    with db.transaccion() as conn:
        if conn.execute("SELECT count(*) FROM usuarios").fetchone()[0]:
            print("La base de datos ya tiene datos. Usa --reiniciar para empezar de cero.")
            return
        password, generada = _contrasena()
        hash_pw = auth.hash_password(password)
        ids = {c: conn.execute("INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES (?, ?, ?, ?)",
                               (n, c, hash_pw, r)).lastrowid for n, c, r in USUARIOS}
        coord, ana, luis = ids["coordinacion@ejemplo.test"], ids["ana.torres@ejemplo.test"], ids["luis.mora@ejemplo.test"]

        pids = [conn.execute("INSERT INTO participantes (nombre_completo, correo, documento, rol, programa) "
                             "VALUES (?, ?, ?, ?, ?)",
                             (n, _correo(n), str(1000000001 + i), r, "Desarrollo de Software" if r == "estudiante" else None)).lastrowid
                for i, (n, r) in enumerate(PARTICIPANTES)]

        base = tiempo.ahora().replace(minute=0, second=0)

        def evento(org, titulo, tipo, dias, horas, cupo, estado, lugar, descripcion=None):
            inicio = base + timedelta(days=dias)
            return conn.execute(
                "INSERT INTO eventos (titulo, descripcion, tipo, inicio, fin, lugar, cupo, estado, organizador_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (titulo, descripcion, tipo, tiempo.a_texto(inicio), tiempo.a_texto(inicio + timedelta(hours=horas)),
                 lugar, cupo, estado, org)).lastrowid

        def inscribir(evento_id, indices, estado="activa", presentes=(), por=None):
            for i in indices:
                ins = conn.execute("INSERT INTO inscripciones (evento_id, participante_id, estado) VALUES (?, ?, ?)",
                                   (evento_id, pids[i], estado)).lastrowid
                if i in presentes:
                    conn.execute("INSERT INTO asistencias (inscripcion_id, estado, registrado_por, registrado_en) "
                                 "VALUES (?, 'presente', ?, ?)", (ins, por, tiempo.a_texto(base - timedelta(days=9))))

        html = evento(ana, "Taller de HTML", "taller", -10, 3, 20, "finalizado", "Sala de cómputo A",
                      "Fundamentos de HTML y CSS.")
        inscribir(html, range(8), presentes=range(6), por=ana)
        python = evento(ana, "Taller de Python", "taller", 2, 3, 30, "publicado", "Aula 301",
                        "Introducción práctica a Python.")
        inscribir(python, range(5))
        bd = evento(luis, "Seminario de Bases de Datos", "seminario", 3, 3, 3, "publicado", "Sala de cómputo B",
                    "Modelado relacional y SQL. Cupo reducido.")
        inscribir(bd, range(3))                                          # cupo lleno: sirve para probar CA-04
        ia = evento(luis, "Charla: Inteligencia Artificial", "conferencia", 4, 2, 80, "publicado",
                    "Auditorio principal", "Panorama actual de la IA.")
        inscribir(ia, range(10))
        excel = evento(ana, "Taller de Excel", "taller", 5, 2, 25, "cancelado", "Aula 205")
        inscribir(excel, range(2), estado="cancelada_por_evento")
        evento(luis, "Capacitación en Git y GitHub", "capacitacion", 7, 4, 25, "borrador", "Aula 301",
               "Control de versiones para equipos.")
        evento(coord, "Semana de la Ingeniería: apertura", "conferencia", 9, 2, 100, "publicado", "Auditorio principal")

    print(f"Base de datos lista en {config.DATABASE_PATH}")
    print(f"Usuarios de prueba: {', '.join(c for _, c, _ in USUARIOS)}")
    if generada:
        print(f"Contraseña de las cuentas de prueba (se muestra una sola vez): {password}")
    else:
        print("Contraseña de las cuentas de prueba: la definida en SEED_PASSWORD (.env)")


if __name__ == "__main__":
    main()
