"""Prepara un evento EN CURSO (datos ficticios) para demostrar el registro de asistencia en vivo.

La asistencia solo se puede registrar desde que un evento inicia, y la aplicación no permite crear
eventos en el pasado; por eso este script de datos de prueba lo inserta directamente.

Uso (desde la carpeta backend, después de seed.py):  python db/preparar_demo.py
"""
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, tiempo  # noqa: E402

TITULO = "Demostración en vivo: Taller de APIs"
INSCRITOS = ("laura.gomez@ejemplo.test", "andres.diaz@ejemplo.test", "maria.perez@ejemplo.test")


def main() -> None:
    db.iniciar_bd()
    with db.transaccion() as conn:
        organizador = conn.execute("SELECT id FROM usuarios WHERE correo = 'ana.torres@ejemplo.test'").fetchone()
        if not organizador:
            print("Primero carga los datos de prueba:  python db/seed.py --reiniciar")
            return
        ahora = tiempo.ahora()
        if conn.execute("SELECT 1 FROM eventos WHERE titulo = ? AND estado = 'publicado' AND fin > ?",
                        (TITULO, tiempo.a_texto(ahora))).fetchone():
            print("Ya hay un evento de demostración en curso. No se creó otro.")
            return
        inicio = (ahora - timedelta(minutes=5)).replace(second=0)
        evento = conn.execute(
            "INSERT INTO eventos (titulo, descripcion, tipo, inicio, fin, lugar, cupo, estado, organizador_id) "
            "VALUES (?, 'Evento preparado para la sustentación.', 'taller', ?, ?, 'Aula 301', 5, 'publicado', ?)",
            (TITULO, tiempo.a_texto(inicio), tiempo.a_texto(inicio + timedelta(hours=4)), organizador["id"])).lastrowid
        total = 0
        for correo in INSCRITOS:
            persona = conn.execute("SELECT id FROM participantes WHERE correo = ?", (correo,)).fetchone()
            if persona:
                conn.execute("INSERT INTO inscripciones (evento_id, participante_id) VALUES (?, ?)",
                             (evento, persona["id"]))
                total += 1
    fin_local = (inicio + timedelta(hours=4)).astimezone(tiempo.BOGOTA)
    print(f"Listo: evento {evento} '{TITULO}' en curso hasta las {fin_local:%H:%M}, con {total} inscritos y cupo 5.")
    print(f"Asistencia: http://127.0.0.1:8000/asistencia.html?id={evento}  (ingresa como Ana Torres o coordinación)")


if __name__ == "__main__":
    main()
