"""
URBIA CDMX — Motor de proyección de afectaciones futuras.

Identifica zonas viales (celdas de ~250 m o colonias) que podrían presentar
baches, obstrucción de coladeras/drenaje o inundaciones en 30, 90 y 180 días,
a partir del historial de reportes cargado en URBIA.

Reglas de honestidad:
  - El resultado por defecto es un ÍNDICE DE RIESGO HISTÓRICO (0-100), una
    estimación descriptiva. No es una probabilidad.
  - Solo se muestran probabilidades si un backtest temporal valida el índice con
    una ventana de prueba al menos igual al horizonte, suficientes casos y
    AUC >= 0.70. Con los datos actuales esto no se cumple.
  - El backtest entrena solo con reportes anteriores a la fecha de corte.
  - Cada factor se etiqueta como "observado", "referencial" o "estimación".
"""
import hashlib
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .alcaldias import alcaldia_por_coordenadas
from .priorizacion import ZONAS_INUNDACION_REFERENCIAL

# ── Configuración ────────────────────────────────────────────────────────────
HORIZONTES = (30, 90, 180)
CELDA_GRADOS = 0.0025          # ≈ 277 m norte-sur, ≈ 262 m este-oeste en CDMX
GAP_EPISODIO_DIAS = 7          # reportes separados por más de 7 días = nuevo episodio
MIN_VECINOS_PARA_ZONA_NUEVA = 2

# Temporada de lluvias del Valle de México (referencial, SMN/CONAGUA: mayo-octubre).
LLUVIAS_INICIO = (5, 15)
LLUVIAS_FIN = (10, 15)

CATEGORIAS = {
    "bache": "Baches y pavimento",
    "coladera_drenaje": "Coladeras y drenaje obstruidos",
    "inundacion": "Encharcamientos e inundaciones",
}
HIDRAULICAS = {"coladera_drenaje", "inundacion"}

# Pesos por horizonte: H historial, Rc reincidencia, Rec recencia, V vecindad, G geografía.
# A mayor horizonte pesa menos lo reciente y más el contexto espacial/geográfico.
PESOS_HORIZONTE = {
    30:  {"H": 0.35, "Rc": 0.20, "Rec": 0.25, "V": 0.10, "G": 0.10},
    90:  {"H": 0.35, "Rc": 0.20, "Rec": 0.15, "V": 0.15, "G": 0.15},
    180: {"H": 0.30, "Rc": 0.20, "Rec": 0.10, "V": 0.20, "G": 0.20},
}
PUNTOS_ESTACIONALES = 15       # máximo que suma la temporada de lluvias al índice

UMBRAL_ALTO = 55
UMBRAL_MEDIO = 35

# Requisitos para habilitar probabilidades
PROB_MIN_POSITIVOS = 30
PROB_MIN_AUC = 0.70

_TEMAS_EXCLUIDOS = ("FALTA DE AGUA", "FUGA", "AGUA POTABLE")

AVISO_RECOMENDACION = "Sugerencia preventiva basada en datos históricos; no es una orden de intervención."


# ── Utilidades ───────────────────────────────────────────────────────────────
def _fecha(v) -> Optional[date]:
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _limpio(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("", "none", "null", "nan", "na", "n/a", "?"):
        return None
    return s


def _tema(descripcion: Optional[str]) -> str:
    d = (descripcion or "").strip()
    if d.upper().startswith("TEMA:"):
        return d[5:].split(".")[0].strip().upper()
    return ""


def categoria_proyeccion(r: Dict) -> Optional[str]:
    """Mapea un reporte a una categoría de proyección, o None si no aplica.

    Corrige la clasificación del importador de Locatel, que guarda FALTA DE AGUA
    y FUGA DE AGUA como drenaje_obstruido: esos son problemas de suministro,
    no afectaciones de la vía pública, y se excluyen.
    """
    tema = _tema(r.get("descripcion"))
    if any(t in tema for t in _TEMAS_EXCLUIDOS):
        return None
    sub = (r.get("subcategoria") or "").lower()
    if sub in ("bache", "grieta", "pavimento_deteriorado", "hundimiento"):
        return "bache"
    if sub in ("coladera_obstruida", "drenaje_obstruido"):
        return "coladera_drenaje"
    if sub in ("inundacion_vialidad", "encharcamiento"):
        return "inundacion"
    return None


def _celda(lat: float, lon: float) -> Tuple[int, int]:
    return (math.floor(lat / CELDA_GRADOS), math.floor(lon / CELDA_GRADOS))


def _id_celda(c: Tuple[int, int]) -> str:
    return f"C{c[0]}_{c[1]}"


def _centro(c: Tuple[int, int]) -> Tuple[float, float]:
    return ((c[0] + 0.5) * CELDA_GRADOS, (c[1] + 0.5) * CELDA_GRADOS)


def _bounds(c: Tuple[int, int]) -> List[List[float]]:
    return [[c[0] * CELDA_GRADOS, c[1] * CELDA_GRADOS],
            [(c[0] + 1) * CELDA_GRADOS, (c[1] + 1) * CELDA_GRADOS]]


def _vecinos(c: Tuple[int, int]):
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                yield (c[0] + di, c[1] + dj)


def _mas_comun(valores) -> Optional[str]:
    vals = [v for v in (_limpio(x) for x in valores) if v]
    return Counter(vals).most_common(1)[0][0] if vals else None


def _fraccion_lluvias(hoy: date, horizonte: int) -> float:
    def en_lluvias(d: date) -> bool:
        return LLUVIAS_INICIO <= (d.month, d.day) <= LLUVIAS_FIN
    dias = sum(1 for i in range(1, horizonte + 1) if en_lluvias(hoy + timedelta(days=i)))
    return dias / horizonte


def _episodios(fechas: List[date]) -> List[List[date]]:
    eps: List[List[date]] = []
    for f in sorted(fechas):
        if eps and (f - eps[-1][-1]).days <= GAP_EPISODIO_DIAS:
            eps[-1].append(f)
        else:
            eps.append([f])
    return eps


def _auc(scores: List[float], labels: List[int]) -> Optional[float]:
    """AUC por Mann-Whitney (con empates). None si falta una de las clases."""
    pares = sorted(zip(scores, labels), key=lambda x: x[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    rangos = [0.0] * len(pares)
    i = 0
    while i < len(pares):
        j = i
        while j + 1 < len(pares) and pares[j + 1][0] == pares[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rangos[k] = r
        i = j + 1
    suma_pos = sum(r for r, (_, l) in zip(rangos, pares) if l == 1)
    return (suma_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


# ── Construcción de zonas ────────────────────────────────────────────────────
def colonias_por_celda(reportes: List[Dict]) -> Dict[Tuple[int, int], str]:
    """Colonia más frecuente por celda, usando CUALQUIER reporte real con coordenadas
    y colonia (p. ej. C5 trae colonia del catálogo oficial). Sirve para etiquetar zonas
    cuyos reportes no traen colonia."""
    por_celda: Dict[Tuple[int, int], List[str]] = defaultdict(list)
    for r in reportes:
        col = _limpio(r.get("colonia"))
        if col and r.get("latitud") is not None and r.get("longitud") is not None:
            por_celda[_celda(float(r["latitud"]), float(r["longitud"]))].append(col)
    return {c: Counter(v).most_common(1)[0][0] for c, v in por_celda.items()}


def _etiquetar_colonia(z: Dict, etiquetas: Dict[Tuple[int, int], str]) -> None:
    if z.get("colonia") or z.get("celda") is None or not etiquetas:
        return
    if z["celda"] in etiquetas:
        z["colonia"], z["colonia_aproximada"] = etiquetas[z["celda"]], False
        return
    vecinas = [etiquetas[v] for v in _vecinos(z["celda"]) if v in etiquetas]
    if vecinas:
        z["colonia"], z["colonia_aproximada"] = Counter(vecinas).most_common(1)[0][0], True


def construir_zonas(reportes: List[Dict],
                    etiquetas: Optional[Dict[Tuple[int, int], str]] = None) -> Tuple[Dict[str, Dict], Dict]:
    """Asigna cada reporte relevante a UNA sola zona (sin duplicar).

    - Con coordenadas confirmadas → celda de ~250 m.
    - Sin coordenadas pero con colonia → zona de colonia (no aparece en el mapa).
    - Sin coordenadas ni colonia → se excluye y se cuenta.
    """
    zonas: Dict[str, Dict] = {}
    excl = Counter()
    for r in reportes:
        cat = categoria_proyeccion(r)
        if not cat:
            continue
        f = _fecha(r.get("fecha_reporte"))
        if not f:
            excl["sin_fecha"] += 1
            continue
        lat, lon = r.get("latitud"), r.get("longitud")
        colonia = _limpio(r.get("colonia"))
        alcaldia = _limpio(r.get("alcaldia"))
        if lat is not None and lon is not None:
            c = _celda(float(lat), float(lon))
            zid, tipo = _id_celda(c), "celda"
        elif colonia:
            clave = f"{alcaldia or ''}|{colonia.lower()}"
            zid = "COL-" + hashlib.md5(clave.encode()).hexdigest()[:8]
            c, tipo = None, "colonia"
        else:
            excl["sin_ubicacion"] += 1
            continue
        z = zonas.setdefault(zid, {"id": zid, "tipo_zona": tipo, "celda": c,
                                   "por_cat": defaultdict(list), "calles": [], "colonias": [],
                                   "alcaldias": [], "fuentes": set()})
        z["por_cat"][cat].append((f, r))
        z["calles"].append(r.get("calle"))
        z["colonias"].append(colonia)
        z["alcaldias"].append(alcaldia)
        if r.get("fuente"):
            z["fuentes"].add(r["fuente"])
    for z in zonas.values():
        z["calle"] = _mas_comun(z["calles"])
        z["colonia"] = _mas_comun(z["colonias"])
        z["alcaldia"] = _mas_comun(z["alcaldias"])
        z["colonia_aproximada"] = False
        if z["celda"] is not None:
            lat, lon = _centro(z["celda"])
            z["lat"], z["lon"] = round(lat, 5), round(lon, 5)
            if not z["alcaldia"]:
                z["alcaldia"] = alcaldia_por_coordenadas(lat, lon)
            _etiquetar_colonia(z, etiquetas or {})
        else:
            z["lat"] = z["lon"] = None
    return zonas, dict(excl)


def _nombre(z: Dict) -> str:
    if z.get("calle"):
        return z["calle"]
    if z.get("colonia"):
        if z.get("sin_reportes_propios"):
            pref = "Zona sin reportes propios cerca de Col. "
        elif z.get("colonia_aproximada"):
            pref = "Zona cercana a Col. "
        else:
            pref = "Zona Col. "
        return pref + z["colonia"]
    if z.get("lat") is not None:
        return f"Zona en ({z['lat']:.4f}, {z['lon']:.4f})"
    return "Ubicación no especificada"


# ── Puntuación ───────────────────────────────────────────────────────────────
def _puntuar(zonas: Dict[str, Dict], cat: str, horizonte: int, hoy: date,
             fecha_ref: date, inicio: date,
             etiquetas: Optional[Dict[Tuple[int, int], str]] = None) -> List[Dict]:
    """Calcula el índice para todas las zonas con historial en `cat`
    y para las celdas sin reportes propios rodeadas de zonas con historial."""
    pesos = dict(PESOS_HORIZONTE[horizonte])
    if cat not in HIDRAULICAS:          # G solo aplica a riesgo hidráulico
        pesos["H"] += pesos.pop("G")
    estacional = _fraccion_lluvias(hoy, horizonte)
    peso_est = 1.0 if cat in HIDRAULICAS else 0.5
    periodo = max(1, (fecha_ref - inicio).days)

    eps_por_celda: Dict[Tuple[int, int], int] = {}
    for z in zonas.values():
        if z["celda"] is not None and z["por_cat"].get(cat):
            eps_por_celda[z["celda"]] = len(_episodios([f for f, _ in z["por_cat"][cat]]))

    # Celdas candidatas sin reportes propios de esta categoría
    candidatas: Dict[Tuple[int, int], List[Tuple[int, int]]] = defaultdict(list)
    for c in eps_por_celda:
        for v in _vecinos(c):
            if v not in eps_por_celda:
                candidatas[v].append(c)
    celda_a_zona = {z["celda"]: z for z in zonas.values() if z["celda"] is not None}

    resultados = []

    def armar(z: Dict, items: List[Tuple[date, Dict]], sin_propios: bool, vec_eps: int, vec_n: int) -> Dict:
        fechas = [f for f, _ in items]
        eps = _episodios(fechas) if fechas else []
        n_rep, n_eps = len(fechas), len(eps)
        alcaldia = z.get("alcaldia")
        H = 0.6 * min(1, math.log1p(n_eps) / math.log1p(5)) + 0.4 * min(1, math.log1p(n_rep) / math.log1p(20))
        Rc = min(1.0, max(0, n_eps - 1) / 3)
        ultima = max(fechas) if fechas else None
        Rec = max(0.0, 1 - (fecha_ref - ultima).days / periodo) if ultima else 0.0
        V = min(1.0, math.log1p(vec_eps) / math.log1p(10))
        G = 1.0 if (cat in HIDRAULICAS and alcaldia in ZONAS_INUNDACION_REFERENCIAL) else 0.0
        comp = {"H": H, "Rc": Rc, "Rec": Rec, "V": V, "G": G}
        base = 100 * sum(pesos.get(k, 0) * comp[k] for k in comp)
        indice = round(min(100.0, base + PUNTOS_ESTACIONALES * estacional * peso_est), 1)
        nivel = "alto" if indice >= UMBRAL_ALTO else "medio" if indice >= UMBRAL_MEDIO else "bajo"

        # Tendencia (solo descriptiva, no entra al índice)
        tendencia = "datos insuficientes"
        if n_rep >= 3:
            mitad = inicio + timedelta(days=periodo / 2)
            n1 = sum(1 for f in fechas if f <= mitad)
            n2 = n_rep - n1
            if n2 > 1.5 * max(n1, 1):
                tendencia = "en aumento"
            elif n1 > 1.5 * max(n2, 1):
                tendencia = "en disminución"
            else:
                tendencia = "estable"
        intervalo = None
        if n_eps >= 2:
            intervalo = round(sum((eps[i][0] - eps[i - 1][-1]).days for i in range(1, n_eps)) / (n_eps - 1), 1)

        factores = []
        if n_rep:
            factores.append({"factor": "Historial en la zona", "tipo": "observado",
                             "valor": f"{n_eps} episodio(s), {n_rep} reporte(s) entre {min(fechas)} y {ultima}"})
            if n_eps >= 2:
                factores.append({"factor": "Reincidencia", "tipo": "observado",
                                 "valor": f"{n_eps} episodios separados; intervalo promedio {intervalo} días"})
            factores.append({"factor": "Último reporte", "tipo": "observado",
                             "valor": f"{ultima} ({(fecha_ref - ultima).days} días antes del fin de los datos)"})
            factores.append({"factor": "Tendencia dentro del periodo", "tipo": "observado", "valor": tendencia})
        if vec_eps:
            factores.append({"factor": "Zonas vecinas con antecedentes", "tipo": "observado",
                             "valor": f"{vec_n} celda(s) contiguas con {vec_eps} episodio(s)"})
        if G:
            factores.append({"factor": "Alcaldía con antecedente de inundación", "tipo": "referencial",
                             "valor": f"{alcaldia} está en la lista referencial de URBIA (no es el Atlas de Riesgo oficial)"})
        if estacional > 0:
            factores.append({"factor": "Temporada de lluvias en el horizonte", "tipo": "referencial",
                             "valor": f"{round(estacional * 100)}% de los {horizonte} días caen entre 15 may y 15 oct"})
        factores.append({"factor": "Índice de riesgo histórico", "tipo": "estimación",
                         "valor": f"{indice}/100 (descriptivo, no es probabilidad)"})

        if sin_propios:
            rec = (f"Inspección preventiva: la zona no tiene reportes propios, pero colinda con {vec_n} "
                   f"zona(s) con antecedentes de {CATEGORIAS[cat].lower()}.")
        elif cat == "coladera_drenaje":
            rec = "Revisar y desazolvar coladeras de la zona antes de la temporada de lluvias (mediados de mayo)."
            if n_eps >= 2:
                rec += " La obstrucción es reincidente: revisar la causa de fondo."
        elif cat == "inundacion":
            rec = "Inspeccionar la zona por antecedentes de encharcamiento o inundación y verificar el desalojo pluvial."
        else:
            rec = ("Evaluar el tramo por reincidencia de baches y programar mantenimiento preventivo del pavimento."
                   if n_eps >= 2 else "Programar inspección visual del pavimento de la zona.")

        if sin_propios or n_rep < 3:
            confianza = "baja"
        elif z["tipo_zona"] == "celda" and n_rep >= 5:
            confianza = "media"
        else:
            confianza = "baja"

        zz = dict(z, sin_reportes_propios=sin_propios)
        return {
            "id": z["id"], "clave": f"{z['id']}|{cat}", "nombre": _nombre(zz),
            "calle": z.get("calle"), "colonia": z.get("colonia"), "alcaldia": alcaldia,
            "colonia_aproximada": bool(z.get("colonia_aproximada")),
            "lat": z.get("lat"), "lon": z.get("lon"),
            "bounds": _bounds(z["celda"]) if z["celda"] is not None else None,
            "tipo_zona": z["tipo_zona"], "categoria": cat, "categoria_label": CATEGORIAS[cat],
            "horizonte": horizonte, "indice": indice, "nivel": nivel,
            "tipo_resultado": "indice_descriptivo", "probabilidad": None,
            "reportes": n_rep, "episodios": n_eps,
            "primera": str(min(fechas)) if fechas else None, "ultima": str(ultima) if ultima else None,
            "tendencia": tendencia, "intervalo_promedio_dias": intervalo,
            "vecinos_episodios": vec_eps, "sin_reportes_propios": sin_propios,
            "componentes": {k: round(v, 3) for k, v in comp.items()},
            "estacional": round(estacional, 3),
            "factores": factores,
            "recomendacion": rec, "aviso_recomendacion": AVISO_RECOMENDACION,
            "fuentes": sorted(z.get("fuentes", [])), "confianza": confianza,
        }

    for z in zonas.values():
        items = z["por_cat"].get(cat)
        if not items:
            continue
        vec_eps = vec_n = 0
        if z["celda"] is not None:
            for v in _vecinos(z["celda"]):
                if v in eps_por_celda:
                    vec_eps += eps_por_celda[v]
                    vec_n += 1
        resultados.append(armar(z, items, False, vec_eps, vec_n))

    for c, vecinas in candidatas.items():
        if len(vecinas) < MIN_VECINOS_PARA_ZONA_NUEVA:
            continue
        base = celda_a_zona.get(c)
        vz = [celda_a_zona[v] for v in vecinas if v in celda_a_zona]
        lat, lon = _centro(c)
        z = {
            "id": _id_celda(c), "tipo_zona": "celda", "celda": c,
            "calle": base.get("calle") if base else None,
            "colonia": (base.get("colonia") if base else None) or _mas_comun(x.get("colonia") for x in vz),
            "alcaldia": (base.get("alcaldia") if base else None) or _mas_comun(x.get("alcaldia") for x in vz)
                        or alcaldia_por_coordenadas(lat, lon),
            "lat": round(lat, 5), "lon": round(lon, 5),
            "fuentes": set().union(*[x.get("fuentes", set()) for x in vz]) if vz else set(),
            "colonia_aproximada": bool(base.get("colonia_aproximada")) if base else False,
        }
        if not z["colonia"]:
            _etiquetar_colonia(z, etiquetas or {})
        elif not base or not base.get("colonia"):
            z["colonia_aproximada"] = True   # tomada de celdas vecinas
        resultados.append(armar(z, [], True, sum(eps_por_celda[v] for v in vecinas), len(vecinas)))

    resultados.sort(key=lambda e: (-e["indice"], -e["reportes"], e["id"]))
    return resultados


# ── Validación temporal (backtest) ───────────────────────────────────────────
def _ubicable(r: Dict) -> bool:
    return (r.get("latitud") is not None and r.get("longitud") is not None) or bool(_limpio(r.get("colonia")))


def _backtest(reportes: List[Dict], cat: str, hoy: date) -> Dict:
    # Solo reportes que pueden asignarse a una zona; los demás no pueden ser casos positivos.
    reportes = [r for r in reportes if _ubicable(r)]
    fechas = [_fecha(r.get("fecha_reporte")) for r in reportes if categoria_proyeccion(r) == cat]
    fechas = [f for f in fechas if f]
    if len(fechas) < 30:
        return {"categoria": cat, "estado": "insuficiente", "motivo": f"Solo {len(fechas)} reportes fechados."}
    dmin, dmax = min(fechas), max(fechas)
    span = (dmax - dmin).days
    if span < 9:
        return {"categoria": cat, "estado": "insuficiente", "motivo": f"Los datos cubren solo {span} días."}
    corte = dmin + timedelta(days=round(span * 2 / 3))
    entren = [r for r in reportes if (_fecha(r.get("fecha_reporte")) or dmax) <= corte]
    prueba = [r for r in reportes if categoria_proyeccion(r) == cat and (_fecha(r.get("fecha_reporte")) or dmin) > corte]

    zonas_e, _ = construir_zonas(entren)
    pred = _puntuar(zonas_e, cat, 30, corte, corte, dmin)
    zonas_p, _ = construir_zonas(prueba)
    positivos = {zid for zid, z in zonas_p.items() if z["por_cat"].get(cat)}

    scores = [e["indice"] for e in pred]
    labels = [1 if e["id"] in positivos else 0 for e in pred]
    base_scores = [e["reportes"] for e in pred]
    k = min(20, len(pred))
    n_pos = sum(labels)
    auc = _auc(scores, labels)
    return {
        "categoria": cat, "estado": "evaluado",
        "entrenamiento": f"{dmin} a {corte}", "prueba": f"{corte + timedelta(days=1)} a {dmax}",
        "dias_prueba": (dmax - corte).days,
        "zonas_evaluadas": len(pred), "zonas_con_reporte_en_prueba": n_pos,
        "zonas_nuevas_no_anticipadas": len(positivos - {e["id"] for e in pred}),
        "tasa_base": round(n_pos / len(pred), 3) if pred else None,
        "precision_top": round(sum(labels[:k]) / k, 3) if k else None, "top_k": k,
        "auc": round(auc, 3) if auc is not None else None,
        "auc_linea_base_conteo": round(_auc(base_scores, labels), 3) if _auc(base_scores, labels) is not None else None,
        "_scores": scores, "_labels": labels,
    }


def _probabilidad_habilitada(bt: Dict, horizonte: int) -> Tuple[bool, str]:
    if bt.get("estado") != "evaluado":
        return False, bt.get("motivo", "Sin validación.")
    if bt["dias_prueba"] < horizonte:
        return False, (f"La ventana de validación ({bt['dias_prueba']} días) es menor que el horizonte "
                       f"({horizonte} días).")
    if bt["zonas_con_reporte_en_prueba"] < PROB_MIN_POSITIVOS:
        return False, f"Solo {bt['zonas_con_reporte_en_prueba']} casos positivos en validación (mínimo {PROB_MIN_POSITIVOS})."
    if bt["auc"] is None or bt["auc"] < PROB_MIN_AUC:
        return False, f"AUC {bt['auc']} menor que {PROB_MIN_AUC}."
    return True, "Validado."


def _calibrar(bt: Dict) -> Dict[str, float]:
    """Frecuencia observada de positivos por nivel en el periodo de prueba."""
    grupos = defaultdict(list)
    for s, l in zip(bt["_scores"], bt["_labels"]):
        n = "alto" if s >= UMBRAL_ALTO else "medio" if s >= UMBRAL_MEDIO else "bajo"
        grupos[n].append(l)
    return {n: sum(v) / len(v) for n, v in grupos.items() if v}


# ── API pública ──────────────────────────────────────────────────────────────
def _solo_reales(reportes: List[Dict]) -> Tuple[List[Dict], bool]:
    """Usa solo datos reales; los demo (ficticios) se usan únicamente si no hay reales."""
    reales = [r for r in reportes if r.get("origen") == "real"]
    return (reales, True) if reales else (list(reportes), False)


def proyectar(reportes: List[Dict], hoy: Optional[date] = None) -> Dict:
    hoy = hoy or date.today()
    reportes, usa_reales = _solo_reales(reportes)
    etiquetas = colonias_por_celda(reportes)
    zonas, excluidos = construir_zonas(reportes, etiquetas)
    fechas_cat: Dict[str, List[date]] = defaultdict(list)
    for z in zonas.values():
        for cat, items in z["por_cat"].items():
            fechas_cat[cat].extend(f for f, _ in items)

    resultados: Dict[int, List[Dict]] = {h: [] for h in HORIZONTES}
    validacion = {}
    for cat in CATEGORIAS:
        if not fechas_cat.get(cat):
            continue
        inicio, fin = min(fechas_cat[cat]), max(fechas_cat[cat])
        bt = _backtest(reportes, cat, hoy)
        calib = None
        for h in HORIZONTES:
            ok, motivo = _probabilidad_habilitada(bt, h)
            bt.setdefault("probabilidad_por_horizonte", {})[h] = {"habilitada": ok, "motivo": motivo}
            if ok and calib is None:
                calib = _calibrar(bt)
            entradas = _puntuar(zonas, cat, h, hoy, fin, inicio, etiquetas)
            if ok:
                for e in entradas:
                    e["tipo_resultado"] = "probabilidad_validada"
                    e["probabilidad"] = round(calib.get(e["nivel"], 0.0), 3)
            resultados[h].extend(entradas)
        validacion[cat] = {k: v for k, v in bt.items() if not k.startswith("_")}

    for h in HORIZONTES:
        resultados[h].sort(key=lambda e: (-e["indice"], -e["reportes"], e["clave"]))

    todas = [f for fs in fechas_cat.values() for f in fs]
    ultima = max(todas) if todas else None
    meta = {
        "fecha_calculo": str(hoy),
        "origen_datos": "real" if usa_reales else "demo",
        "datos_desde": str(min(todas)) if todas else None,
        "datos_hasta": str(ultima) if ultima else None,
        "antiguedad_datos_dias": (hoy - ultima).days if ultima else None,
        "reportes_usados": sum(len(fs) for fs in fechas_cat.values()),
        "excluidos": excluidos,
        "zonas_sin_coordenadas": sum(1 for z in zonas.values() if z["tipo_zona"] == "colonia"),
        "tamano_celda_m": 250,
        "ventanas": {h: {"inicio": str(hoy + timedelta(days=1)), "fin": str(hoy + timedelta(days=h))} for h in HORIZONTES},
    }
    return {"resultados": resultados, "validacion": validacion, "meta": meta,
            "limitaciones": _limitaciones(meta, validacion)}


def _limitaciones(meta: Dict, validacion: Dict) -> List[str]:
    lim = [
        f"Los datos analizados van de {meta['datos_desde']} a {meta['datos_hasta']}; "
        f"tienen {meta['antiguedad_datos_dias']} días de antigüedad. La proyección supone que los patrones históricos se repiten.",
        "El índice es una estimación descriptiva (0-100), no una probabilidad. "
        "No hay suficiente historia para validar horizontes de 30, 90 o 180 días.",
        "Casi ningún reporte trae calle: el análisis se hace por celdas de ~250 m (con coordenadas) o por colonia. "
        "La colonia de una celda se toma de reportes oficiales (p. ej. C5) ubicados en ella o, si se marca "
        "como aproximada, en una celda vecina.",
        "La estacionalidad no se puede medir con un solo mes de datos; se usa la temporada de lluvias "
        "referencial del Valle de México (15 may - 15 oct).",
        "No se integraron precipitaciones históricas, el Atlas de Riesgo oficial ni el estado de mantenimiento: "
        "no hay datos verificables cargados.",
        "Se excluyen los reportes de FALTA DE AGUA y FUGA DE AGUA: son problemas de suministro, no de la vía pública.",
    ]
    if "inundacion" not in validacion:
        lim.append("No hay reportes reales de encharcamiento o inundación en los datos cargados; "
                   "esa categoría queda vacía hasta integrar el Atlas de Riesgo de Inundaciones u otra fuente.")
    if meta.get("origen_datos") == "demo":
        lim.insert(0, "ATENCIÓN: no hay datos reales cargados; la proyección usa datos DEMO ficticios.")
    else:
        lim.append("Los registros DEMO (ficticios) no se usan en la proyección.")
    if meta.get("excluidos", {}).get("sin_ubicacion"):
        lim.append(f"{meta['excluidos']['sin_ubicacion']} reportes sin coordenadas ni colonia quedaron fuera.")
    return lim


# ── Caché e interfaz para la API y el asistente ──────────────────────────────
_CACHE: Dict = {"firma": None, "datos": None}


def obtener(forzar: bool = False) -> Dict:
    from .database import get_reportes
    reportes = get_reportes()
    firma = (len(reportes), str(date.today()))
    if forzar or _CACHE["firma"] != firma:
        _CACHE["datos"] = proyectar(reportes)
        _CACHE["firma"] = firma
    return _CACHE["datos"]


def filtrar(datos: Dict, horizonte: int, alcaldia: Optional[str] = None, colonia: Optional[str] = None,
            categoria: Optional[str] = None, nivel: Optional[str] = None) -> List[Dict]:
    res = datos["resultados"].get(horizonte, [])
    if alcaldia:
        res = [e for e in res if e.get("alcaldia") == alcaldia]
    if colonia:
        res = [e for e in res if (e.get("colonia") or "").lower() == colonia.lower()]
    if categoria:
        res = [e for e in res if e["categoria"] == categoria]
    if nivel:
        niveles = {n.strip() for n in nivel.split(",")}
        res = [e for e in res if e["nivel"] in niveles]
    return res


def resumen(datos: Dict, horizonte: int, actuales: Optional[Dict[str, int]] = None) -> Dict:
    res = datos["resultados"].get(horizonte, [])
    por_cat = {}
    for cat, label in CATEGORIAS.items():
        ec = [e for e in res if e["categoria"] == cat]
        por_cat[cat] = {
            "label": label,
            "zonas": len(ec),
            "alto": sum(1 for e in ec if e["nivel"] == "alto"),
            "medio": sum(1 for e in ec if e["nivel"] == "medio"),
            "bajo": sum(1 for e in ec if e["nivel"] == "bajo"),
            "sin_reportes_propios": sum(1 for e in ec if e["sin_reportes_propios"]),
            "con_historial": sum(1 for e in ec if not e["sin_reportes_propios"]),
            "reportes_abiertos_actuales": (actuales or {}).get(cat, 0),
        }
    por_alc = defaultdict(lambda: {"zonas_alto": 0, "zonas": 0, "indice_total": 0.0})
    for e in res:
        a = e.get("alcaldia") or "Sin alcaldía"
        por_alc[a]["zonas"] += 1
        por_alc[a]["indice_total"] += e["indice"]
        if e["nivel"] == "alto":
            por_alc[a]["zonas_alto"] += 1
    alc = sorted(({"alcaldia": a, **v, "indice_total": round(v["indice_total"], 1)} for a, v in por_alc.items()),
                 key=lambda x: (-x["zonas_alto"], -x["indice_total"]))
    return {
        "horizonte": horizonte, "ventana": datos["meta"]["ventanas"][horizonte],
        "tipo_resultado": res[0]["tipo_resultado"] if res else "indice_descriptivo",
        "por_categoria": por_cat, "por_alcaldia": alc,
        "validacion": datos["validacion"], "meta": datos["meta"],
        "limitaciones": datos["limitaciones"],
        "umbrales": {"alto": UMBRAL_ALTO, "medio": UMBRAL_MEDIO},
    }


def historial_zona(zona_id: str, categoria: Optional[str] = None) -> List[Dict]:
    """Reportes que componen la zona (sin datos personales)."""
    from .database import get_reportes
    zonas, _ = construir_zonas(_solo_reales(get_reportes())[0])
    z = zonas.get(zona_id)
    if not z:
        return []
    salida = []
    for cat, items in z["por_cat"].items():
        if categoria and cat != categoria:
            continue
        for f, r in sorted(items, key=lambda x: x[0], reverse=True):
            salida.append({"fecha": str(f), "categoria": CATEGORIAS[cat],
                           "tema": _tema(r.get("descripcion")) or (r.get("subcategoria") or ""),
                           "estado": r.get("estado"), "fuente": r.get("fuente"), "id": r.get("id")})
    return salida


def reportes_abiertos_por_categoria(reportes: List[Dict]) -> Dict[str, int]:
    c = Counter()
    for r in reportes:
        cat = categoria_proyeccion(r)
        if cat and (r.get("estado") in ("abierto", "en_proceso", "emergencia")):
            c[cat] += 1
    return dict(c)
