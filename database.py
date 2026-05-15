"""Database setup for Saturno Shift Out.

La base de datos vive en AppData\\Local\\SaturnoShift\\ — FUERA del proyecto.
Esto garantiza que los datos de usuarios persistan aunque el código sea
actualizado, reemplazado o el proyecto sea borrado y recreado.

Ruta permanente: C:\\Users\\<usuario>\\AppData\\Local\\SaturnoShift\\saturno_shift.db
"""

import os
import aiosqlite
from pathlib import Path

# ── Ruta permanente fuera del proyecto ───────────────────────────────────────
# Usa APPDATA del usuario actual para que sea independiente del directorio
# del proyecto. Nunca toques este archivo manualmente — edita solo el código.
_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SaturnoShift"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = _DATA_DIR / "saturno_shift.db"


async def init_db() -> None:
    """Crea la tabla si no existe. Nunca destruye datos existentes."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # CREATE TABLE IF NOT EXISTS → nunca borra ni sobreescribe datos
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shift_out (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                local          TEXT    NOT NULL,
                id_colaborador TEXT    NOT NULL,
                shift_function TEXT    NOT NULL,
                semana         INTEGER NOT NULL,
                fecha_turno    TEXT    NOT NULL,
                observacion    TEXT,
                created_at     TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.commit()
