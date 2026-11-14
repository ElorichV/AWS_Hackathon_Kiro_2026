"""
URBIA CDMX — Modelos de datos (Pydantic)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CategoriaEnum(str, Enum):
    hidraulica = "hidraulica"
    vial = "vial"
    seguridad = "seguridad"
    otro = "otro"


class PrioridadEnum(str, Enum):
    critica = "critica"
    alta = "alta"
    media = "media"
    baja = "baja"


class EstadoEnum(str, Enum):
    abierto = "abierto"
    en_proceso = "en_proceso"
    cerrado = "cerrado"
    emergencia = "emergencia"


class OrigenEnum(str, Enum):
    real = "real"
    demo = "demo"
    historico = "historico"


class Reporte(BaseModel):
    id: str
    fuente: str
    origen: OrigenEnum = OrigenEnum.demo
    fecha_reporte: Optional[str] = None
    alcaldia: Optional[str] = None
    colonia: Optional[str] = None
    calle: Optional[str] = None
    categoria: CategoriaEnum = CategoriaEnum.otro
    subcategoria: Optional[str] = None
    descripcion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    coords_confirmadas: bool = False
    estado: EstadoEnum = EstadoEnum.abierto
    es_emergencia: bool = False
    incidente_id: Optional[str] = None


class Incidente(BaseModel):
    id: str
    tipo: str
    categoria: CategoriaEnum
    alcaldia: Optional[str] = None
    colonia: Optional[str] = None
    calle: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    total_reportes: int = 1
    estado: EstadoEnum = EstadoEnum.abierto
    es_emergencia: bool = False
    fecha_primer_reporte: Optional[str] = None
    fecha_ultimo_reporte: Optional[str] = None
    puntaje_S: float = 0.0
    puntaje_D: float = 0.0
    puntaje_M: float = 0.0
    puntaje_A: float = 0.0
    puntaje_R: float = 0.0
    puntaje_total: float = 0.0
    nivel_prioridad: PrioridadEnum = PrioridadEnum.baja
    confianza: float = 1.0
    justificacion: Optional[str] = None
    origen: OrigenEnum = OrigenEnum.demo


class PesosMotor(BaseModel):
    peso_S: float = Field(default=0.30, ge=0, le=1, description="Seguridad y gravedad")
    peso_D: float = Field(default=0.25, ge=0, le=1, description="Frecuencia de denuncias")
    peso_M: float = Field(default=0.20, ge=0, le=1, description="Impacto en movilidad")
    peso_A: float = Field(default=0.15, ge=0, le=1, description="Antigüedad del incidente")
    peso_R: float = Field(default=0.10, ge=0, le=1, description="Riesgo de lluvia/ambiental")


class FuenteDatos(BaseModel):
    id: str
    nombre: str
    url: str
    licencia: Optional[str] = None
    fecha_cobertura: Optional[str] = None
    fecha_descarga: Optional[str] = None
    registros: Optional[int] = None
    disponible: bool = True
    notas: Optional[str] = None


class ResumenGeneral(BaseModel):
    total_reportes: int
    incidentes_unicos: int
    casos_abiertos: int
    casos_criticos: int
    casos_emergencia: int
    alcaldias_analizadas: int
    fecha_actualizacion: str
    advertencia_datos: str = "Los datos mostrados pueden incluir registros históricos o de demostración. Ver sección Fuentes."


class FiltrosReporte(BaseModel):
    alcaldia: Optional[str] = None
    colonia: Optional[str] = None
    categoria: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    nivel_prioridad: Optional[str] = None
    estado: Optional[str] = None
    solo_emergencias: bool = False
