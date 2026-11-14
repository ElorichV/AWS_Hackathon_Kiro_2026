"""
URBIA CDMX — Motor de Priorización
Fórmula: PRIORIDAD = 0.30(S) + 0.25(D) + 0.20(M) + 0.15(A) + 0.10(R)

ADVERTENCIA: La ponderación usada es una propuesta metodológica del equipo URBIA.
No es una metodología oficial del Gobierno de la Ciudad de México.
"""
import math
from datetime import datetime, date
from typing import List, Dict, Optional, Any


# ── Pesos por defecto ────────────────────────────────────────────────────────
PESOS_DEFAULT = {
    "S": 0.30,  # Seguridad y gravedad
    "D": 0.25,  # Frecuencia de denuncias
    "M": 0.20,  # Impacto en movilidad/servicios
    "A": 0.15,  # Antigüedad del incidente abierto
    "R": 0.10,  # Riesgo de lluvia/ambiental
}

# ── Zonas con alta peligrosidad histórica de inundación ─────────────────────
# Fuente: conocimiento general de zonas de inundación CDMX.
# No representa el Atlas de Riesgo oficial. Marcar como REFERENCIAL.
ZONAS_INUNDACION_REFERENCIAL = [
    "Iztapalapa", "Iztacalco", "Gustavo A. Madero",
    "Xochimilco", "Tláhuac", "Cuajimalpa de Morelos",
]

# ── Vialidades primarias (indicador sustituto de aforo alto) ─────────────────
VIALIDADES_PRIMARIAS = [
    "insurgentes", "eje central", "reforma", "periférico", "viaducto",
    "politécnico", "churubusco", "ermita", "taxqueña", "zaragoza",
    "tlalpan", "xochimilco", "cuauhtémoc", "circuito",
]

# ── Servicios esenciales cercanos (subcategorías que elevan M) ───────────────
SUBCATEGORIAS_ALTO_IMPACTO = [
    "inundacion_vialidad", "vialidad_bloqueada", "hundimiento",
]


def _calcular_S(incidente: Dict) -> tuple:
    """
    Variable S: Seguridad y gravedad (0–100)
    Criterios:
      - es_emergencia → 100
      - subcategoria de alto impacto → 70-85
      - categoria seguridad → +20
      - categoria vial con hundimiento → 65
      - resto → 30-50
    """
    if incidente.get("es_emergencia"):
        return 100.0, "Emergencia confirmada: máxima prioridad de seguridad."

    sub = (incidente.get("subcategoria") or "").lower()
    cat = (incidente.get("categoria") or "").lower()

    if sub in ["vialidad_bloqueada", "inundacion_vialidad"]:
        return 85.0, "Vialidad bloqueada o inundada: riesgo directo para circulación."
    if sub == "hundimiento":
        return 75.0, "Hundimiento: riesgo estructural y vial."
    if cat == "seguridad":
        return 70.0, "Categoría de seguridad: potencial emergencia."
    if sub in ["bache", "grieta", "pavimento_deteriorado"]:
        return 50.0, "Daño vial: riesgo moderado para vehículos y peatones."
    if sub in ["coladera_obstruida", "drenaje_obstruido"]:
        return 45.0, "Infraestructura hidráulica comprometida: riesgo en temporada de lluvias."
    if sub == "encharcamiento":
        return 40.0, "Encharcamiento: riesgo bajo en condiciones normales, mayor en lluvia."

    return 30.0, "Gravedad no determinada con precisión. Puntaje provisional."


def _calcular_D(total_reportes: int) -> tuple:
    """
    Variable D: Frecuencia de denuncias (0–100)
    Transformación logarítmica para evitar que volúmenes muy grandes dominen.
    D = min(100, (log(n+1) / log(50+1)) * 100)
    """
    if total_reportes <= 0:
        return 0.0, "Sin reportes registrados."
    score = min(100.0, (math.log(total_reportes + 1) / math.log(51)) * 100)
    return round(score, 2), f"{total_reportes} reporte(s) registrado(s). Transformación logarítmica aplicada."


def _calcular_M(incidente: Dict) -> tuple:
    """
    Variable M: Impacto en movilidad y servicios esenciales (0–100)
    Indicadores sustitutos (no hay aforo vehicular disponible):
      - Vialidad primaria → +40
      - Subcategoría de alto impacto → +30
      - Alcaldía de alta densidad → +20
      - Sin información suficiente → 20 provisional
    """
    score = 20.0
    razones = []

    calle = (incidente.get("calle") or "").lower()
    sub = (incidente.get("subcategoria") or "").lower()
    alcaldia = (incidente.get("alcaldia") or "")

    if any(v in calle for v in VIALIDADES_PRIMARIAS):
        score += 40
        razones.append("Vialidad primaria o de alto tránsito (indicador sustituto).")

    if sub in SUBCATEGORIAS_ALTO_IMPACTO:
        score += 30
        razones.append("Tipo de incidente con alto impacto en la circulación.")

    if alcaldia in ["Iztapalapa", "Cuauhtémoc", "Gustavo A. Madero", "Tlalpan"]:
        score += 10
        razones.append("Alcaldía con alta densidad poblacional.")

    score = min(100.0, score)
    nota = " ".join(razones) if razones else "Sin datos de aforo verificables. Puntaje provisional basado en indicadores sustitutos."
    return round(score, 2), nota


def _calcular_A(fecha_primer_reporte: Optional[str]) -> tuple:
    """
    Variable A: Antigüedad del incidente abierto (0–100)
    Mide días desde el primer reporte del incidente (no edad de registro histórico).
    A = min(100, (días / 365) * 100)
    """
    if not fecha_primer_reporte:
        return 25.0, "Fecha de primer reporte desconocida. Puntaje provisional de 25."
    try:
        fecha = datetime.strptime(fecha_primer_reporte[:10], "%Y-%m-%d").date()
        dias = (date.today() - fecha).days
        score = min(100.0, (dias / 365) * 100)
        return round(score, 2), f"Incidente sin atender durante {dias} días desde el primer reporte."
    except Exception:
        return 25.0, "No se pudo calcular antigüedad. Puntaje provisional de 25."


def _calcular_R(incidente: Dict) -> tuple:
    """
    Variable R: Exposición a riesgo de lluvia/ambiental (0–100)
    Diferencia:
      - Peligrosidad histórica (zona conocida de inundación)
      - Pronóstico vigente (no disponible sin API meteorológica)
      - Tipo de incidente hidráulico
    """
    alcaldia = (incidente.get("alcaldia") or "")
    cat = (incidente.get("categoria") or "").lower()
    sub = (incidente.get("subcategoria") or "").lower()

    score = 10.0
    razones = []

    if alcaldia in ZONAS_INUNDACION_REFERENCIAL:
        score += 40
        razones.append(f"{alcaldia}: zona con peligrosidad histórica de inundación (referencial, no Atlas oficial).")

    if cat == "hidraulica":
        score += 30
        razones.append("Incidente hidráulico: mayor vulnerabilidad ante lluvias.")

    if sub in ["inundacion_vialidad", "encharcamiento"]:
        score += 20
        razones.append("Historial de encharcamiento o inundación en la ubicación.")

    score = min(100.0, score)
    razones.append("Pronóstico meteorológico vigente no integrado (requiere API). Puntaje basado en historial.")
    return round(score, 2), " ".join(razones)


def calcular_prioridad_incidente(incidente: Dict, pesos: Optional[Dict] = None) -> Dict:
    """
    Calcula el puntaje de prioridad de un incidente.
    Retorna el incidente enriquecido con puntajes y justificación.
    El motor es determinista: mismos inputs → mismo output.
    """
    if pesos is None:
        pesos = PESOS_DEFAULT

    # Validar que los pesos sumen ~1.0 (tolerancia 0.01)
    suma = sum(pesos.values())
    if abs(suma - 1.0) > 0.01:
        raise ValueError(f"Los pesos deben sumar 1.0. Suma actual: {suma:.3f}")

    # Si es emergencia confirmada → escalamiento directo, no depende del puntaje
    if incidente.get("es_emergencia") or incidente.get("estado") == "emergencia":
        return {
            **incidente,
            "puntaje_S": 100.0, "puntaje_D": 100.0, "puntaje_M": 100.0,
            "puntaje_A": 100.0, "puntaje_R": 100.0,
            "puntaje_total": 100.0,
            "nivel_prioridad": "critica",
            "confianza": 1.0,
            "justificacion": "⚠️ EMERGENCIA CONFIRMADA. Escalamiento directo. No depende del puntaje del motor.",
        }

    s, nota_s = _calcular_S(incidente)
    d, nota_d = _calcular_D(incidente.get("total_reportes", 1))
    m, nota_m = _calcular_M(incidente)
    a, nota_a = _calcular_A(incidente.get("fecha_primer_reporte"))
    r, nota_r = _calcular_R(incidente)

    total = (
        pesos["S"] * s +
        pesos["D"] * d +
        pesos["M"] * m +
        pesos["A"] * a +
        pesos["R"] * r
    )
    total = round(total, 2)

    if total >= 70:
        nivel = "critica"
    elif total >= 50:
        nivel = "alta"
    elif total >= 30:
        nivel = "media"
    else:
        nivel = "baja"

    # Confianza: se reduce si faltan datos clave
    confianza = 1.0
    if not incidente.get("coords_confirmadas"):
        confianza -= 0.3
    if not incidente.get("fecha_primer_reporte"):
        confianza -= 0.1
    confianza = max(0.1, round(confianza, 2))

    justificacion = (
        f"Puntaje total: {total}/100 | Nivel: {nivel.upper()}\n"
        f"• S={s} (peso {pesos['S']*100:.0f}%): {nota_s}\n"
        f"• D={d} (peso {pesos['D']*100:.0f}%): {nota_d}\n"
        f"• M={m} (peso {pesos['M']*100:.0f}%): {nota_m}\n"
        f"• A={a} (peso {pesos['A']*100:.0f}%): {nota_a}\n"
        f"• R={r} (peso {pesos['R']*100:.0f}%): {nota_r}\n"
        f"Confianza: {confianza*100:.0f}%"
    )

    return {
        **incidente,
        "puntaje_S": s, "puntaje_D": d, "puntaje_M": m,
        "puntaje_A": a, "puntaje_R": r,
        "puntaje_total": total,
        "nivel_prioridad": nivel,
        "confianza": confianza,
        "justificacion": justificacion,
    }


def agrupar_en_incidentes(reportes: List[Dict]) -> List[Dict]:
    """
    Agrupa reportes en incidentes únicos por:
    - Proximidad geográfica (< 200 metros)
    - Misma categoría
    - Intervalo temporal (< 30 días entre reportes)

    Los registros originales NO se eliminan.
    Se distinguen:
    1. Total de reportes
    2. Incidentes únicos estimados
    3. Reportes en incidentes abiertos
    """
    incidentes = []
    asignados = set()

    def _distancia_km(lat1, lon1, lat2, lon2):
        """Distancia aproximada en km usando fórmula de Haversine simplificada."""
        if None in (lat1, lon1, lat2, lon2):
            return float("inf")
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def _dias_entre(f1, f2):
        try:
            d1 = datetime.strptime(f1[:10], "%Y-%m-%d").date()
            d2 = datetime.strptime(f2[:10], "%Y-%m-%d").date()
            return abs((d2 - d1).days)
        except Exception:
            return 999

    for i, r in enumerate(reportes):
        if r["id"] in asignados:
            continue

        # Semilla del incidente
        grupo = [r]
        asignados.add(r["id"])

        for j, r2 in enumerate(reportes):
            if r2["id"] in asignados:
                continue
            if r2.get("categoria") != r.get("categoria"):
                continue

            dist = _distancia_km(r.get("latitud"), r.get("longitud"),
                                  r2.get("latitud"), r2.get("longitud"))
            if dist > 0.2:  # > 200 metros → no agrupar
                continue

            dias = _dias_entre(r.get("fecha_reporte", ""), r2.get("fecha_reporte", ""))
            if dias > 30:  # > 30 días → incidente diferente
                continue

            grupo.append(r2)
            asignados.add(r2["id"])

        # Construir incidente con el reporte más grave como semilla
        semilla = max(grupo, key=lambda x: 1 if x.get("es_emergencia") else 0)
        fechas = sorted([g["fecha_reporte"] for g in grupo if g.get("fecha_reporte")])

        inc_id = f"INC-{semilla['id']}"
        inc = {
            "id": inc_id,
            "tipo": semilla.get("subcategoria") or semilla.get("categoria"),
            "categoria": semilla.get("categoria"),
            "alcaldia": semilla.get("alcaldia"),
            "colonia": semilla.get("colonia"),
            "calle": semilla.get("calle"),
            "latitud": semilla.get("latitud"),
            "longitud": semilla.get("longitud"),
            "total_reportes": len(grupo),
            "estado": "emergencia" if semilla.get("es_emergencia") else semilla.get("estado", "abierto"),
            "es_emergencia": semilla.get("es_emergencia", False),
            "fecha_primer_reporte": fechas[0] if fechas else None,
            "fecha_ultimo_reporte": fechas[-1] if fechas else None,
            "coords_confirmadas": semilla.get("coords_confirmadas", False),
            "origen": semilla.get("origen", "demo"),
        }
        incidentes.append(inc)

    return incidentes


def recalcular_todos(incidentes: List[Dict], pesos: Optional[Dict] = None) -> List[Dict]:
    """Recalcula prioridades para todos los incidentes con los pesos dados."""
    if pesos is None:
        pesos = PESOS_DEFAULT
    resultado = [calcular_prioridad_incidente(inc, pesos) for inc in incidentes]
    # Ordenar: emergencias primero, luego por puntaje descendente
    resultado.sort(key=lambda x: (
        0 if x.get("es_emergencia") or x.get("estado") == "emergencia" else 1,
        -x.get("puntaje_total", 0)
    ))
    return resultado
