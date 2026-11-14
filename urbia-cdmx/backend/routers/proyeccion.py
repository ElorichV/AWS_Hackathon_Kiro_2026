"""
URBIA CDMX — Rutas de la proyección de afectaciones futuras.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..services import proyeccion as proy
from ..services.database import get_reportes

router = APIRouter()


def _validar_horizonte(h: int) -> int:
    if h not in proy.HORIZONTES:
        raise HTTPException(status_code=400, detail=f"Horizonte inválido. Usa uno de {list(proy.HORIZONTES)}.")
    return h


def _validar_categoria(c: Optional[str]) -> Optional[str]:
    if c and c not in proy.CATEGORIAS:
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Usa una de {list(proy.CATEGORIAS)}.")
    return c


@router.get("/proyeccion")
def proyeccion_lista(
    horizonte: int = Query(90, description="30, 90 o 180 días"),
    alcaldia: Optional[str] = Query(None),
    colonia: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None, description="bache | coladera_drenaje | inundacion"),
    nivel: Optional[str] = Query(None, description="alto,medio,bajo"),
    limite: int = Query(500, ge=1, le=5000),
):
    """Zonas con posible afectación futura, ordenadas por índice de riesgo histórico."""
    _validar_horizonte(horizonte)
    _validar_categoria(categoria)
    datos = proy.obtener()
    res = proy.filtrar(datos, horizonte, alcaldia, colonia, categoria, nivel)
    return {
        "horizonte": horizonte,
        "ventana": datos["meta"]["ventanas"][horizonte],
        "tipo_resultado": res[0]["tipo_resultado"] if res else "indice_descriptivo",
        "total": len(res),
        "resultados": res[:limite],
    }


@router.get("/proyeccion/resumen")
def proyeccion_resumen(horizonte: int = Query(90)):
    """Indicadores por categoría y alcaldía, comparación actual vs. futuro, validación y limitaciones."""
    _validar_horizonte(horizonte)
    todos = get_reportes()
    reales = [r for r in todos if r.get("origen") == "real"] or todos
    return proy.resumen(proy.obtener(), horizonte, proy.reportes_abiertos_por_categoria(reales))


@router.get("/proyeccion/colonias")
def proyeccion_colonias(alcaldia: Optional[str] = Query(None)):
    """Colonias que aparecen en la proyección (para el filtro)."""
    res = proy.obtener()["resultados"][90]
    return sorted({e["colonia"] for e in res
                   if e.get("colonia") and (not alcaldia or e.get("alcaldia") == alcaldia)})


@router.get("/proyeccion/zona/{zona_id}")
def proyeccion_zona(zona_id: str, horizonte: int = Query(90), categoria: Optional[str] = Query(None)):
    """Detalle de una zona: proyección por horizonte y categoría, e historial de reportes."""
    _validar_horizonte(horizonte)
    _validar_categoria(categoria)
    datos = proy.obtener()
    entradas = [e for e in datos["resultados"][horizonte]
                if e["id"] == zona_id and (not categoria or e["categoria"] == categoria)]
    if not entradas:
        raise HTTPException(status_code=404, detail="Zona no encontrada en la proyección.")
    por_horizonte = {h: [{"categoria": e["categoria"], "indice": e["indice"], "nivel": e["nivel"]}
                         for e in datos["resultados"][h] if e["id"] == zona_id]
                     for h in proy.HORIZONTES}
    return {
        "zona": entradas,
        "por_horizonte": por_horizonte,
        "historial": proy.historial_zona(zona_id, categoria),
        "limitaciones": datos["limitaciones"],
    }
