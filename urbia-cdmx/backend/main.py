"""
URBIA CDMX — Servidor principal FastAPI
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .routers.api import router
from .routers.proyeccion import router as router_proyeccion
from .services.database import init_db, insert_reporte, insert_incidente, insert_fuente
from .services.priorizacion import agrupar_en_incidentes, recalcular_todos
from .data.demo_data import REPORTES_DEMO, FUENTES_DEMO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = FastAPI(
    title="URBIA CDMX",
    description=(
        "Plataforma inteligente de priorización y gestión de infraestructura urbana. "
        "Herramienta de apoyo a decisiones — no sustituye evaluación técnica ni institucional."
    ),
    version="0.1.0-mvp",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(router_proyeccion, prefix="/api")

# Servir archivos estáticos del frontend
static_path = os.path.join(FRONTEND_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"mensaje": "URBIA CDMX API activa. Visita /docs para la documentación."}


@app.on_event("startup")
def startup():
    """Inicializa la base de datos y carga datos de demostración si la BD está vacía."""
    init_db()

    # Cargar fuentes siempre (son metadata, no reportes)
    for f in FUENTES_DEMO:
        insert_fuente(f)

    # Cargar datos demo solo si la BD está vacía
    from .services.database import get_reportes
    reportes_existentes = get_reportes()
    if not reportes_existentes:
        for r in REPORTES_DEMO:
            insert_reporte(r)
        reportes_existentes = get_reportes()
        # Calcular incidentes para los datos demo
        from .services.priorizacion import agrupar_en_incidentes, recalcular_todos
        incidentes = agrupar_en_incidentes(reportes_existentes)
        calculados = recalcular_todos(incidentes)
        for inc in calculados:
            insert_incidente(inc)
        print(f"✅ URBIA CDMX iniciado — {len(reportes_existentes)} reportes demo, {len(calculados)} incidentes calculados.")
        print("⚠️  Datos de demostración cargados (ficticios). Ver sección Fuentes en la interfaz.")
    else:
        print(f"✅ URBIA CDMX iniciado — {len(reportes_existentes)} reportes en BD existente.")
