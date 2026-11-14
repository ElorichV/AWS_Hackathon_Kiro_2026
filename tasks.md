# URBIA CDMX — Lista de Tareas

> Última actualización: inicio del proyecto  
> Estado general: 🔴 No iniciado

---

## FASE 1 — MVP Indispensable

### 1.1 Inicialización del proyecto
- [ ] Verificar entorno: Python, Node, npm, pip
- [ ] Instalar dependencias de backend: `fastapi`, `uvicorn`, `pandas`, `pydantic`, `requests`, `python-multipart`
- [ ] Instalar dependencias de frontend: React + TypeScript + Tailwind CSS + Leaflet
- [ ] Crear estructura de carpetas del proyecto (`/backend`, `/frontend`, `/data`, `/docs`)
- [ ] Crear `.env.example` con variables de entorno documentadas
- [ ] Crear `README.md` con instrucciones de instalación y ejecución

### 1.2 Esquema de datos
- [ ] Definir modelo `Reporte` (id, fuente, fecha, alcaldía, colonia, calle, categoría, descripción, coords, prioridad, estado)
- [ ] Definir modelo `Incidente` (id, reportes agrupados, tipo, coordenadas, puntaje, estado)
- [ ] Definir modelo `Fuente` (nombre, url, licencia, fecha_cobertura, fecha_descarga)
- [ ] Crear base de datos SQLite local con esquema inicial
- [ ] Cargar datos de demostración simulados (etiquetados como DEMO)

### 1.3 Carga de datos reales
- [ ] Intentar descargar dataset 0311 Locatel: https://www.datos.cdmx.gob.mx/dataset/0311
- [ ] Intentar descargar dataset Reportes de Agua: https://datos.cdmx.gob.mx/dataset/reportes-de-agua
- [ ] Intentar descargar dataset Incidentes Viales C5: https://datos.cdmx.gob.mx/dataset/incidentes-viales-c5
- [ ] Inspeccionar columnas y tipos de cada dataset descargado
- [ ] Registrar fuente, licencia, fechas y URL en catálogo interno
- [ ] Implementar endpoint `POST /upload-csv` para carga manual de archivos
- [ ] Si descarga falla, documentar motivo y activar fallback CSV

### 1.4 Motor de priorización
- [ ] Implementar cálculo de variable S (Seguridad y gravedad) — peso 30%
- [ ] Implementar cálculo de variable D (Frecuencia de denuncias, transformación logarítmica) — peso 25%
- [ ] Implementar cálculo de variable M (Impacto en movilidad/servicios) — peso 20%
- [ ] Implementar cálculo de variable A (Antigüedad del incidente abierto) — peso 15%
- [ ] Implementar cálculo de variable R (Exposición a lluvia/riesgo) — peso 10%
- [ ] Normalizar todas las variables de 0 a 100
- [ ] Calcular `PRIORIDAD = 0.30(S) + 0.25(D) + 0.20(M) + 0.15(A) + 0.10(R)`
- [ ] Implementar vía de escalamiento para emergencias (bypasa puntaje)
- [ ] Verificar que el motor es determinista (mismos inputs → mismo output)
- [ ] Exponer endpoint `GET /prioridades` con ranking ordenado
- [ ] Exponer endpoint `POST /recalcular` para modificar pesos y recalcular

### 1.5 Dashboard — Backend (API)
- [ ] Endpoint `GET /resumen` — totales: reportes, incidentes, abiertos, críticos, alcaldías
- [ ] Endpoint `GET /reportes` — con filtros por alcaldía, colonia, categoría, fecha, prioridad, estado
- [ ] Endpoint `GET /incidentes` — incidentes únicos agrupados
- [ ] Endpoint `GET /fuentes` — catálogo de fuentes de datos
- [ ] Documentación automática con Swagger UI (`/docs`)

### 1.6 Dashboard — Frontend
- [ ] Sección A: Resumen general (tarjetas con métricas clave)
- [ ] Sección B: Mapa de riesgo con Leaflet + OpenStreetMap
  - [ ] Marcadores por reporte
  - [ ] Agrupación de marcadores cercanos
  - [ ] Filtros por alcaldía, categoría y nivel de riesgo
  - [ ] Popup con detalle y justificación de prioridad
- [ ] Sección C: Ranking de prioridades (tabla ordenada con justificación)
- [ ] Etiqueta visible para datos DEMO / HISTÓRICO / NO VERIFICADO
- [ ] Diseño responsivo en español
- [ ] Integración con API del backend

### 1.7 Demostraciones reproducibles
- [ ] Demo 1: Cargar 50 reportes simulados de baches en Iztapalapa y ver ranking
- [ ] Demo 2: Simular lluvia fuerte y observar cambio de prioridades
- [ ] Demo 3: Marcar una emergencia y verificar que sube al tope sin importar puntaje

---

## FASE 2 — Inteligencia Artificial

### 2.1 Clasificación de reportes con IA
- [ ] Implementar clasificador determinista básico (sin Bedrock) como fallback
- [ ] Extraer: tipo de incidente, categoría, ubicación, fecha, gravedad, confianza
- [ ] Marcar ubicaciones ambiguas como "no confirmadas"
- [ ] Integrar Amazon Bedrock si hay credenciales AWS disponibles
- [ ] El modelo NO debe inventar puntajes — solo recibe resultados del motor

### 2.2 Deduplicación de incidentes
- [ ] Agrupar reportes por: proximidad geográfica + similitud semántica + tipo + intervalo temporal
- [ ] Mantener registros originales intactos (no eliminar)
- [ ] Distinguir: total reportes / incidentes únicos estimados / reportes en incidentes abiertos

### 2.3 Asistente URBIA AI
- [ ] Interfaz conversacional en Sección E del dashboard
- [ ] Conectar a funciones del backend para responder con datos reales
- [ ] Responder preguntas sobre vialidades urgentes, intervenciones, presupuesto, competencia
- [ ] Incluir fuente, fecha de corte y nivel de confianza en cada respuesta importante
- [ ] El asistente nunca genera cifras que no estén en la base de datos

---

## FASE 3 — Planeación Operativa

### 3.1 Inventario de recursos
- [ ] Crear catálogo de recursos (cuadrillas, vehículos, equipos, materiales, presupuesto)
- [ ] Marcar explícitamente como valores FICTICIOS y editables
- [ ] Permitir edición desde la interfaz

### 3.2 Fichas de intervención
- [ ] Generar ficha por incidente: tipo de trabajo, recursos, materiales, duración, costo estimado
- [ ] Marcar costos como PROVISIONALES
- [ ] Si no hay medidas, indicar "requiere levantamiento en campo"

### 3.3 Optimización de planes
- [ ] Implementar Plan A: atender los de mayor riesgo
- [ ] Implementar Plan B: mayor cobertura respetando presupuesto y capacidad
- [ ] Algoritmo de selección bajo restricciones (knapsack simplificado)
- [ ] Comparador visual de Plan A vs Plan B en el dashboard (Sección D)

### 3.4 Marco normativo
- [ ] Construir matriz normativa: Ley de Movilidad, Gestión de Riesgos, Obras Públicas, Protección de Datos
- [ ] Registrar: nombre oficial, artículo, fecha, URL, aplicabilidad al módulo
- [ ] Diferenciar: obligación legal / recomendación técnica / criterio propuesto / supuesto de demo
- [ ] Proponer dependencia competente solo cuando hay respaldo normativo
- [ ] Permitir estado "competencia por determinar"

---

## FASE 4 — Integración AWS

- [ ] Abstraer servicios AWS detrás de una capa de interfaces intercambiables
- [ ] Integrar Amazon Bedrock para clasificación y explicaciones (si hay credenciales)
- [ ] Migrar almacenamiento a Amazon S3 (opcional)
- [ ] Desplegar con AWS Lambda o EC2
- [ ] Configurar CloudWatch para observabilidad
- [ ] No declarar conexión AWS activa si no existe

---

## PRUEBAS AUTOMATIZADAS

- [ ] Test 1: Dos reportes del mismo incidente no cuentan como dos daños distintos
- [ ] Test 2: Emergencia confirmada no queda relegada por puntaje bajo
- [ ] Test 3: Reporte sin coordenadas no aparece en ubicación inventada
- [ ] Test 4: Motor produce resultados deterministas
- [ ] Test 5: Cambiar pesos modifica correctamente el ranking
- [ ] Test 6: Datos históricos no se muestran como incidentes actualmente abiertos
- [ ] Test 7: Estimaciones de costo se identifican como provisionales
- [ ] Test 8: El asistente no genera cifras ausentes en la base de datos
- [ ] Test 9: Fuentes legales son trazables desde la interfaz
- [ ] Test 10: Sistema funciona localmente con datos de demostración

---

## ENTREGABLES FINALES

- [ ] `requirements.md` — documento de requisitos
- [ ] `design.md` — diseño técnico
- [ ] `tasks.md` — este archivo ✅
- [ ] Código fuente funcional (backend + frontend)
- [ ] Datos de demostración + datos reales importados (si disponibles)
- [ ] `README.md` con instrucciones exactas
- [ ] Suite de pruebas automatizadas
- [ ] `.env.example`
- [ ] Documentación de fuentes y normativa
- [ ] Guion de demostración de 3 minutos

---

## ESTADO ACTUAL

| Fase | Estado |
|------|--------|
| Fase 1 — MVP | ✅ COMPLETA |
| Fase 2 — IA | ✅ Asistente determinista completo (sin Bedrock) |
| Fase 3 — Operativa | ✅ Simulador de recursos + Plan A / Plan B |
| Fase 4 — AWS | ⬜ Pendiente (capa de abstracción lista) |

---

## ✅ LO QUE ESTÁ FUNCIONANDO AHORA

**Servidor activo:** http://localhost:8000

### Backend (FastAPI + SQLite)
- [x] Base de datos SQLite inicializada
- [x] 20 reportes demo cargados (10 alcaldías)
- [x] 13 incidentes únicos calculados por agrupación geográfica
- [x] Motor de priorización `PRIORIDAD = 0.30(S) + 0.25(D) + 0.20(M) + 0.15(A) + 0.10(R)`
- [x] Emergencias escaladas automáticamente (puntaje 100, primeras en ranking)
- [x] Endpoints: `/api/resumen`, `/api/incidentes`, `/api/reportes`, `/api/mapa`, `/api/fuentes`, `/api/normativa`
- [x] Recálculo con pesos personalizados: `POST /api/recalcular`
- [x] Carga de CSV: `POST /api/upload-csv`
- [x] Asistente URBIA AI: `POST /api/chat`
- [x] Documentación Swagger: http://localhost:8000/docs

### Frontend (HTML + JS + Leaflet)
- [x] Dashboard responsivo en español
- [x] Sección A: Resumen con 6 métricas + gráficas de barras por categoría y alcaldía
- [x] Sección B: Mapa Leaflet + OpenStreetMap con marcadores por nivel de riesgo
- [x] Sección C: Ranking con puntajes, justificaciones expandibles y ajuste de pesos
- [x] Sección D: Planeación con Plan A / Plan B y slider de presupuesto
- [x] Sección E: Chat con URBIA AI y preguntas sugeridas
- [x] Sección F: Catálogo de fuentes y matriz normativa
- [x] Carga de CSV desde la interfaz

### Pruebas
- [x] 10/10 pruebas de aceptación pasadas

---

## ⏳ PENDIENTE

### Datos reales
- [ ] Descargar y validar dataset 0311 Locatel
- [ ] Descargar y validar Reportes de Agua SACMEX
- [ ] Descargar y validar Incidentes Viales C5
- [ ] Integrar Atlas de Riesgo de Inundaciones

### Fase 4 — AWS
- [ ] Integrar Amazon Bedrock (si hay credenciales)
- [ ] Migrar a S3 / DynamoDB (opcional)
- [ ] Despliegue en Lambda o EC2
- [ ] CloudWatch para observabilidad

**Para arrancar:** `bash start.sh` desde la carpeta `urbia-cdmx/`
