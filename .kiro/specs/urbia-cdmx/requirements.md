# URBIA CDMX — Documento de Requisitos

> Versión: 1.1 — MVP Hackathon  
> Fecha: Noviembre 2026  
> Estado: En implementación

---

## 1. Propósito

URBIA CDMX es una plataforma de apoyo a decisiones que transforma denuncias ciudadanas y datos públicos de la Ciudad de México en recomendaciones transparentes y justificadas de mantenimiento urbano.

**No es:** un sistema oficial de gobierno, un sustituto de evaluación de ingeniería, ni un emisor de órdenes de trabajo.

---

## 2. Usuarios objetivo

| Usuario | Necesidad principal |
|---------|-------------------|
| Tomador de decisiones (alcaldía/dependencia) | Ver qué calles requieren atención inmediata y por qué |
| Analista de infraestructura | Explorar datos, ajustar pesos, comparar escenarios |
| Ciudadano informado | Consultar estado de reportes y prioridades |
| Operador de campo | Saber qué recursos necesita una intervención |

---

## 3. Requisitos funcionales

### RF-01 — Carga de datos
- **RF-01.1** El sistema debe aceptar carga de archivos CSV con reportes de ciudadanos.
- **RF-01.2** El sistema debe intentar descargar datos oficiales de la CDMX (0311, C5, SACMEX).
- **RF-01.3** Si una fuente falla, el sistema debe operar con datos de demostración etiquetados como DEMO.
- **RF-01.4** Cada registro debe tener trazabilidad a su fuente original (nombre, URL, fecha de cobertura).
- **RF-01.5** Los datos personales de ciudadanos deben minimizarse (no exponer nombre, teléfono, etc.).

### RF-02 — Procesamiento de reportes
- **RF-02.1** El sistema debe agrupar reportes del mismo incidente por proximidad geográfica (<200m), misma categoría e intervalo temporal (<30 días).
- **RF-02.2** Los registros originales no deben eliminarse durante la agrupación.
- **RF-02.3** El sistema debe distinguir: (a) total de reportes, (b) incidentes únicos estimados, (c) reportes en incidentes abiertos.
- **RF-02.4** Reportes sin coordenadas deben marcarse como "ubicación no confirmada" y no aparecer en el mapa.
- **RF-02.5** El sistema debe clasificar reportes en tres categorías: hidráulica, vial, seguridad.

### RF-03 — Motor de priorización
- **RF-03.1** El sistema debe calcular: `PRIORIDAD = 0.30(S) + 0.25(D) + 0.20(M) + 0.15(A) + 0.10(R)`
- **RF-03.2** Cada variable debe normalizarse de 0 a 100 con criterios explícitos y documentados.
- **RF-03.3** El motor debe ser determinista: mismos inputs producen siempre el mismo output.
- **RF-03.4** Los pesos deben ser configurables desde la interfaz y el cambio debe recalcular el ranking.
- **RF-03.5** Las emergencias confirmadas deben escalar automáticamente a puntaje 100 sin depender del motor.
- **RF-03.6** Si faltan datos, el sistema debe mostrar puntaje provisional con nivel de confianza, sin asumir riesgo cero.

### RF-04 — Visualización geográfica
- **RF-04.1** El dashboard debe incluir un mapa interactivo con marcadores por nivel de prioridad.
- **RF-04.2** El mapa debe permitir filtrar por alcaldía y categoría.
- **RF-04.3** Cada marcador debe mostrar popup con: calle, alcaldía, puntaje, nivel de prioridad y justificación.
- **RF-04.4** Solo deben aparecer en el mapa los incidentes con coordenadas confirmadas.

### RF-05 — Dashboard y ranking
- **RF-05.1** El dashboard debe mostrar: total reportes, incidentes únicos, casos abiertos, casos críticos, emergencias activas, alcaldías analizadas.
- **RF-05.2** El ranking debe ordenar incidentes con emergencias primero, luego por puntaje descendente.
- **RF-05.3** Cada fila del ranking debe incluir justificación expandible con el detalle de cada variable.
- **RF-05.4** Los datos DEMO, históricos y no verificados deben etiquetarse visiblemente.

### RF-06 — Planeación operativa
- **RF-06.1** El sistema debe generar Plan A (mayor riesgo primero) y Plan B (mayor cobertura respetando presupuesto).
- **RF-06.2** El presupuesto debe ser ajustable desde la interfaz.
- **RF-06.3** Los costos estimados deben marcarse explícitamente como FICTICIOS/PROVISIONALES.
- **RF-06.4** Si no hay medidas de campo, indicar "requiere levantamiento técnico".

### RF-07 — Asistente URBIA AI
- **RF-07.1** El asistente debe responder preguntas sobre los datos cargados en el sistema.
- **RF-07.2** El asistente nunca debe generar cifras que no existan en la base de datos.
- **RF-07.3** Cada respuesta debe incluir fuente, fecha de corte y nivel de confianza.
- **RF-07.4** El asistente debe poder responder: vialidades urgentes, emergencias activas, intervenciones por presupuesto, autoridad competente.
- **RF-07.5** El asistente es la pantalla inicial del dashboard y sugiere el Mapa de Riesgo para ver más detalle.
- **RF-07.6** Las ubicaciones se muestran como `calle, Col. colonia, alcaldía`, sin textos `None` ni `?`.

> Detalle de RF-07.5 y RF-07.6 en `.kiro/specs/urbia-ai-asistente/requirements.md`.

### RF-08 — Normativa e institucionalidad
- **RF-08.1** El sistema debe incluir una matriz normativa referencial con leyes aplicables.
- **RF-08.2** El sistema debe sugerir dependencia competente solo cuando haya respaldo normativo.
- **RF-08.3** Debe existir el estado "competencia por determinar" para casos ambiguos.
- **RF-08.4** El sistema no debe emitir órdenes oficiales ni declarar emergencias públicas.

---

## 4. Requisitos no funcionales

### RNF-01 — Disponibilidad local
El sistema debe funcionar completamente offline con datos de demostración, sin requerir credenciales externas.

### RNF-02 — Transparencia
Toda recomendación debe incluir: fuente de datos, pesos usados, variables calculadas y nivel de confianza.

### RNF-03 — Separación de tipos de datos
Los datos DEMO, históricos y reales deben identificarse en cada registro y visualización.

### RNF-04 — Determinismo
El motor de priorización debe producir resultados idénticos para los mismos inputs, en cualquier orden de ejecución.

### RNF-05 — Extensibilidad AWS
La arquitectura debe permitir conectar Amazon Bedrock, S3 y DynamoDB sin reescribir la lógica de negocio.

### RNF-06 — Privacidad
Ninguna visualización pública debe exponer datos personales de ciudadanos denunciantes.

---

## 5. Criterios de aceptación (10 pruebas verificables)

| # | Criterio | Verificación |
|---|----------|-------------|
| CA-01 | Dos reportes del mismo incidente → 1 incidente único | `test_1_dos_reportes_mismo_incidente` |
| CA-02 | Emergencia confirmada → siempre primera en ranking | `test_2_emergencia_no_queda_relegada` |
| CA-03 | Reporte sin coords → no aparece en mapa con ubicación inventada | `test_3_sin_coordenadas_no_inventa_ubicacion` |
| CA-04 | Motor determinista | `test_4_motor_determinista` |
| CA-05 | Cambiar pesos → modifica resultados | `test_5_cambiar_pesos_modifica_resultado` |
| CA-06 | Datos históricos cerrados → no se marcan como abiertos | `test_6_datos_historicos_no_son_activos` |
| CA-07 | Costos → marcados como provisionales | `test_7_costos_marcados_como_provisionales` |
| CA-08 | Asistente → no inventa cifras ausentes | `test_8_asistente_no_inventa_cifras` |
| CA-09 | Fuentes → trazables con URL y nombre | `test_9_fuentes_trazables` |
| CA-10 | Sistema funciona con datos demo locales | `test_10_sistema_funciona_con_datos_demo` |

**Estado actual: 10/10 pasadas.**

---

## 6. Restricciones y supuestos

- Los datos del 0311 Locatel y C5 son **históricos** — no representan el estado actual de la infraestructura.
- La ponderación S/D/M/A/R es una **propuesta metodológica**, no una metodología oficial del GCDMX.
- Los costos unitarios del módulo de planeación son **ficticios** hasta que se realice levantamiento técnico.
- El sistema no tiene acceso a aforo vehicular real — usa indicadores sustitutos claramente identificados.
- Pronóstico meteorológico en tiempo real requiere integración con API externa (no incluida en MVP).
