# URBIA CDMX — Diseño Técnico

> Versión: 1.1 — MVP Hackathon  
> Fecha: Noviembre 2026

---

## 1. Visión de arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGADOR / CLIENTE                   │
│         HTML + Vanilla JS + Leaflet (OpenStreetMap)      │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP / JSON
┌─────────────────────▼───────────────────────────────────┐
│                  BACKEND — FastAPI (Python)               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Router  │  │   Servicios  │  │   Capa de datos   │  │
│  │  /api/*  │  │ priorizacion │  │   SQLite (dev)    │  │
│  │          │  │  asistente   │  │   PostgreSQL(prod)│  │
│  │          │  │  importador  │  │                   │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────┘
                      │ (opcional)
┌─────────────────────▼───────────────────────────────────┐
│                  SERVICIOS AWS (opcionales)               │
│   Amazon Bedrock │ S3 │ DynamoDB │ Lambda │ CloudWatch   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Estructura de archivos

```
urbia-cdmx/
├── .kiro/
│   └── specs/urbia-cdmx/
│       ├── requirements.md   ← este archivo
│       ├── design.md
│       └── tasks.md
├── backend/
│   ├── __init__.py
│   ├── main.py               ← FastAPI app + startup
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        ← Pydantic models
│   ├── routers/
│   │   ├── __init__.py
│   │   └── api.py            ← Todos los endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py       ← Capa SQLite (CRUD)
│   │   ├── priorizacion.py   ← Motor de priorización
│   │   ├── asistente.py      ← URBIA AI
│   │   ├── alcaldias.py      ← Normalización, bbox y perímetros de alcaldías
│   │   └── importador.py     ← Importación de datos reales
│   └── data/
│       ├── __init__.py
│       ├── demo_data.py      ← 20 registros ficticios
│       └── urbia.db          ← SQLite (auto-generado)
├── frontend/
│   ├── index.html            ← Dashboard SPA
│   └── static/js/app.js     ← Lógica frontend
├── tests/
│   └── test_motor.py         ← 10 pruebas de aceptación
├── docs/
├── start.sh
├── .env.example
└── README.md
```

---

## 3. Modelos de datos

### Reporte (tabla: reportes)
```
id                  TEXT PK
fuente              TEXT         — nombre de la fuente
origen              TEXT         — 'real' | 'demo' | 'historico'
fecha_reporte       TEXT         — YYYY-MM-DD
alcaldia            TEXT
colonia             TEXT
calle               TEXT
categoria           TEXT         — 'vial' | 'hidraulica' | 'seguridad' | 'otro'
subcategoria        TEXT         — bache, coladera_obstruida, etc.
descripcion         TEXT
latitud             REAL         — None si no confirmada
longitud            REAL         — None si no confirmada
coords_confirmadas  INTEGER      — 0 | 1
estado              TEXT         — 'abierto' | 'en_proceso' | 'cerrado' | 'emergencia'
es_emergencia       INTEGER      — 0 | 1
incidente_id        TEXT FK → incidentes.id
created_at          TEXT
```

### Incidente (tabla: incidentes)
```
id                  TEXT PK      — INC-{reporte_semilla_id}
tipo                TEXT         — subcategoría del reporte semilla
categoria           TEXT
alcaldia / colonia / calle
latitud / longitud               — del reporte semilla
total_reportes      INTEGER      — cantidad de reportes agrupados
estado              TEXT
es_emergencia       INTEGER
fecha_primer_reporte TEXT
fecha_ultimo_reporte TEXT
puntaje_S/D/M/A/R   REAL         — 0.0 – 100.0 cada una
puntaje_total       REAL         — 0.0 – 100.0
nivel_prioridad     TEXT         — 'critica'|'alta'|'media'|'baja'
confianza           REAL         — 0.1 – 1.0
justificacion       TEXT         — texto explicativo completo
origen              TEXT
updated_at          TEXT
```

---

## 4. Motor de priorización — detalle

### Fórmula
```
PRIORIDAD = 0.30·S + 0.25·D + 0.20·M + 0.15·A + 0.10·R
```

### Variable S — Seguridad y gravedad

| Condición | Puntaje |
|-----------|---------|
| Emergencia confirmada | 100 (escalamiento directo) |
| Vialidad bloqueada / inundación | 85 |
| Hundimiento | 75 |
| Categoría seguridad | 70 |
| Bache / grieta / pavimento | 50 |
| Coladera / drenaje | 45 |
| Encharcamiento | 40 |
| Desconocido | 30 (provisional) |

### Variable D — Frecuencia de denuncias
```
D = min(100, (log(n+1) / log(51)) × 100)
```
Transformación logarítmica para evitar que volúmenes muy altos dominen.  
Referencia: 50 reportes = D≈100; 1 reporte = D≈5.

### Variable M — Impacto en movilidad
Indicadores sustitutos (sin aforo vehicular disponible):

| Condición | Puntos |
|-----------|--------|
| Base | 20 |
| Vialidad primaria (IPN, Insurgentes, Eje Central…) | +40 |
| Subcategoría de alto impacto (bloqueo, inundación, hundimiento) | +30 |
| Alcaldía de alta densidad (Iztapalapa, Cuauhtémoc…) | +10 |

### Variable A — Antigüedad del incidente abierto
```
A = min(100, (días_desde_primer_reporte / 365) × 100)
```
Mide tiempo transcurrido desde el primer reporte del incidente, no la edad de un registro histórico.

### Variable R — Riesgo de lluvia/ambiental

| Condición | Puntos |
|-----------|--------|
| Base | 10 |
| Alcaldía en zona de peligrosidad histórica de inundación | +40 |
| Categoría hidráulica | +30 |
| Subcategoría inundación o encharcamiento | +20 |

> Pronóstico meteorológico vigente no integrado (requiere API). Puntaje basado en historial referencial.

### Niveles de prioridad
```
puntaje ≥ 70  →  CRÍTICA
puntaje ≥ 50  →  ALTA
puntaje ≥ 30  →  MEDIA
puntaje < 30  →  BAJA
```

### Confianza
```
confianza = 1.0
  - 0.3 si coords_confirmadas = False
  - 0.1 si fecha_primer_reporte es None
  mínimo: 0.1
```

---

## 5. Agrupación de incidentes

### Criterios de agrupación (AND)
1. Distancia < 200 metros (Haversine)
2. Misma categoría
3. Intervalo entre reportes < 30 días

### Reglas
- El reporte semilla es el de mayor gravedad (emergencia > cualquier otro)
- Los registros originales NO se eliminan
- Si un reporte tiene latitud/longitud = None → no participa en agrupación geográfica pero sí se carga como incidente individual sin coords

---

## 6. API — Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/resumen | Totales generales |
| GET | /api/incidentes | Ranking ordenado (filtros opcionales) |
| GET | /api/reportes | Lista de reportes (filtros opcionales) |
| GET | /api/mapa | Incidentes con coords para Leaflet |
| GET | /api/alcaldias | Lista de alcaldías con datos |
| GET | /api/fuentes | Catálogo de fuentes |
| GET | /api/normativa | Marco normativo referencial |
| POST | /api/recalcular | Recalcular con pesos personalizados |
| POST | /api/chat | Asistente URBIA AI |
| POST | /api/upload-csv | Carga masiva desde archivo |
| POST | /api/importar-real | Descargar e importar datos oficiales CDMX |
| GET | /docs | Swagger UI |

---

## 7. Frontend — Secciones del dashboard

| Sección | Componentes clave |
|---------|------------------|
| A — Resumen | 6 tarjetas de métricas + 2 gráficas de barras |
| B — Mapa de Riesgo | Leaflet + OpenStreetMap, marcadores por nivel, filtros |
| C — Ranking | Tabla ordenada, puntajes con barra visual, justificación expandible, ajuste de pesos |
| D — Planeación | Plan A vs Plan B, slider de presupuesto, costos ficticios marcados |
| E — URBIA AI (pantalla inicial) | Chat conversacional, preguntas sugeridas, respuestas con fuente/confianza, sugerencia al mapa |
| F — Fuentes | Catálogo de fuentes con estado (disponible/no), normativa referencial |
| Carga | Upload CSV con validación, formato esperado |

---

## 8. Fuentes de datos integradas

| Fuente | URL | Cobertura | Estado MVP |
|--------|-----|-----------|-----------|
| 0311 Locatel 2023 | archivo.datos.cdmx.gob.mx (SUAC) | 2023 (histórico) | ✅ 5,000 registros importados |
| Incidentes Viales C5 2022-2024 | https://archivo.datos.cdmx.gob.mx/C5/incidentes_viales/inViales_2022_2024.csv | 2022-2024 (histórico) | ✅ 3,000 registros importados |
| Datos DEMO URBIA | local | n/a | ✅ 20 registros cargados |
| Reportes de Agua SACMEX | https://datos.cdmx.gob.mx/dataset/reportes-de-agua | Pendiente | ⏳ Fase 2 |
| Atlas Riesgo Inundaciones | https://www.datos.cdmx.gob.mx/es/dataset/atlas-de-riesgo-inundaciones | Histórico | ⏳ Fase 2 |

### Columnas verificadas

**Locatel 0311:**
`id_folio, fecha_solicitud, hora_solicitud, tipo_de_entrada, tema_solicitud, estatus, fecha_concluido, alcaldia, colonia_datos, 0311_colonia_registro, latitud, longitud`
(sexo y edad descartados por privacidad)

**Incidentes Viales C5:**
`folio, fecha_creacion, hora_creacion, dia_semana, fecha_cierre, tipo_incidente_c4, incidente_c4, alcaldia_inicio, codigo_cierre, alcaldia_catalogo, colonia_catalogo, longitud, latitud`

---

### Calidad de ubicación (base actual)

| Campo | Incidentes con dato | De 6,577 |
|-------|--------------------|----------|
| calle | 13 | 0.2% |
| colonia | 2,220 | 34% |
| coordenadas | 3,491 | 53% |

Los importadores guardan `calle = None`. Plan de mejora en `.kiro/specs/urbia-ai-asistente/design.md`.

---

## 9. Integración AWS (Fase 4)

La capa de servicios está diseñada para ser reemplazada sin tocar la lógica de negocio:

| Servicio actual | Reemplazo AWS |
|----------------|--------------|
| SQLite | DynamoDB o RDS/PostGIS |
| Clasificador determinista | Amazon Bedrock (Claude) |
| Almacenamiento local de CSVs | Amazon S3 |
| Proceso local | AWS Lambda |
| Logs en archivo | CloudWatch |

**Principio:** el motor de priorización nunca delega el cálculo al LLM. Bedrock solo se usa para explicaciones en lenguaje natural, recibiendo los puntajes ya calculados.

---

## 10. Decisiones técnicas tomadas

| Decisión | Alternativa descartada | Razón |
|----------|----------------------|-------|
| HTML + Vanilla JS (sin React/npm) | React + TypeScript | Node.js no instalado en el entorno; más rápido para hackathon |
| SQLite | PostgreSQL/PostGIS | Simplicidad para MVP local; migración trivial |
| Clasificador determinista | Solo Bedrock | Funcionar sin credenciales AWS |
| Haversine simplificado | GeoPandas | No requiere instalación de GDAL |
| Agrupación por 200m + 30 días | ML de clustering | Determinista, explicable, suficiente para MVP |
