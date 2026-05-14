"""Database setup and helpers for Saturno Shift app."""

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "saturno_shift.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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
