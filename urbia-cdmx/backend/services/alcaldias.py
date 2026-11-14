"""
URBIA CDMX — Normalización de alcaldías y datos geográficos
Mejoras 4 y 5: homologación de nombres y asignación por coordenadas
"""
from typing import Optional, Tuple

# ── Catálogo oficial de las 16 alcaldías ─────────────────────────────────────
ALCALDIAS_OFICIALES = [
    "Álvaro Obregón",
    "Azcapotzalco",
    "Benito Juárez",
    "Coyoacán",
    "Cuajimalpa de Morelos",
    "Cuauhtémoc",
    "Gustavo A. Madero",
    "Iztacalco",
    "Iztapalapa",
    "La Magdalena Contreras",
    "Miguel Hidalgo",
    "Milpa Alta",
    "Tláhuac",
    "Tlalpan",
    "Venustiano Carranza",
    "Xochimilco",
]

# ── Tabla de sinónimos → nombre oficial ──────────────────────────────────────
# Cubre abreviaturas, errores de acento, variantes del dataset CDMX
_SINONIMOS = {
    # Álvaro Obregón
    "alvaro obregon": "Álvaro Obregón",
    "alvaro obregón": "Álvaro Obregón",
    "álvaro obregon": "Álvaro Obregón",
    "a. obregon": "Álvaro Obregón",
    "a.obregon": "Álvaro Obregón",
    # Azcapotzalco
    "azcapotzalco": "Azcapotzalco",
    # Benito Juárez
    "benito juarez": "Benito Juárez",
    "benito juárez": "Benito Juárez",
    "b. juarez": "Benito Juárez",
    # Coyoacán
    "coyoacan": "Coyoacán",
    "coyoacán": "Coyoacán",
    # Cuajimalpa
    "cuajimalpa": "Cuajimalpa de Morelos",
    "cuajimalpa de morelos": "Cuajimalpa de Morelos",
    # Cuauhtémoc
    "cuauhtemoc": "Cuauhtémoc",
    "cuauhtémoc": "Cuauhtémoc",
    # Gustavo A. Madero
    "gustavo a. madero": "Gustavo A. Madero",
    "gustavo a madero": "Gustavo A. Madero",
    "gustavo madero": "Gustavo A. Madero",
    "g.a. madero": "Gustavo A. Madero",
    "g. a. madero": "Gustavo A. Madero",
    "g.a.madero": "Gustavo A. Madero",
    # Iztacalco
    "iztacalco": "Iztacalco",
    # Iztapalapa
    "iztapalapa": "Iztapalapa",
    # La Magdalena Contreras
    "la magdalena contreras": "La Magdalena Contreras",
    "magdalena contreras": "La Magdalena Contreras",
    "la magdalena": "La Magdalena Contreras",
    # Miguel Hidalgo
    "miguel hidalgo": "Miguel Hidalgo",
    # Milpa Alta
    "milpa alta": "Milpa Alta",
    # Tláhuac
    "tlahuac": "Tláhuac",
    "tláhuac": "Tláhuac",
    # Tlalpan
    "tlalpan": "Tlalpan",
    # Venustiano Carranza
    "venustiano carranza": "Venustiano Carranza",
    "v. carranza": "Venustiano Carranza",
    "v.carranza": "Venustiano Carranza",
    # Xochimilco
    "xochimilco": "Xochimilco",
}

# ── Bounding boxes aproximados por alcaldía (lat_min, lat_max, lon_min, lon_max)
# Fuente: conocimiento geográfico general — no reemplaza GeoJSON oficial
# Se usan como fallback cuando no hay otro dato de alcaldía
_BBOXES = {
    "Álvaro Obregón":        (19.310, 19.410, -99.290, -99.180),
    "Azcapotzalco":          (19.460, 19.520, -99.210, -99.160),
    "Benito Juárez":         (19.355, 19.410, -99.185, -99.130),
    "Coyoacán":              (19.300, 19.380, -99.185, -99.090),
    "Cuajimalpa de Morelos": (19.330, 19.430, -99.340, -99.240),
    "Cuauhtémoc":            (19.400, 19.470, -99.175, -99.110),
    "Gustavo A. Madero":     (19.460, 19.560, -99.160, -99.060),
    "Iztacalco":             (19.370, 19.420, -99.110, -99.060),
    "Iztapalapa":            (19.310, 19.420, -99.090, -98.990),
    "La Magdalena Contreras":(19.270, 19.360, -99.280, -99.190),
    "Miguel Hidalgo":        (19.400, 19.470, -99.260, -99.170),
    "Milpa Alta":            (19.130, 19.270, -99.080, -98.960),
    "Tláhuac":               (19.240, 19.360, -99.030, -98.960),
    "Tlalpan":               (19.150, 19.370, -99.230, -99.060),
    "Venustiano Carranza":   (19.400, 19.460, -99.110, -99.040),
    "Xochimilco":            (19.230, 19.330, -99.130, -99.000),
}


def normalizar_alcaldia(nombre: Optional[str]) -> Optional[str]:
    """
    Recibe cualquier variante de nombre de alcaldía y retorna el nombre oficial.
    Retorna None si no puede identificarla.
    """
    if not nombre:
        return None
    limpio = nombre.strip().upper()
    if limpio in ("NA", "N/A", "NONE", "", "DESCONOCIDA", "DESCONOCIDO", "SIN ALCALDIA"):
        return None
    clave = nombre.strip().lower()
    if clave in _SINONIMOS:
        return _SINONIMOS[clave]
    # Búsqueda parcial como último recurso
    for sinonimo, oficial in _SINONIMOS.items():
        if sinonimo in clave or clave in sinonimo:
            return oficial
    return nombre.strip()  # Devolver tal cual si no encontramos match


def alcaldia_por_coordenadas(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """
    Intenta asignar alcaldía usando bounding boxes aproximados.
    Si las coords caen en más de una bbox, retorna la primera coincidencia.
    Marcar resultado como 'estimado por coordenadas' al usarlo.
    """
    if lat is None or lon is None:
        return None
    for alcaldia, (lat_min, lat_max, lon_min, lon_max) in _BBOXES.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return alcaldia
    return None


def normalizar_y_completar(alcaldia: Optional[str],
                            lat: Optional[float],
                            lon: Optional[float]) -> Tuple[Optional[str], bool]:
    """
    Normaliza el nombre y, si queda None, intenta asignar por coordenadas.
    Retorna (alcaldia_final, fue_estimada_por_coords).
    """
    normalizada = normalizar_alcaldia(alcaldia)
    if normalizada:
        return normalizada, False
    # Fallback por coordenadas
    por_coords = alcaldia_por_coordenadas(lat, lon)
    if por_coords:
        return por_coords, True
    return None, False


# ── GeoJSON simplificado de perímetros de alcaldías ─────────────────────────
# Polígonos aproximados para visualización en Leaflet.
# No son los límites oficiales del INEGI. Solo para demo visual.
PERIMETROS_ALCALDIAS = {
    "Iztapalapa": [
        [19.420, -99.090], [19.420, -98.990], [19.310, -98.990],
        [19.310, -99.090], [19.420, -99.090]
    ],
    "Cuauhtémoc": [
        [19.470, -99.175], [19.470, -99.110], [19.400, -99.110],
        [19.400, -99.175], [19.470, -99.175]
    ],
    "Gustavo A. Madero": [
        [19.560, -99.160], [19.560, -99.060], [19.460, -99.060],
        [19.460, -99.160], [19.560, -99.160]
    ],
    "Álvaro Obregón": [
        [19.410, -99.290], [19.410, -99.180], [19.310, -99.180],
        [19.310, -99.290], [19.410, -99.290]
    ],
    "Tlalpan": [
        [19.370, -99.230], [19.370, -99.060], [19.150, -99.060],
        [19.150, -99.230], [19.370, -99.230]
    ],
    "Benito Juárez": [
        [19.410, -99.185], [19.410, -99.130], [19.355, -99.130],
        [19.355, -99.185], [19.410, -99.185]
    ],
    "Coyoacán": [
        [19.380, -99.185], [19.380, -99.090], [19.300, -99.090],
        [19.300, -99.185], [19.380, -99.185]
    ],
    "Miguel Hidalgo": [
        [19.470, -99.260], [19.470, -99.170], [19.400, -99.170],
        [19.400, -99.260], [19.470, -99.260]
    ],
    "Venustiano Carranza": [
        [19.460, -99.110], [19.460, -99.040], [19.400, -99.040],
        [19.400, -99.110], [19.460, -99.110]
    ],
    "Iztacalco": [
        [19.420, -99.110], [19.420, -99.060], [19.370, -99.060],
        [19.370, -99.110], [19.420, -99.110]
    ],
    "Azcapotzalco": [
        [19.520, -99.210], [19.520, -99.160], [19.460, -99.160],
        [19.460, -99.210], [19.520, -99.210]
    ],
    "Xochimilco": [
        [19.330, -99.130], [19.330, -99.000], [19.230, -99.000],
        [19.230, -99.130], [19.330, -99.130]
    ],
    "Tláhuac": [
        [19.360, -99.030], [19.360, -98.960], [19.240, -98.960],
        [19.240, -99.030], [19.360, -99.030]
    ],
    "Milpa Alta": [
        [19.270, -99.080], [19.270, -98.960], [19.130, -98.960],
        [19.130, -99.080], [19.270, -99.080]
    ],
    "La Magdalena Contreras": [
        [19.360, -99.280], [19.360, -99.190], [19.270, -99.190],
        [19.270, -99.280], [19.360, -99.280]
    ],
    "Cuajimalpa de Morelos": [
        [19.430, -99.340], [19.430, -99.240], [19.330, -99.240],
        [19.330, -99.340], [19.430, -99.340]
    ],
}
