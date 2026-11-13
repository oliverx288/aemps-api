#!/usr/bin/env python3
"""
Importa los problemas de suministro de la AEMPS (CIMA) a SQLite.

USO (desde la raiz del repo, con el entorno virtual activado):

    source venv/bin/activate
    python backend/importar.py

Se puede ejecutar todas las veces que quieras: no crea duplicados, porque cada
medicamento se identifica por su codigo nacional (cn).

Que hace, paso a paso:
  1. Descarga TODAS las paginas de la API de CIMA (200 resultados por pagina).
  2. Solo si la descarga ha ido bien, abre la base backend/aemps.db.
  3. En una transaccion: pone en_origen = 0 en todas las filas y luego hace
     INSERT ... ON CONFLICT(cn) DO UPDATE con cada registro (en_origen = 1).
     Las filas que quedan en 0 ya no estan en CIMA (no se borran: es el historico).
  4. Si algo falla en medio, la transaccion se deshace y la base queda como estaba.

Solo usa la libreria estandar de Python (no hace falta instalar nada).
"""

import json
import sqlite3
import ssl
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://cima.aemps.es/cima/rest/psuministro"
# La base de datos vive junto a este script: backend/aemps.db
RUTA_DB = Path(__file__).resolve().parent / "aemps.db"
MADRID = ZoneInfo("Europe/Madrid")

# Esquema segun docs/API.md (seccion 2).
ESQUEMA = """
CREATE TABLE IF NOT EXISTS problemas_suministro (
    cn                 TEXT    PRIMARY KEY,
    nombre             TEXT    NOT NULL,
    nombre_busqueda    TEXT    NOT NULL,
    tipo_problema      INTEGER NOT NULL,
    fecha_inicio       TEXT    NOT NULL,
    fecha_fin          TEXT,
    observaciones      TEXT    NOT NULL DEFAULT '',
    activo             INTEGER NOT NULL DEFAULT 1,
    en_origen          INTEGER NOT NULL DEFAULT 1,
    actualizado_en     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_problemas_fecha_inicio ON problemas_suministro (fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_problemas_fecha_fin    ON problemas_suministro (fecha_fin);
CREATE INDEX IF NOT EXISTS idx_problemas_tipo         ON problemas_suministro (tipo_problema);
CREATE INDEX IF NOT EXISTS idx_problemas_en_origen    ON problemas_suministro (en_origen);
"""

# Si el cn ya existe, actualiza la fila; si no, la crea.
UPSERT = """
INSERT INTO problemas_suministro
    (cn, nombre, nombre_busqueda, tipo_problema, fecha_inicio, fecha_fin,
     observaciones, activo, en_origen, actualizado_en)
VALUES
    (:cn, :nombre, :nombre_busqueda, :tipo_problema, :fecha_inicio, :fecha_fin,
     :observaciones, :activo, 1, :actualizado_en)
ON CONFLICT(cn) DO UPDATE SET
    nombre          = excluded.nombre,
    nombre_busqueda = excluded.nombre_busqueda,
    tipo_problema   = excluded.tipo_problema,
    fecha_inicio    = excluded.fecha_inicio,
    fecha_fin       = excluded.fecha_fin,
    observaciones   = excluded.observaciones,
    activo          = excluded.activo,
    en_origen       = 1,
    actualizado_en  = excluded.actualizado_en
"""


def normalizar(texto):
    """Minusculas y sin tildes: 'Ácido' -> 'acido' (para las busquedas)."""
    sin_tildes = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.lower()


def ms_a_fecha(ms):
    """Milisegundos epoch -> 'YYYY-MM-DD' en hora de Madrid. None si no hay valor."""
    if ms is None or ms == "":
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=MADRID).strftime("%Y-%m-%d")


def contexto_ssl():
    """
    Contexto HTTPS con verificacion de certificados (nunca se desactiva).
    El Python de python.org en macOS no trae certificados raiz y falla con
    CERTIFICATE_VERIFY_FAILED; en ese caso usamos los del sistema (/etc/ssl/cert.pem).
    """
    sistema = Path("/etc/ssl/cert.pem")
    if sistema.exists() and not Path(ssl.get_default_verify_paths().openssl_cafile).exists():
        return ssl.create_default_context(cafile=str(sistema))
    return ssl.create_default_context()


def pedir_json(url):
    """Descarga una URL y devuelve el JSON ya convertido en diccionario."""
    peticion = urllib.request.Request(url, headers={"User-Agent": "aemps-importador"})
    with urllib.request.urlopen(peticion, timeout=30, context=contexto_ssl()) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def descargar_todo():
    """Recorre todas las paginas y devuelve la lista de registros (sin cn repetidos)."""
    registros = {}  # clave = cn, asi un cn repetido no puede entrar dos veces
    pagina = 1
    while True:
        datos = pedir_json(f"{URL}?pagina={pagina}")
        total = datos["totalFilas"]
        tamanio = datos["tamanioPagina"]
        for r in datos["resultados"]:
            registros[str(r["cn"])] = r
        print(f"  pagina {pagina}: {len(datos['resultados'])} registros")
        if pagina * tamanio >= total:
            break
        pagina += 1
    # Comprobacion de seguridad: si no coincide con lo que anuncia CIMA, no seguimos.
    if len(registros) != total:
        raise RuntimeError(f"CIMA anuncia {total} filas pero se han leido {len(registros)}")
    return list(registros.values())


def a_fila(r, ahora):
    """Convierte un registro de CIMA en los valores de nuestra tabla."""
    nombre = r["nombre"]
    return {
        "cn": str(r["cn"]),
        "nombre": nombre,
        "nombre_busqueda": normalizar(nombre),
        "tipo_problema": int(r["tipoProblemaSuministro"]),  # numero tal cual
        "fecha_inicio": ms_a_fecha(r["fini"]),
        "fecha_fin": ms_a_fecha(r.get("ffin")),  # None (NULL) si no existe
        "observaciones": r.get("observ") or "",
        "activo": 1 if r.get("activo", True) else 0,  # tal cual viene de la AEMPS
        "actualizado_en": ahora,
    }


def main():
    print("Descargando de CIMA...")
    registros = descargar_todo()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    filas = [a_fila(r, ahora) for r in registros]

    con = sqlite3.connect(RUTA_DB)
    try:
        con.executescript(ESQUEMA)  # crea tabla e indices si no existen
        # "with con" = transaccion: si hay un error, se hace rollback automatico.
        with con:
            con.execute("UPDATE problemas_suministro SET en_origen = 0")
            con.executemany(UPSERT, filas)
        total, fuera = con.execute(
            "SELECT COUNT(*), SUM(en_origen = 0) FROM problemas_suministro"
        ).fetchone()
    finally:
        con.close()

    print(f"Importados {len(filas)} registros. Filas en la base: {total}. "
          f"Ya no estan en CIMA (en_origen=0): {fuera or 0}.")
    print(f"Base de datos: {RUTA_DB}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # mensaje claro en vez de un traceback largo
        print(f"ERROR: la importacion ha fallado y la base no se ha modificado: {e}", file=sys.stderr)
        sys.exit(1)
