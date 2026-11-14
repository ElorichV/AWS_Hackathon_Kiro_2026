"""
URBIA CDMX — Capa de base de datos (SQLite para desarrollo)
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "urbia.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reportes (
            id TEXT PRIMARY KEY,
            fuente TEXT,
            origen TEXT DEFAULT 'demo',
            fecha_reporte TEXT,
            alcaldia TEXT,
            colonia TEXT,
            calle TEXT,
            categoria TEXT,
            subcategoria TEXT,
            descripcion TEXT,
            latitud REAL,
            longitud REAL,
            coords_confirmadas INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'abierto',
            es_emergencia INTEGER DEFAULT 0,
            incidente_id TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidentes (
            id TEXT PRIMARY KEY,
            tipo TEXT,
            categoria TEXT,
            alcaldia TEXT,
            colonia TEXT,
            calle TEXT,
            latitud REAL,
            longitud REAL,
            total_reportes INTEGER DEFAULT 1,
            estado TEXT DEFAULT 'abierto',
            es_emergencia INTEGER DEFAULT 0,
            fecha_primer_reporte TEXT,
            fecha_ultimo_reporte TEXT,
            puntaje_S REAL DEFAULT 0,
            puntaje_D REAL DEFAULT 0,
            puntaje_M REAL DEFAULT 0,
            puntaje_A REAL DEFAULT 0,
            puntaje_R REAL DEFAULT 0,
            puntaje_total REAL DEFAULT 0,
            nivel_prioridad TEXT DEFAULT 'baja',
            confianza REAL DEFAULT 1.0,
            justificacion TEXT,
            origen TEXT DEFAULT 'demo',
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fuentes (
            id TEXT PRIMARY KEY,
            nombre TEXT,
            url TEXT,
            licencia TEXT,
            fecha_cobertura TEXT,
            fecha_descarga TEXT,
            registros INTEGER,
            disponible INTEGER DEFAULT 1,
            notas TEXT
        )
    """)

    conn.commit()
    conn.close()


def insert_reporte(r: Dict[str, Any]):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO reportes
        (id, fuente, origen, fecha_reporte, alcaldia, colonia, calle,
         categoria, subcategoria, descripcion, latitud, longitud,
         coords_confirmadas, estado, es_emergencia, incidente_id, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        r["id"], r.get("fuente"), r.get("origen", "demo"),
        r.get("fecha_reporte"), r.get("alcaldia"), r.get("colonia"), r.get("calle"),
        r.get("categoria"), r.get("subcategoria"), r.get("descripcion"),
        r.get("latitud"), r.get("longitud"),
        1 if r.get("coords_confirmadas") else 0,
        r.get("estado", "abierto"),
        1 if r.get("es_emergencia") else 0,
        r.get("incidente_id"),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def insert_incidente(inc: Dict[str, Any]):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO incidentes
        (id, tipo, categoria, alcaldia, colonia, calle, latitud, longitud,
         total_reportes, estado, es_emergencia, fecha_primer_reporte, fecha_ultimo_reporte,
         puntaje_S, puntaje_D, puntaje_M, puntaje_A, puntaje_R, puntaje_total,
         nivel_prioridad, confianza, justificacion, origen, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        inc["id"], inc.get("tipo"), inc.get("categoria"),
        inc.get("alcaldia"), inc.get("colonia"), inc.get("calle"),
        inc.get("latitud"), inc.get("longitud"),
        inc.get("total_reportes", 1),
        inc.get("estado", "abierto"),
        1 if inc.get("es_emergencia") else 0,
        inc.get("fecha_primer_reporte"), inc.get("fecha_ultimo_reporte"),
        inc.get("puntaje_S", 0), inc.get("puntaje_D", 0),
        inc.get("puntaje_M", 0), inc.get("puntaje_A", 0), inc.get("puntaje_R", 0),
        inc.get("puntaje_total", 0),
        inc.get("nivel_prioridad", "baja"),
        inc.get("confianza", 1.0),
        inc.get("justificacion"),
        inc.get("origen", "demo"),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def insert_fuente(f: Dict[str, Any]):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO fuentes
        (id, nombre, url, licencia, fecha_cobertura, fecha_descarga, registros, disponible, notas)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        f["id"], f.get("nombre"), f.get("url"), f.get("licencia"),
        f.get("fecha_cobertura"), f.get("fecha_descarga"), f.get("registros"),
        1 if f.get("disponible") else 0, f.get("notas")
    ))
    conn.commit()
    conn.close()


def get_reportes(filters: Optional[Dict] = None) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM reportes WHERE 1=1"
    params = []
    if filters:
        if filters.get("alcaldia"):
            query += " AND alcaldia = ?"
            params.append(filters["alcaldia"])
        if filters.get("categoria"):
            query += " AND categoria = ?"
            params.append(filters["categoria"])
        if filters.get("estado"):
            query += " AND estado = ?"
            params.append(filters["estado"])
        if filters.get("solo_emergencias"):
            query += " AND es_emergencia = 1"
        if filters.get("fecha_inicio"):
            query += " AND fecha_reporte >= ?"
            params.append(filters["fecha_inicio"])
        if filters.get("fecha_fin"):
            query += " AND fecha_reporte <= ?"
            params.append(filters["fecha_fin"])
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_incidentes(filters: Optional[Dict] = None) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM incidentes WHERE 1=1"
    params = []
    if filters:
        if filters.get("alcaldia"):
            query += " AND alcaldia = ?"
            params.append(filters["alcaldia"])
        if filters.get("categoria"):
            query += " AND categoria = ?"
            params.append(filters["categoria"])
        if filters.get("nivel_prioridad"):
            query += " AND nivel_prioridad = ?"
            params.append(filters["nivel_prioridad"])
        if filters.get("estado"):
            query += " AND estado = ?"
            params.append(filters["estado"])
    query += " ORDER BY puntaje_total DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_resumen() -> Dict:
    conn = get_connection()
    cur = conn.cursor()
    total_reportes = cur.execute("SELECT COUNT(*) FROM reportes").fetchone()[0]
    incidentes_unicos = cur.execute("SELECT COUNT(*) FROM incidentes").fetchone()[0]
    casos_abiertos = cur.execute("SELECT COUNT(*) FROM incidentes WHERE estado IN ('abierto','emergencia')").fetchone()[0]
    casos_criticos = cur.execute("SELECT COUNT(*) FROM incidentes WHERE nivel_prioridad IN ('critica','alta')").fetchone()[0]
    casos_emergencia = cur.execute("SELECT COUNT(*) FROM incidentes WHERE es_emergencia = 1").fetchone()[0]
    alcaldias = cur.execute("SELECT COUNT(DISTINCT alcaldia) FROM reportes WHERE alcaldia IS NOT NULL").fetchone()[0]
    conn.close()
    return {
        "total_reportes": total_reportes,
        "incidentes_unicos": incidentes_unicos,
        "casos_abiertos": casos_abiertos,
        "casos_criticos": casos_criticos,
        "casos_emergencia": casos_emergencia,
        "alcaldias_analizadas": alcaldias,
        "fecha_actualizacion": datetime.now().isoformat(),
        "advertencia_datos": "Los datos mostrados pueden incluir registros históricos o de demostración. Ver sección Fuentes.",
    }


def get_fuentes() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM fuentes")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_alcaldias() -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT alcaldia FROM reportes WHERE alcaldia IS NOT NULL ORDER BY alcaldia")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows
