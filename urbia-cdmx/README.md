# URBIA CDMX — MVP v0.1

**Plataforma Inteligente de Priorización, Proyección y Gestión de Infraestructura Urbana**

> ⚠️ Esta es una herramienta de apoyo a decisiones. No sustituye la evaluación técnica de ingeniería ni la autoridad de las instituciones públicas.

---

## Inicio rápido

### En Linux / macOS / Git Bash
```bash
cd "urbia-cdmx"
bash start.sh
```

### En Windows (PowerShell)
```powershell
cd "urbia-cdmx"
python -m pip install fastapi uvicorn pydantic requests python-multipart
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Abre en el navegador: **http://localhost:8000** (Swagger UI en **http://localhost:8000/docs**).  
Requisito mínimo: **Python 3.9+**

---

## Estructura del proyecto

```text
urbia-cdmx/
├── .kiro/
│   └── specs/                # Especificaciones Kiro (urbia-cdmx y urbia-ai-asistente)
├── backend/
│   ├── main.py               # Servidor FastAPI
│   ├── models/schemas.py     # Modelos Pydantic
│   ├── routers/
│   │   ├── api.py            # Endpoints principales de la API
│   │   └── proyeccion.py     # Endpoints de proyección futura (30/90/180 días)
│   ├── services/
│   │   ├── database.py       # Capa SQLite
│   │   ├── priorizacion.py   # Motor de priorización S-D-M-A-R
│   │   ├── proyeccion.py     # Motor de proyección de afectaciones futuras
│   │   ├── asistente.py      # URBIA AI
│   │   ├── alcaldias.py      # Normalización y perímetros de las 16 alcaldías
│   │   └── importador.py     # Importador de datos abiertos CDMX (Locatel y C5)
│   └── data/
│       ├── demo_data.py      # Datos semilla y catálogos
│       └── urbia.db          # Base SQLite (8,000 reportes históricos + 20 demo)
├── frontend/
│   ├── index.html            # Dashboard principal SPA
│   └── static/js/app.js      # Lógica del frontend
├── scripts/
│   ├── run_import.py         # Script de importación de datos abiertos
│   └── setup_and_import.py   # Inicialización e importación
├── tests/
│   └── test_motor.py         # Suite de 10 pruebas de aceptación
├── start.sh                  # Script de inicio
├── .env.example              # Variables de entorno de ejemplo
└── README.md
```

---

## API — Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/resumen` | Totales generales y advertencia de origen de datos |
| GET | `/api/incidentes` | Ranking de incidentes por prioridad |
| GET | `/api/reportes` | Lista de reportes con filtros |
| GET | `/api/mapa` | Datos para el mapa (con coordenadas confirmadas) |
| POST | `/api/recalcular` | Recalcular con pesos personalizados |
| POST | `/api/chat` | Asistente URBIA AI |
| GET | `/api/proyeccion` | Proyección de riesgo histórico a 30, 90 y 180 días |
| GET | `/api/proyeccion/resumen` | Resumen de proyección, backtest y limitaciones |
| GET | `/api/proyeccion/zona/{id}` | Detalle e historial de una celda o colonia |
| POST | `/api/upload-csv` | Cargar reportes desde CSV |
| POST | `/api/importar-real` | Importar datos oficiales de Locatel 0311 y C5 |
| GET | `/api/fuentes` | Catálogo de fuentes |
| GET | `/api/normativa` | Marco normativo referencial |
| GET | `/docs` | Documentación Swagger interactiva |

---

## Motor de priorización

```text
PRIORIDAD = 0.30(S) + 0.25(D) + 0.20(M) + 0.15(A) + 0.10(R)
```

| Variable | Descripción | Rango |
|----------|-------------|-------|
| S | Seguridad y gravedad | 0–100 |
| D | Frecuencia de denuncias (transformación log) | 0–100 |
| M | Impacto en movilidad/servicios | 0–100 |
| A | Antigüedad del incidente abierto | 0–100 |
| R | Exposición a riesgo de lluvia/ambiental | 0–100 |

> Los pesos son **configurables desde la interfaz**. Las **emergencias confirmadas** siempre aparecen primero con puntaje 100.

---

## Pruebas automatizadas

```bash
cd urbia-cdmx
python tests/test_motor.py
```
