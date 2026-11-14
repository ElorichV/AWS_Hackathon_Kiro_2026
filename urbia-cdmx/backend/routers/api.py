"""
URBIA CDMX — Rutas de la API (FastAPI)
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import csv
import io
from datetime import datetime

from ..services.database import (
    get_reportes, get_incidentes, get_resumen, get_fuentes,
    get_alcaldias, insert_reporte, insert_incidente, insert_fuente,
)
from ..services.priorizacion import (
    agrupar_en_incidentes, recalcular_todos, PESOS_DEFAULT
)
from ..services.asistente import responder
from ..models.schemas import PesosMotor
from ..services.importador import importar_locatel, importar_c5
from ..services.alcaldias import PERIMETROS_ALCALDIAS, ALCALDIAS_OFICIALES

router = APIRouter()


@router.get("/resumen")
def resumen():
    """Totales generales del sistema."""
    return get_resumen()


@router.get("/reportes")
def listar_reportes(
    alcaldia: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    solo_emergencias: bool = Query(False),
):
    """Lista reportes con filtros opcionales."""
    filtros = {
        "alcaldia": alcaldia, "categoria": categoria,
        "estado": estado, "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin, "solo_emergencias": solo_emergencias,
    }
    return get_reportes({k: v for k, v in filtros.items() if v})


@router.get("/incidentes")
def listar_incidentes(
    alcaldia: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    nivel_prioridad: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
):
    """Lista incidentes únicos agrupados, ordenados por prioridad."""
    filtros = {
        "alcaldia": alcaldia, "categoria": categoria,
        "nivel_prioridad": nivel_prioridad, "estado": estado,
    }
    return get_incidentes({k: v for k, v in filtros.items() if v})


@router.get("/mapa")
def datos_mapa(
    alcaldia: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    nivel_prioridad: Optional[str] = Query(None, description="Separar varios niveles con coma: critica,alta"),
):
    """Datos optimizados para el mapa. Filtros: alcaldía, categoría, nivel(es) de prioridad."""
    filtros = {}
    if alcaldia:
        filtros["alcaldia"] = alcaldia
    if categoria:
        filtros["categoria"] = categoria
    incidentes = get_incidentes(filtros)
    # Filtrar por nivel (puede ser múltiple separado por coma)
    if nivel_prioridad:
        niveles = [n.strip().lower() for n in nivel_prioridad.split(",")]
        incidentes = [i for i in incidentes if (i.get("nivel_prioridad") or "").lower() in niveles
                      or (i.get("es_emergencia") and "critica" in niveles)]
    return [i for i in incidentes if i.get("latitud") and i.get("longitud")]


@router.post("/recalcular")
def recalcular(pesos: PesosMotor):
    """Recalcula prioridades con pesos personalizados."""
    suma = pesos.peso_S + pesos.peso_D + pesos.peso_M + pesos.peso_A + pesos.peso_R
    if abs(suma - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Los pesos deben sumar 1.0. Suma actual: {suma:.3f}"
        )
    p = {
        "S": pesos.peso_S, "D": pesos.peso_D,
        "M": pesos.peso_M, "A": pesos.peso_A, "R": pesos.peso_R,
    }
    incidentes = get_incidentes()
    resultado = recalcular_todos(incidentes, p)
    # Guardar resultados recalculados
    for inc in resultado:
        insert_incidente(inc)
    return {
        "mensaje": f"Recálculo completado para {len(resultado)} incidentes.",
        "pesos_usados": p,
        "top_5": resultado[:5],
    }


@router.get("/alcaldias")
def listar_alcaldias():
    """Lista de alcaldías con datos cargados."""
    return get_alcaldias()


@router.get("/alcaldias/catalogo")
def catalogo_alcaldias():
    """Catálogo oficial de las 16 alcaldías de la CDMX."""
    return ALCALDIAS_OFICIALES


@router.get("/alcaldias/perimetros")
def perimetros_alcaldias(alcaldia: Optional[str] = Query(None)):
    """
    Polígonos aproximados de perímetros de alcaldías para Leaflet.
    Si se especifica alcaldía, retorna solo ese perímetro.
    NOTA: Son aproximaciones para visualización — no son límites oficiales del INEGI.
    """
    if alcaldia:
        coords = PERIMETROS_ALCALDIAS.get(alcaldia)
        if not coords:
            raise HTTPException(status_code=404, detail=f"No hay perímetro disponible para: {alcaldia}")
        return {"alcaldia": alcaldia, "perimetro": coords, "advertencia": "Perímetro aproximado — no es límite oficial INEGI"}
    return {
        "alcaldias": [
            {"alcaldia": a, "perimetro": p}
            for a, p in PERIMETROS_ALCALDIAS.items()
        ],
        "advertencia": "Perímetros aproximados para visualización. No son límites oficiales del INEGI.",
    }


@router.get("/motor/explicacion")
def explicacion_motor():
    """
    Explicación completa del motor de priorización:
    criterios, fórmula, rangos y ponderaciones.
    """
    return {
        "advertencia": "Esta ponderación es una propuesta metodológica del equipo URBIA. No es metodología oficial del Gobierno de la Ciudad de México.",
        "formula": "PRIORIDAD = 0.30·S + 0.25·D + 0.20·M + 0.15·A + 0.10·R",
        "variables": [
            {
                "clave": "S",
                "nombre": "Seguridad y Gravedad",
                "peso": 0.30,
                "descripcion": "Evalúa el riesgo directo para personas: emergencias, bloqueos, hundimientos.",
                "rangos": [
                    {"condicion": "Emergencia confirmada", "puntaje": 100},
                    {"condicion": "Vialidad bloqueada o inundada", "puntaje": 85},
                    {"condicion": "Hundimiento estructural", "puntaje": 75},
                    {"condicion": "Categoría seguridad", "puntaje": 70},
                    {"condicion": "Bache, grieta, pavimento dañado", "puntaje": 50},
                    {"condicion": "Coladera u obstrucción hidráulica", "puntaje": 45},
                    {"condicion": "Encharcamiento", "puntaje": 40},
                    {"condicion": "Sin clasificar", "puntaje": 30},
                ],
            },
            {
                "clave": "D",
                "nombre": "Frecuencia de Denuncias",
                "peso": 0.25,
                "descripcion": "Volumen de reportes ciudadanos sobre el mismo incidente, con transformación logarítmica para evitar que grandes volúmenes dominen el resultado.",
                "formula": "D = min(100, (log(n+1) / log(51)) × 100)",
                "ejemplos": [
                    {"reportes": 1, "puntaje": 5},
                    {"reportes": 5, "puntaje": 22},
                    {"reportes": 10, "puntaje": 29},
                    {"reportes": 25, "puntaje": 43},
                    {"reportes": 50, "puntaje": 100},
                ],
            },
            {
                "clave": "M",
                "nombre": "Impacto en Movilidad y Servicios",
                "peso": 0.20,
                "descripcion": "Evalúa el impacto en la circulación usando indicadores sustitutos (no hay aforo vehicular disponible).",
                "indicadores": [
                    {"condicion": "Base", "puntos": 20},
                    {"condicion": "Vialidad primaria (Insurgentes, Eje Central, IPN…)", "puntos": "+40"},
                    {"condicion": "Tipo de alto impacto (bloqueo, inundación, hundimiento)", "puntos": "+30"},
                    {"condicion": "Alcaldía de alta densidad (Iztapalapa, Cuauhtémoc…)", "puntos": "+10"},
                ],
                "nota": "Indicadores sustitutos — no hay aforo vehicular integrado en el MVP.",
            },
            {
                "clave": "A",
                "nombre": "Antigüedad del Incidente Abierto",
                "peso": 0.15,
                "descripcion": "Días transcurridos desde el primer reporte del incidente sin atender. Mide el tiempo real de desatención, no la antigüedad de un registro histórico.",
                "formula": "A = min(100, (días / 365) × 100)",
                "ejemplos": [
                    {"dias": 30, "puntaje": 8},
                    {"dias": 90, "puntaje": 25},
                    {"dias": 180, "puntaje": 49},
                    {"dias": 365, "puntaje": 100},
                ],
            },
            {
                "clave": "R",
                "nombre": "Riesgo de Lluvia y Exposición Ambiental",
                "peso": 0.10,
                "descripcion": "Peligrosidad histórica de inundación combinada con el tipo de incidente.",
                "indicadores": [
                    {"condicion": "Base", "puntos": 10},
                    {"condicion": "Alcaldía con peligrosidad histórica de inundación", "puntos": "+40"},
                    {"condicion": "Categoría hidráulica", "puntos": "+30"},
                    {"condicion": "Historial de encharcamiento o inundación", "puntos": "+20"},
                ],
                "nota": "Pronóstico meteorológico en tiempo real no integrado. Requiere API externa.",
            },
        ],
        "niveles_prioridad": [
            {"nivel": "CRÍTICA",  "rango": "70 – 100", "descripcion": "Requiere atención inmediata por riesgo grave para personas o infraestructura.", "color": "#dc2626"},
            {"nivel": "ALTA",     "rango": "50 – 69",  "descripcion": "Requiere atención prioritaria. Alto impacto o probabilidad de agravarse.", "color": "#ea580c"},
            {"nivel": "MEDIA",    "rango": "30 – 49",  "descripcion": "Necesita atención programada. Sin evidencia de riesgo inmediato.", "color": "#ca8a04"},
            {"nivel": "BAJA",     "rango": "0 – 29",   "descripcion": "Puede atenderse mediante mantenimiento rutinario y seguimiento.", "color": "#16a34a"},
        ],
        "nota_emergencias": "Las emergencias confirmadas se escalan automáticamente a puntaje 100 sin pasar por el motor, garantizando que siempre aparezcan primero en el ranking.",
    }




@router.get("/fuentes")
def listar_fuentes():
    """Catálogo de fuentes de datos."""
    return get_fuentes()


@router.post("/chat")
def chat(payload: dict):
    """Asistente URBIA AI — responde preguntas sobre los datos."""
    pregunta = payload.get("pregunta", "").strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="El campo 'pregunta' es obligatorio.")
    if len(pregunta) > 500:
        raise HTTPException(status_code=400, detail="Pregunta demasiado larga (máx 500 caracteres).")
    return responder(pregunta)


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Carga masiva de reportes desde un archivo CSV.
    Columnas esperadas: id, fuente, fecha_reporte, alcaldia, colonia, calle,
    categoria, subcategoria, descripcion, latitud, longitud, estado, es_emergencia
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV.")

    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    insertados = 0
    errores = []

    for i, row in enumerate(reader):
        try:
            reporte = {
                "id": row.get("id") or f"CSV-{i+1:04d}-{datetime.now().timestamp():.0f}",
                "fuente": row.get("fuente", "CSV cargado por usuario"),
                "origen": "real" if row.get("origen") == "real" else "demo",
                "fecha_reporte": row.get("fecha_reporte"),
                "alcaldia": row.get("alcaldia"),
                "colonia": row.get("colonia"),
                "calle": row.get("calle"),
                "categoria": row.get("categoria", "otro"),
                "subcategoria": row.get("subcategoria"),
                "descripcion": row.get("descripcion"),
                "latitud": float(row["latitud"]) if row.get("latitud") else None,
                "longitud": float(row["longitud"]) if row.get("longitud") else None,
                "coords_confirmadas": row.get("latitud") is not None,
                "estado": row.get("estado", "abierto"),
                "es_emergencia": str(row.get("es_emergencia", "")).lower() in ("true", "1", "si", "sí"),
            }
            insert_reporte(reporte)
            insertados += 1
        except Exception as e:
            errores.append({"fila": i + 2, "error": str(e)})

    # Re-agrupar y recalcular
    todos_reportes = get_reportes()
    incidentes = agrupar_en_incidentes(todos_reportes)
    calculados = recalcular_todos(incidentes)
    for inc in calculados:
        insert_incidente(inc)

    return {
        "mensaje": f"{insertados} reportes cargados correctamente.",
        "incidentes_generados": len(calculados),
        "errores": errores[:10],
        "advertencia": "Verifica que los datos cargados sean reales o estén etiquetados correctamente.",
    }


@router.post("/importar-real")
async def importar_datos_reales():
    """
    Descarga e importa datos reales desde los portales oficiales de la CDMX.
    Fuentes: 0311 Locatel 2022, Incidentes Viales C5 2022-2024.
    Solo registros afirmativos/confirmados. Datos históricos etiquetados como tal.
    """
    import urllib.request
    resultados = []

    # ── Locatel 0311 (2022) ──────────────────────────────────────────────────
    try:
        url_locatel = "https://archivo.datos.cdmx.gob.mx/suac/locatel0311-2022.csv"
        req = urllib.request.urlopen(url_locatel, timeout=30)
        # Leer solo los primeros 5MB para no colapsar memoria
        contenido = req.read(5 * 1024 * 1024).decode("utf-8", errors="replace")
        reportes, meta = importar_locatel(contenido, max_registros=3000)
        for r in reportes:
            insert_reporte(r)
        insert_fuente(meta)
        resultados.append({
            "fuente": "0311 Locatel 2022",
            "importados": len(reportes),
            "estado": "ok",
            "advertencia": "Datos históricos 2022. No representan estado actual.",
        })
    except Exception as e:
        resultados.append({"fuente": "0311 Locatel 2022", "estado": "error", "error": str(e)})

    # ── Incidentes Viales C5 (2022-2024) ────────────────────────────────────
    try:
        url_c5 = "https://archivo.datos.cdmx.gob.mx/C5/incidentes_viales/inViales_2022_2024.csv"
        req = urllib.request.urlopen(url_c5, timeout=30)
        contenido = req.read(5 * 1024 * 1024).decode("utf-8", errors="replace")
        reportes, meta = importar_c5(contenido, max_registros=2000)
        for r in reportes:
            insert_reporte(r)
        insert_fuente(meta)
        resultados.append({
            "fuente": "Incidentes Viales C5 2022-2024",
            "importados": len(reportes),
            "estado": "ok",
            "advertencia": "Datos históricos. Solo registros Afirmativos (confirmados en campo).",
        })
    except Exception as e:
        resultados.append({"fuente": "Incidentes Viales C5", "estado": "error", "error": str(e)})

    # ── Reagrupar y recalcular ────────────────────────────────────────────────
    todos_reportes = get_reportes()
    incidentes = agrupar_en_incidentes(todos_reportes)
    calculados = recalcular_todos(incidentes)
    for inc in calculados:
        insert_incidente(inc)

    return {
        "mensaje": f"Importación completada. {len(calculados)} incidentes totales calculados.",
        "resultados": resultados,
        "advertencia_general": (
            "⚠️ Los datos importados son HISTÓRICOS. "
            "No representan el estado actual de la infraestructura. "
            "Separados de los datos DEMO en el catálogo de fuentes."
        ),
    }


def normativa():
    """Matriz normativa de referencia."""
    return {
        "advertencia": "Esta información es referencial. Verificar en fuentes oficiales antes de aplicar.",
        "fuente_primaria": "https://data.consejeria.cdmx.gob.mx/",
        "normas": [
            {
                "nombre": "Ley de Movilidad de la Ciudad de México",
                "disposicion": "Establece obligaciones de seguridad vial y mantenimiento de infraestructura",
                "articulo": "Verificar en Consejería Jurídica CDMX",
                "url": "https://data.consejeria.cdmx.gob.mx/",
                "aplicabilidad": "Módulo B (vial), Módulo C (seguridad)",
                "tipo": "obligacion_legal_referencial",
            },
            {
                "nombre": "Ley de Gestión Integral de Riesgos y Protección Civil de la CDMX",
                "disposicion": "Marco para identificación y atención de riesgos hidrometeorológicos",
                "articulo": "Verificar en Consejería Jurídica CDMX",
                "url": "https://data.consejeria.cdmx.gob.mx/",
                "aplicabilidad": "Módulo A (hidráulica), Módulo C (seguridad)",
                "tipo": "obligacion_legal_referencial",
            },
            {
                "nombre": "Ley de Obras Públicas de la Ciudad de México",
                "disposicion": "Regula contratación y ejecución de obras de mantenimiento urbano",
                "articulo": "Verificar en Consejería Jurídica CDMX",
                "url": "https://data.consejeria.cdmx.gob.mx/",
                "aplicabilidad": "Módulo D (planeación operativa)",
                "tipo": "obligacion_legal_referencial",
            },
            {
                "nombre": "Ley de Protección de Datos Personales en Posesión de Sujetos Obligados CDMX",
                "disposicion": "Obliga a minimizar datos personales y proteger información de ciudadanos",
                "articulo": "Verificar en Consejería Jurídica CDMX",
                "url": "https://data.consejeria.cdmx.gob.mx/",
                "aplicabilidad": "Todo el sistema — datos de denunciantes",
                "tipo": "obligacion_legal_referencial",
            },
        ],
        "nota_sistema": (
            "URBIA CDMX no emite órdenes oficiales de trabajo ni declara emergencias públicas. "
            "Es una herramienta de apoyo a decisiones. La asignación de competencias requiere "
            "validación institucional."
        ),
    }
