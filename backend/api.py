"""
API FastAPI de problemas de suministro (AEMPS).
Cumple el contrato de docs/API.md (version 1.1). Solo LEE de backend/aemps.db;
los datos se cargan con backend/importar.py.

ARRANCAR (desde la raiz del repo, con el entorno virtual activado):

    source venv/bin/activate
    pip install -r backend/requirements.txt
    cd backend
    uvicorn api:app --reload --port 8000

Documentacion interactiva automatica: http://localhost:8000/docs
"""

import math
import os
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
RUTA_DB = BASE / "aemps.db"
MADRID = ZoneInfo("Europe/Madrid")

# Lee backend/.env (si existe). Ahi va CORS_ORIGINS; no hay claves en el codigo.
load_dotenv(BASE / ".env")

ORIGENES_POR_DEFECTO = (
    "http://localhost:5500,http://127.0.0.1:5500,"
    "http://localhost:8080,http://127.0.0.1:8080"
)

app = FastAPI(title="Problemas de suministro AEMPS", version="1.1")

# CORS: el navegador solo deja al frontend llamar a la API si el origen esta en la lista.
origenes = [o.strip() for o in os.getenv("CORS_ORIGINS", ORIGENES_POR_DEFECTO).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


# ---------------------------------------------------------------- utilidades

def hoy_madrid():
    """Fecha de hoy en Madrid como 'YYYY-MM-DD' (no usamos date('now') de SQLite: es UTC)."""
    return datetime.now(MADRID).strftime("%Y-%m-%d")


def normalizar(texto):
    """Minusculas y sin tildes, igual que hace el importador con nombre_busqueda."""
    sin = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def get_db():
    """
    Dependencia de FastAPI: abre la base en modo SOLO LECTURA para cada peticion
    y la cierra al terminar. Si el archivo no existe -> 503 (contrato).
    """
    if not RUTA_DB.exists():
        raise HTTPException(503, "Base de datos no disponible. Ejecuta primero la importación.")
    con = sqlite3.connect(f"file:{RUTA_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row  # permite leer columnas por nombre
    try:
        yield con
    finally:
        con.close()


# Expresiones SQL de las reglas de la seccion 5 del contrato.
# estado: activo solo si la AEMPS lo marca activo Y sigue apareciendo en CIMA.
SQL_ACTIVO = "(activo = 1 AND en_origen = 1)"
# vencido: tiene fecha de fin y ya paso (el parametro ? es la fecha de hoy).
SQL_VENCIDO = "(fecha_fin IS NOT NULL AND fecha_fin < ?)"


def fila_a_dict(f, hoy, con_actualizado=False):
    """Convierte una fila de la base en el JSON del contrato."""
    d = {
        "cn": f["cn"],
        "nombre": f["nombre"],
        "tipo_problema": f["tipo_problema"],
        "fecha_inicio": f["fecha_inicio"],
        "fecha_fin": f["fecha_fin"],
        "estado": "activo" if (f["activo"] == 1 and f["en_origen"] == 1) else "resuelto",
        "vencido": f["fecha_fin"] is not None and f["fecha_fin"] < hoy,
        "observaciones": f["observaciones"],
    }
    if con_actualizado:
        d["actualizado_en"] = f["actualizado_en"]
    return d


def ultima_importacion(con):
    """Fecha de la importacion mas reciente (None si la tabla esta vacia)."""
    return con.execute("SELECT MAX(actualizado_en) FROM problemas_suministro").fetchone()[0]


# ------------------------------------------------------------- manejo de errores

@app.exception_handler(sqlite3.OperationalError)
async def error_base(request: Request, exc: sqlite3.OperationalError):
    # Tipico: el archivo existe pero la tabla no (importacion sin hacer).
    return JSONResponse(
        {"detail": "Base de datos no disponible. Ejecuta primero la importación."}, status_code=503
    )


@app.exception_handler(Exception)
async def error_inesperado(request: Request, exc: Exception):
    return JSONResponse({"detail": "Error interno del servidor"}, status_code=500)


# ------------------------------------------------------------------- endpoints

@app.get("/api/salud")
def salud(con: sqlite3.Connection = Depends(get_db)):
    total = con.execute("SELECT COUNT(*) FROM problemas_suministro").fetchone()[0]
    return {"estado": "ok", "total_registros": total, "ultima_importacion": ultima_importacion(con)}


@app.get("/api/problemas")
def listar(
    q: Optional[str] = Query(None, min_length=2),
    estado: Literal["activo", "resuelto", "todos"] = "activo",
    tipo: Optional[int] = None,
    ocultar_vencidos: bool = False,
    orden: Literal["fecha_inicio_desc", "fecha_inicio_asc", "nombre"] = "fecha_inicio_desc",
    pagina: int = Query(1, ge=1),
    tamanio: int = Query(20, ge=1, le=100),
    con: sqlite3.Connection = Depends(get_db),
):
    hoy = hoy_madrid()
    condiciones, params = [], []

    if q:
        # Busca en el nombre normalizado y en el cn. Escapamos % y _ para que
        # cuenten como texto normal y no como comodines de LIKE.
        texto = normalizar(q.strip()).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        condiciones.append("(nombre_busqueda LIKE ? ESCAPE '\\' OR cn LIKE ? ESCAPE '\\')")
        params += [f"%{texto}%", f"%{texto}%"]
    if estado == "activo":
        condiciones.append(SQL_ACTIVO)
    elif estado == "resuelto":
        condiciones.append(f"NOT {SQL_ACTIVO}")
    if tipo is not None:
        condiciones.append("tipo_problema = ?")
        params.append(tipo)
    if ocultar_vencidos:
        condiciones.append(f"NOT {SQL_VENCIDO}")
        params.append(hoy)

    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    # El orden va por una lista fija (nunca se mete texto del usuario en el SQL).
    orden_sql = {
        "fecha_inicio_desc": "fecha_inicio DESC, cn",
        "fecha_inicio_asc": "fecha_inicio ASC, cn",
        "nombre": "nombre_busqueda, cn",
    }[orden]

    total = con.execute(f"SELECT COUNT(*) FROM problemas_suministro {donde}", params).fetchone()[0]
    filas = con.execute(
        f"SELECT * FROM problemas_suministro {donde} ORDER BY {orden_sql} LIMIT ? OFFSET ?",
        params + [tamanio, (pagina - 1) * tamanio],
    ).fetchall()

    return {
        "total": total,
        "pagina": pagina,
        "tamanio": tamanio,
        "total_paginas": math.ceil(total / tamanio),
        "resultados": [fila_a_dict(f, hoy) for f in filas],
    }


@app.get("/api/problemas/{cn}")
def detalle(cn: str, con: sqlite3.Connection = Depends(get_db)):
    f = con.execute("SELECT * FROM problemas_suministro WHERE cn = ?", (cn,)).fetchone()
    if f is None:
        raise HTTPException(404, f"No existe ningún problema de suministro con cn {cn}")
    return fila_a_dict(f, hoy_madrid(), con_actualizado=True)


@app.get("/api/resumen")
def resumen(con: sqlite3.Connection = Depends(get_db)):
    total, activos = con.execute(
        f"SELECT COUNT(*), COALESCE(SUM({SQL_ACTIVO}), 0) FROM problemas_suministro"
    ).fetchone()
    por_tipo = con.execute(
        f"""SELECT tipo_problema, COUNT(*) AS total FROM problemas_suministro
            WHERE {SQL_ACTIVO} GROUP BY tipo_problema ORDER BY total DESC, tipo_problema"""
    ).fetchall()
    return {
        "total": total,
        "activos": activos,
        "resueltos": total - activos,
        "por_tipo": [{"tipo_problema": r["tipo_problema"], "total": r["total"]} for r in por_tipo],
        "ultima_importacion": ultima_importacion(con),
    }


class PeticionChat(BaseModel):
    mensaje: str


@app.post("/api/chat")
def chat(peticion: PeticionChat):
    # Ruta reservada: el chatbot llegara en una fase posterior.
    raise HTTPException(501, "El chatbot todavía no está disponible")
