"""
URBIA CDMX — Importador de datos reales
Transforma datasets oficiales al esquema interno de URBIA.

Fuentes soportadas:
  1. Solicitudes *0311 Locatel (ADIP/CDMX)
  2. Incidentes Viales C5 (C5/CDMX)

Reglas:
  - No inventar coordenadas: si latitud/longitud son 0 o vacías → coords_confirmadas=False
  - Marcar origen como 'real' y etiqueta de fuente oficial
  - No mostrar datos personales (sexo, edad se descartan)
  - Registrar fecha de cobertura y URL de descarga
"""
import csv
import io
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple
from .alcaldias import normalizar_y_completar

# ── Mapeo de temas Locatel → categoría URBIA ──────────────────────────────────
LOCATEL_CATEGORIA_MAP = {
    # Hidráulica
    "MANTENIMIENTO DE COLADERA / ALCANTARILLA": ("hidraulica", "coladera_obstruida"),
    "COLADERA": ("hidraulica", "coladera_obstruida"),
    "DRENAJE": ("hidraulica", "drenaje_obstruido"),
    "INUNDACION": ("hidraulica", "inundacion_vialidad"),
    "INUNDACIÓN": ("hidraulica", "inundacion_vialidad"),
    "ENCHARCAMIENTO": ("hidraulica", "encharcamiento"),
    "FALTA DE AGUA": ("hidraulica", "drenaje_obstruido"),
    "AGUA POTABLE": ("hidraulica", "drenaje_obstruido"),
    "FUGAS DE AGUA": ("hidraulica", "drenaje_obstruido"),
    "FUGA DE AGUA": ("hidraulica", "drenaje_obstruido"),
    # Vial
    "BACHE": ("vial", "bache"),
    "BACHEO": ("vial", "bache"),
    "PAVIMENTO": ("vial", "pavimento_deteriorado"),
    "HUNDIMIENTO": ("vial", "hundimiento"),
    "GRIETA": ("vial", "grieta"),
    "BANQUETA": ("vial", "pavimento_deteriorado"),
    # Seguridad
    "ALUMBRADO": ("seguridad", "alumbrado"),
}

# ── Mapeo de incidentes C5 → categoría URBIA ──────────────────────────────────
C5_CATEGORIA_MAP = {
    "Choque sin lesionados": ("vial", "choque_vial"),
    "Choque con lesionados": ("seguridad", "choque_vial"),
    "Atropellado": ("seguridad", "atropello"),
    "Motociclista": ("seguridad", "accidente_moto"),
    "Ciclista": ("seguridad", "accidente_ciclista"),
    "Volcadura": ("seguridad", "volcadura"),
    "Choque con prensados": ("seguridad", "choque_vial"),
    "Persona atrapada / desbarrancada": ("seguridad", "persona_atrapada"),
    "Vehículo atrapadovarado": ("vial", "vehiculo_varado"),
    "Vehiculo desbarrancado": ("seguridad", "volcadura"),
}


def _generar_id(fuente_prefix: str, folio: str) -> str:
    """Genera un ID reproducible y único."""
    h = hashlib.md5(f"{fuente_prefix}-{folio}".encode()).hexdigest()[:8]
    return f"{fuente_prefix}-{h}"


def _coord_valida(val: str) -> bool:
    try:
        f = float(val)
        return f != 0.0 and abs(f) > 0.001
    except (ValueError, TypeError):
        return False


def importar_locatel(contenido_csv: str, max_registros: int = 5000) -> Tuple[List[Dict], Dict]:
    """
    Importa solicitudes 0311 Locatel filtradas por relevancia urbana.
    Retorna (lista_reportes, metadata_fuente).

    Solo importa temas relacionados con infraestructura (baches, coladeras, drenaje, etc.).
    Descarta: sexo, edad y cualquier dato personal.
    """
    keywords = [
        "bache", "coladera", "alcantarilla", "drenaje", "inundac",
        "pavimento", "hundimiento", "grieta", "agua", "encharcam",
        "alumbrado", "banqueta", "bacheo",
    ]

    reportes = []
    total_leidos = 0
    total_relevantes = 0
    sin_coords = 0

    reader = csv.DictReader(io.StringIO(contenido_csv))

    for row in reader:
        total_leidos += 1
        if total_relevantes >= max_registros:
            break

        tema = (row.get("tema_solicitud") or "").strip().upper()
        if not any(k in tema.lower() for k in keywords):
            continue

        total_relevantes += 1

        # Coordenadas
        lat_raw = row.get("latitud", "0")
        lon_raw = row.get("longitud", "0")
        tiene_coords = _coord_valida(lat_raw) and _coord_valida(lon_raw)
        if not tiene_coords:
            sin_coords += 1

        # Categoría
        cat, subcat = "otro", "otro"
        for k, (c, s) in LOCATEL_CATEGORIA_MAP.items():
            if k in tema:
                cat, subcat = c, s
                break

        # Estado
        estatus = (row.get("estatus") or "").upper()
        if estatus in ("CERRADO", "CONCLUIDO"):
            estado = "cerrado"
        elif estatus in ("EN PROCESO", "TURNADO", "ASIGNADO"):
            estado = "en_proceso"
        else:
            estado = "abierto"

        lat_v = float(lat_raw) if tiene_coords else None
        lon_v = float(lon_raw) if tiene_coords else None
        alcaldia_raw = None if (row.get("alcaldia") or "").strip().upper() in ("NA", "N/A", "", "NONE") else (row.get("alcaldia") or "").strip()
        alcaldia_norm, estimada = normalizar_y_completar(alcaldia_raw, lat_v, lon_v)

        folio = row.get("id_folio", f"LOC-{total_relevantes}")
        reporte = {
            "id": _generar_id("LOC", folio),
            "fuente": "Solicitudes *0311 Locatel — ADIP/CDMX",
            "origen": "real",
            "fecha_reporte": row.get("fecha_solicitud"),
            "alcaldia": alcaldia_norm,
            "colonia": (row.get("colonia_datos") or "").strip() or None,
            "calle": None,
            "categoria": cat,
            "subcategoria": subcat,
            "descripcion": f"Tema: {tema}. Fuente: 0311 Locatel. Folio: {folio}{' [alcaldía estimada por coords]' if estimada else ''}",
            "latitud": lat_v,
            "longitud": lon_v,
            "coords_confirmadas": tiene_coords,
            "estado": estado,
            "es_emergencia": False,
            "incidente_id": None,
        }
        reportes.append(reporte)

    metadata = {
        "id": "FUENTE-LOCATEL-2022",
        "nombre": "Solicitudes *0311 Locatel (2022) — ADIP/CDMX",
        "url": "https://archivo.datos.cdmx.gob.mx/suac/locatel0311-2022.csv",
        "licencia": "CC-BY-4.0",
        "fecha_cobertura": "2022 (histórico)",
        "fecha_descarga": datetime.now().strftime("%Y-%m-%d"),
        "registros": total_relevantes,
        "disponible": True,
        "notas": (
            f"Dataset real descargado de datos.cdmx.gob.mx. "
            f"Se importaron {total_relevantes} registros relevantes de {total_leidos} totales. "
            f"{sin_coords} sin coordenadas confirmadas. "
            "Se omitieron datos personales (sexo, edad). "
            "Datos históricos de 2022 — no representan estado actual."
        ),
    }
    return reportes, metadata


def importar_c5(contenido_csv: str, max_registros: int = 3000) -> Tuple[List[Dict], Dict]:
    """
    Importa incidentes viales C5.
    Solo importa registros con código de cierre 'A' (Afirmativo = confirmados).
    Los demás (N=Negativo, F=Falso, D=Duplicado, I=Informativo) se descartan.
    """
    reportes = []
    total_leidos = 0
    total_afirmativos = 0
    sin_coords = 0

    reader = csv.DictReader(io.StringIO(contenido_csv))

    for row in reader:
        total_leidos += 1
        if total_afirmativos >= max_registros:
            break

        # Solo afirmativos (confirmados en campo)
        codigo = (row.get("codigo_cierre") or "").strip().upper()
        if codigo != "A":
            continue

        total_afirmativos += 1

        incidente = (row.get("incidente_c4") or "").strip()
        tipo_inc = (row.get("tipo_incidente_c4") or "").strip()

        lat_raw = row.get("latitud", "0")
        lon_raw = row.get("longitud", "0")
        tiene_coords = _coord_valida(lat_raw) and _coord_valida(lon_raw)
        if not tiene_coords:
            sin_coords += 1

        cat, subcat = C5_CATEGORIA_MAP.get(incidente, ("seguridad", "incidente_vial"))

        folio = row.get("folio", f"C5-{total_afirmativos}")
        fecha = row.get("fecha_creacion") or row.get("fecha_cierre")

        # Emergencia solo para los más graves (prensados, atrapados)
        # Lesionados y atropellados son incidentes viales graves pero históricos cerrados
        # — no se marcan como emergencias activas
        es_emergencia = any(k in incidente.lower() for k in [
            "prensado", "atrapada", "desbarrancada"
        ])

        lat_v = float(lat_raw) if tiene_coords else None
        lon_v = float(lon_raw) if tiene_coords else None
        alcaldia_raw = (row.get("alcaldia_catalogo") or row.get("alcaldia_inicio") or "").strip() or None
        alcaldia_norm, estimada = normalizar_y_completar(alcaldia_raw, lat_v, lon_v)

        reporte = {
            "id": _generar_id("C5", folio),
            "fuente": "Incidentes Viales C5 — C5/CDMX",
            "origen": "real",
            "fecha_reporte": fecha,
            "alcaldia": alcaldia_norm,
            "colonia": (row.get("colonia_catalogo") or "").strip() or None,
            "calle": None,
            "categoria": cat,
            "subcategoria": subcat,
            "descripcion": (
                f"Incidente: {incidente}. Tipo: {tipo_inc}. "
                f"Código cierre: Afirmativo (confirmado). Folio: {folio}"
                f"{' [alcaldía estimada por coords]' if estimada else ''}"
            ),
            "latitud": lat_v,
            "longitud": lon_v,
            "coords_confirmadas": tiene_coords,
            "estado": "cerrado",
            "es_emergencia": es_emergencia,
            "incidente_id": None,
        }
        reportes.append(reporte)

    metadata = {
        "id": "FUENTE-C5-2022-2024",
        "nombre": "Incidentes Viales C5 (2022-2024) — C5/CDMX",
        "url": "https://archivo.datos.cdmx.gob.mx/C5/incidentes_viales/inViales_2022_2024.csv",
        "licencia": "CC-BY-4.0",
        "fecha_cobertura": "2022-2024 (histórico)",
        "fecha_descarga": datetime.now().strftime("%Y-%m-%d"),
        "registros": total_afirmativos,
        "disponible": True,
        "notas": (
            f"Dataset real descargado de datos.cdmx.gob.mx (C5). "
            f"Se importaron {total_afirmativos} registros Afirmativos (confirmados) de {total_leidos} totales. "
            f"{sin_coords} sin coordenadas confirmadas. "
            "Solo registros con código de cierre A=Afirmativo. "
            "Datos históricos — no representan incidentes actualmente abiertos."
        ),
    }
    return reportes, metadata
