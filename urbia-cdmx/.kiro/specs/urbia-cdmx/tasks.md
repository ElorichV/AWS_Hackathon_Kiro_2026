# URBIA CDMX — Lista de Tareas (Spec Tasks)

> Última actualización: Noviembre 2026 (v1.1)  
> Vinculado a: requirements.md, design.md

---

## FASE 1 — MVP Indispensable ✅ COMPLETA

### 1.1 Inicialización del proyecto ✅
- [x] Verificar entorno: Python 3.9, pip disponibles
- [x] Instalar dependencias: fastapi, uvicorn, pandas, pydantic, requests, python-multipart
- [x] Crear estructura de carpetas (backend, frontend, tests, docs, .kiro/specs)
- [x] Crear `.env.example`
- [x] Crear `README.md` con instrucciones exactas
- [x] Crear `start.sh`

### 1.2 Esquema de datos ✅
- [x] Modelo `Reporte` con todos los campos requeridos (Pydantic + SQLite)
- [x] Modelo `Incidente` con puntajes, justificación y nivel de confianza
- [x] Modelo `FuenteDatos` con trazabilidad completa
- [x] Inicialización automática de SQLite en startup
- [x] 20 registros de demostración ficticios cargados y etiquetados

### 1.3 Carga de datos ✅
- [x] Columnas verificadas: Locatel 0311, Incidentes Viales C5
- [x] Importador `locatel` → categoriza por tema_solicitud, descarta datos personales
- [x] Importador `c5` → solo registros Afirmativos (confirmados en campo)
- [x] Endpoint `POST /api/upload-csv` con validación
- [x] Endpoint `POST /api/importar-real` para descarga automática
- [x] Fallback a datos DEMO si falla la descarga
- [x] Datos reales descargados e importados: 5,000 registros Locatel 2023 + 3,000 registros C5 2022-2024 (+20 demo = 8,020 reportes, 6,577 incidentes)
- [x] Normalización de alcaldías y estimación por coordenadas (`services/alcaldias.py`)

### 1.4 Motor de priorización ✅
- [x] Variable S: seguridad y gravedad (8 niveles definidos)
- [x] Variable D: frecuencia logarítmica `log(n+1)/log(51)×100`
- [x] Variable M: impacto en movilidad con indicadores sustitutos
- [x] Variable A: antigüedad en días desde primer reporte abierto
- [x] Variable R: peligrosidad histórica de inundación + tipo hidráulico
- [x] Normalización 0–100 de todas las variables
- [x] Fórmula `PRIORIDAD = 0.30(S) + 0.25(D) + 0.20(M) + 0.15(A) + 0.10(R)`
- [x] Escalamiento de emergencias (puntaje 100, independiente del motor)
- [x] Motor determinista verificado
- [x] Pesos configurables + endpoint recalcular
- [x] Justificación textual por variable para cada incidente

### 1.5 API Backend ✅
- [x] `GET /api/resumen`
- [x] `GET /api/incidentes` con filtros
- [x] `GET /api/reportes` con filtros
- [x] `GET /api/mapa` (solo con coords confirmadas)
- [x] `GET /api/alcaldias`
- [x] `GET /api/fuentes`
- [x] `GET /api/normativa`
- [x] `POST /api/recalcular`
- [x] `POST /api/chat`
- [x] `POST /api/upload-csv`
- [x] `POST /api/importar-real`
- [x] Swagger UI en `/docs`

### 1.6 Dashboard Frontend ✅
- [x] Sección A: Resumen (6 métricas + gráficas de barras)
- [x] Sección B: Mapa Leaflet + OpenStreetMap
  - [x] Marcadores por nivel de riesgo (rojo/naranja/amarillo/verde)
  - [x] Emergencias con animación de pulso
  - [x] Filtros por alcaldía y categoría
  - [x] Popup con detalle completo
- [x] Sección C: Ranking de prioridades
  - [x] Tabla con barra de puntaje visual
  - [x] Justificación expandible por incidente
  - [x] Ajuste de pesos con sliders + recalcular
  - [x] Filtros por alcaldía, categoría, nivel
- [x] Sección D: Planeación (Plan A vs Plan B, slider de presupuesto)
- [x] Sección E: URBIA AI (chat + preguntas sugeridas), ahora es la pantalla inicial (ver spec `urbia-ai-asistente`)
- [x] Mejoras del mapa: leyenda de niveles, perímetros de alcaldías, filtros multinivel, explicación del motor
- [x] Sección F: Fuentes y normativa
- [x] Sección carga de CSV
- [x] Etiquetas DEMO / HISTÓRICO / Real visibles
- [x] Dashboard responsivo en español

### 1.7 Demostraciones reproducibles ✅
- [x] Demo 1: 20 reportes demo cargados automáticamente al iniciar → ver ranking
- [x] Demo 2: Ajustar peso R (lluvia) a 40% → observar cambio en incidentes hidráulicos
- [x] Demo 3: Emergencia Av. Doctores → siempre primera con puntaje 100

---

## FASE 2 — Inteligencia Artificial ✅ COMPLETA (determinista)

### 2.1 Clasificación de reportes ✅
- [x] Clasificador determinista por palabras clave (sin Bedrock)
- [x] Mapeo de temas Locatel → categoría/subcategoría URBIA
- [x] Mapeo de incidentes C5 → categoría/subcategoría URBIA
- [x] Marcado de coords no confirmadas
- [ ] Integrar Amazon Bedrock (Fase 4, si hay credenciales)

### 2.2 Deduplicación ✅
- [x] Agrupación por: distancia <200m + misma categoría + intervalo <30 días
- [x] Registros originales preservados
- [x] Distinción: total reportes / incidentes únicos / reportes en abiertos

### 2.3 Asistente URBIA AI ✅
- [x] Interfaz de chat en el dashboard
- [x] Responde: vialidades urgentes, emergencias, coladeras, presupuesto, autoridad, resumen
- [x] Respuestas basadas en datos reales de la BD (nunca inventadas)
- [x] Fuente + confianza + fecha de corte en cada respuesta
- [x] Preguntas sugeridas en la interfaz

---

## FASE 3 — Planeación Operativa ✅ COMPLETA (simulador)

### 3.1 Simulador de recursos ✅
- [x] Catálogo ficticio de cuadrillas, presupuesto, costos unitarios
- [x] Marcado explícito como FICTICIO en datos y UI
- [ ] Edición desde interfaz (pendiente — mejora futura)

### 3.2 Fichas de intervención ✅
- [x] Costo estimado por tipo de incidente (ficticio, referencial)
- [x] Marcado como PROVISIONAL en la UI
- [ ] Generación de PDF por intervención (mejora futura)

### 3.3 Optimización Plan A / Plan B ✅
- [x] Plan A: mayor riesgo hasta agotar presupuesto
- [x] Plan B: mayor cobertura (menor costo primero, emergencias siempre incluidas)
- [x] Slider de presupuesto ajustable
- [x] Comparativa visual en el dashboard

### 3.4 Marco normativo ✅
- [x] Matriz de 4 leyes aplicables (referencial)
- [x] Diferenciación: obligación legal / recomendación / criterio propuesto
- [x] Dependencia competente sugerida por tipo de infraestructura
- [x] Estado "competencia por determinar" disponible

---

## FASE 4 — Integración AWS ⏳ PENDIENTE

- [ ] Verificar credenciales AWS disponibles
- [ ] Integrar Amazon Bedrock para clasificación y explicaciones
- [ ] Migrar almacenamiento a Amazon S3
- [ ] Configurar DynamoDB como alternativa a SQLite
- [ ] Desplegar con AWS Lambda o EC2
- [ ] Configurar CloudWatch para logs y métricas
- [ ] Implementar capa de abstracción AWS/local intercambiable

---

## PRUEBAS AUTOMATIZADAS ✅ 10/10

- [x] Test 1: Dos reportes mismo incidente → 1 único ✅
- [x] Test 2: Emergencia → siempre primera ✅
- [x] Test 3: Sin coords → no inventa ubicación ✅
- [x] Test 4: Motor determinista ✅
- [x] Test 5: Cambiar pesos → modifica resultados ✅
- [x] Test 6: Histórico cerrado → no marca como abierto ✅
- [x] Test 7: Costos marcados como ficticios ✅
- [x] Test 8: Asistente no inventa cifras ✅
- [x] Test 9: Fuentes trazables ✅
- [x] Test 10: Funciona con datos demo ✅

---

## ENTREGABLES ✅

- [x] `requirements.md` — este documento
- [x] `design.md` — diseño técnico
- [x] `tasks.md` — esta lista
- [x] Código fuente funcional (backend + frontend)
- [x] Datos de demostración (20 registros)
- [x] Importadores de datos reales (Locatel + C5)
- [x] `README.md` con instrucciones
- [x] Suite de 10 pruebas automatizadas
- [x] `.env.example`
- [x] Guion de demostración de 3 minutos (en README)
- [x] Datos reales importados (8,000 registros reales)
- [ ] Documentación de normativa completa (parcial en `/api/normativa`)

---

## BLOQUEADORES ACTIVOS

| Bloqueador | Causa | Solución |
|-----------|-------|---------|
| Terminal en estado `dquote` | Resuelto — se usó script Python directo | ✅ Resuelto |
| Datos reales no cargados en BD | Resuelto — importador corregido y ejecutado | ✅ Resuelto |

---

## PENDIENTES DE DATOS (detalle en spec `urbia-ai-asistente`, tarea 5)

- [ ] Quitar duplicados en tabla `fuentes` (FUENTE-001 y FUENTE-003)
- [ ] Recuperar calle/colonia: hoy solo 13 de 6,577 incidentes tienen calle y 2,220 colonia
- [ ] Quitar el aviso de "datos ficticios" de la UI cuando hay datos reales

---

## PRÓXIMOS PASOS (post-hackathon)

1. Integrar dataset Reportes de Agua (SACMEX)
2. Integrar Atlas de Riesgo de Inundaciones (GeoJSON)
3. Conectar API meteorológica para variable R en tiempo real
4. Agregar autenticación básica para panel de administración
5. Despliegue en AWS (Fase 4)
6. Levantamiento de costos reales con instituciones competentes
