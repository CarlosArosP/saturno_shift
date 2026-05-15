"""migrate_to_turso.py — Migra datos locales de SQLite → Turso.

Uso (una sola vez, después de configurar el .env):
    python migrate_to_turso.py

El script lee la DB local en AppData y sube cada fila a Turso.
Es idempotente: no crea duplicados si ya existe la fila con el mismo ID.
"""

import asyncio
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOCAL_DB = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SaturnoShift" / "saturno_shift.db"


async def migrate() -> None:
    import database as db  # usa las credenciales del .env

    if not LOCAL_DB.exists():
        print(f"No se encontró DB local en: {LOCAL_DB}")
        print("Nada que migrar.")
        return

    con = sqlite3.connect(LOCAL_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM shift_out ORDER BY id").fetchall()
    con.close()

    if not rows:
        print("DB local vacía, nada que migrar.")
        return

    print(f"Migrando {len(rows)} registro(s)...")
    await db.init_db()

    ok = 0
    for row in rows:
        try:
            await db.run(
                """INSERT OR IGNORE INTO shift_out
                   (id, local, id_colaborador, shift_function,
                    semana, fecha_turno, observacion, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                [row["id"], row["local"], row["id_colaborador"],
                 row["shift_function"], row["semana"],
                 row["fecha_turno"], row["observacion"], row["created_at"]],
            )
            ok += 1
            print(f"  ✅ ID {row['id']} – Local {row['local']} – {row['id_colaborador']}")
        except Exception as e:
            print(f"  ❌ ID {row['id']} – Error: {e}")

    print(f"\n✅ Migración completa: {ok}/{len(rows)} registros subidos a Turso.")


if __name__ == "__main__":
    asyncio.run(migrate())
