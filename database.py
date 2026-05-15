"""Turso HTTP client — SQLite en la nube para Saturno Shift Out.

Documentación: https://docs.turso.tech/sdk/http/reference
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


# ── Credenciales (carga en runtime, no en import) ─────────────────────────────
def _env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        raise RuntimeError(
            f"Variable '{key}' no configurada. "
            "Copia .env.example → .env y rellena tus credenciales de Turso."
        )
    return val


# ── Row: acceso por nombre o por índice (compat. con templates Jinja2) ────────
class Row:
    __slots__ = ("_data", "_vals")

    def __init__(self, cols: list[str], vals: list[Any]) -> None:
        self._data = dict(zip(cols, vals))
        self._vals = vals

    def __getitem__(self, key: str | int) -> Any:
        return self._vals[key] if isinstance(key, int) else self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def keys(self) -> list[str]:
        return list(self._data.keys())


# ── Conversores de tipos Turso ↔ Python ───────────────────────────────────────
def _from_cell(cell: dict) -> Any:
    t, v = cell.get("type", "null"), cell.get("value")
    if t == "null" or v is None:
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    return v  # text / blob → str


def _to_arg(v: Any) -> dict:
    if v is None:
        return {"type": "null", "value": None}
    if isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": str(v)}
    return {"type": "text", "value": str(v)}


# ── Ejecutor base ─────────────────────────────────────────────────────────────
async def _pipeline(sql: str, args: list | None = None) -> dict:
    url   = _env("TURSO_URL")
    token = _env("TURSO_AUTH_TOKEN")
    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": sql,
                    "args": [_to_arg(a) for a in (args or [])],
                },
            },
            {"type": "close"},
        ]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{url}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
    return resp.json()["results"][0]["response"]["result"]


# ── API pública ───────────────────────────────────────────────────────────────
async def query(sql: str, args: list | None = None) -> list[Row]:
    """SELECT → lista de Row."""
    result = await _pipeline(sql, args)
    cols = [c["name"] for c in result["cols"]]
    return [Row(cols, [_from_cell(cell) for cell in row]) for row in result["rows"]]


async def run(sql: str, args: list | None = None) -> int:
    """INSERT / UPDATE / DELETE → filas afectadas."""
    result = await _pipeline(sql, args)
    return result.get("affected_row_count", 0)


async def init_db() -> None:
    """Crea la tabla base y agrega columnas nuevas si no existen."""
    await run("""
        CREATE TABLE IF NOT EXISTS shift_out (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            local               TEXT    NOT NULL,
            id_colaborador      TEXT    NOT NULL,
            shift_function      TEXT    NOT NULL,
            semana              INTEGER NOT NULL,
            fecha_turno         TEXT,
            observacion         TEXT,
            created_at          TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','-4 hours'))
        )
    """)
    # Columnas nuevas — idempotente: ignora error si ya existen
    for col_sql in [
        "ALTER TABLE shift_out ADD COLUMN fecha_inicio      TEXT",
        "ALTER TABLE shift_out ADD COLUMN fecha_termino     TEXT",
        "ALTER TABLE shift_out ADD COLUMN observacion_tipo  TEXT",
        "ALTER TABLE shift_out ADD COLUMN observacion_detalle TEXT",
    ]:
        try:
            await run(col_sql)
        except Exception:
            pass  # columna ya existe
