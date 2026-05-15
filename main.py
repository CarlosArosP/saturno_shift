"""FastAPI app – Saturno Shift Out.

Uses Jinja2 directly (avoids Starlette 1.0.0 / Jinja2 3.1 caching quirks).
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Optional

import aiosqlite
import openpyxl
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

import socket

from database import DB_PATH, init_db


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


SERVER_IP = _get_local_ip()
SERVER_PORT = 8502

# ── Jinja2 env (no Starlette wrapper) ────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render(template_name: str, **ctx) -> str:
    return _jinja_env.get_template(template_name).render(**ctx)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Saturno – Levantamiento Shift")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Validation data (mirrors Hoja2 from the Excel) ───────────────────────────
LOCALES = [93, 94, 96, 99, 120, 121, 456, 618, 670, 929]
SHIFT_FUNCTIONS = ["Experiencia de Pago", "Disponibilidad Apoyo"]
SEMANAS = list(range(19, 52))
FECHA_MIN = date.today().isoformat()
FECHA_MAX = "2027-12-31"

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


# ── Main page ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = render(
        "index.html",
        locales=LOCALES,
        shift_functions=SHIFT_FUNCTIONS,
        semanas=SEMANAS,
        fecha_min=FECHA_MIN,
        fecha_max=FECHA_MAX,
        server_ip=SERVER_IP,
        server_port=SERVER_PORT,
        db_path=str(DB_PATH),
    )
    return HTMLResponse(html)


# ── Submit shift entry ────────────────────────────────────────────────────────
@app.post("/submit", response_class=HTMLResponse)
async def submit(
    local: str = Form(...),
    id_colaborador: str = Form(...),
    shift_function: str = Form(...),
    semana: int = Form(...),
    fecha_turno: str = Form(...),
    observacion: str = Form(""),
) -> HTMLResponse:
    errors: list[str] = []
    if str(local) not in [str(l) for l in LOCALES]:
        errors.append("Local inválido.")
    if shift_function not in SHIFT_FUNCTIONS:
        errors.append("SHIFT_FUNCTION inválida.")
    if semana not in SEMANAS:
        errors.append("Semana inválida.")
    try:
        fd = date.fromisoformat(fecha_turno)
        if not (date.fromisoformat(FECHA_MIN) <= fd <= date.fromisoformat(FECHA_MAX)):
            errors.append("Fecha fuera de rango permitido.")
    except ValueError:
        errors.append("Fecha inválida.")

    if errors:
        return HTMLResponse(_alert("error", " / ".join(errors)), status_code=422)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO shift_out
               (local, id_colaborador, shift_function, semana, fecha_turno, observacion)
               VALUES (?,?,?,?,?,?)""",
            (local, id_colaborador.strip(), shift_function, semana, fecha_turno, observacion.strip()),
        )
        await db.commit()

    return HTMLResponse(_alert("success", "✅ Registro guardado exitosamente."))


# ── Consolidated data (HTMX partial) ─────────────────────────────────────────
@app.get("/consolidado", response_class=HTMLResponse)
async def consolidado(
    semana: Optional[int] = Query(None),
    local: Optional[str] = Query(None),
    shift_function: Optional[str] = Query(None),
    fecha_turno: Optional[str] = Query(None),
) -> HTMLResponse:
    rows = await _query_rows(semana, local, shift_function, fecha_turno)
    html = render("partials/tabla.html", rows=rows)
    return HTMLResponse(html)


# ── Excel export ──────────────────────────────────────────────────────────────
@app.get("/export")
async def export_excel(
    semana: Optional[int] = Query(None),
    local: Optional[str] = Query(None),
    shift_function: Optional[str] = Query(None),
    fecha_turno: Optional[str] = Query(None),
) -> StreamingResponse:
    rows = await _query_rows(semana, local, shift_function, fecha_turno)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Shift Out"
    ws.append(["ID", "Local", "ID Colaborador", "SHIFT_FUNCTION", "Semana", "Fecha Turno", "Observación", "Fecha Registro"])
    for row in rows:
        ws.append([row["id"], row["local"], row["id_colaborador"],
                   row["shift_function"], row["semana"],
                   row["fecha_turno"], row["observacion"], row["created_at"]])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=shift_out_export.xlsx"},
    )


# ── Delete a row ────────────────────────────────────────────────────────────
@app.delete("/delete/{row_id}", response_class=HTMLResponse)
async def delete_row(row_id: int) -> HTMLResponse:
    async with aiosqlite.connect(DB_PATH) as db:
        result = await db.execute("DELETE FROM shift_out WHERE id = ?", (row_id,))
        await db.commit()
    if result.rowcount == 0:
        return HTMLResponse("", status_code=404)
    return HTMLResponse("")   # HTMX outerHTML swap → removes the <tr>


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _query_rows(
    semana: Optional[int],
    local: Optional[str],
    shift_function: Optional[str],
    fecha_turno: Optional[str],
) -> list:
    sql = "SELECT * FROM shift_out WHERE 1=1"
    params: list = []
    if semana:
        sql += " AND semana = ?"
        params.append(semana)
    if local:
        sql += " AND local = ?"
        params.append(local)
    if shift_function:
        sql += " AND shift_function = ?"
        params.append(shift_function)
    if fecha_turno:
        sql += " AND fecha_turno = ?"
        params.append(fecha_turno)
    sql += " ORDER BY created_at DESC"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        return await cursor.fetchall()


def _alert(kind: str, message: str) -> str:
    colors = {
        "success": "bg-green-50 border-green-400 text-green-800",
        "error":   "bg-red-50 border-red-400 text-red-800",
    }
    cls = colors.get(kind, colors["error"])
    return (
        f'<div id="form-feedback" class="border-l-4 p-4 rounded-lg {cls} '
        f'text-sm font-medium">{message}</div>'
    )
