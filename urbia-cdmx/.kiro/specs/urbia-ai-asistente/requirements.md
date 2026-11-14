# URBIA AI — Asistente como pantalla principal — Requisitos

> Spec de funcionalidad. Complementa `.kiro/specs/urbia-cdmx/` (spec principal).
> Estado: En implementación

## Introducción

URBIA AI es el asistente conversacional del dashboard. Esta funcionalidad lo convierte en la primera pantalla que ve el usuario, mejora la forma en que describe ubicaciones y lo hace dirigir al usuario hacia el Mapa de Riesgo cuando necesita más detalle.

Hallazgo que motiva el spec: en la base actual (6,577 incidentes) solo 13 tienen calle, 2,220 tienen colonia y 3,491 tienen coordenadas. Las respuestas mostraban `None (Cuauhtémoc)` porque los importadores de Locatel y C5 guardan `calle = None`.

## Requisitos

### Requisito 1 — El chat es la pantalla inicial

**Historia de usuario:** Como tomador de decisiones, quiero que lo primero que vea al abrir URBIA sea el asistente, para poder preguntar directamente sin navegar por el dashboard.

#### Criterios de aceptación

1. WHEN el usuario abre `http://localhost:8000` THEN el sistema SHALL mostrar la sección URBIA AI como sección activa.
2. WHEN se carga la página THEN el menú lateral SHALL mostrar "URBIA AI" como primer elemento, antes de "Resumen".
3. WHEN se carga la página THEN el título de la barra superior SHALL decir "URBIA AI — Asistente".
4. WHEN se carga la página THEN el sistema SHALL mostrar las preguntas sugeridas sin que el usuario haga clic.

### Requisito 2 — El asistente sugiere el mapa

**Historia de usuario:** Como analista, quiero que el asistente me indique dónde ver más detalle, para pasar de una respuesta de texto a la vista geográfica.

#### Criterios de aceptación

1. WHEN se muestra el mensaje de bienvenida THEN el sistema SHALL mencionar la sección "Mapa de Riesgo".
2. WHEN el asistente responde con una lista de incidentes (urgentes, hidráulicos, emergencias, presupuesto) THEN la respuesta SHALL terminar con una sugerencia de abrir el Mapa de Riesgo.
3. WHEN el usuario hace clic en la sugerencia del mapa THEN el sistema SHALL navegar a la sección Mapa de Riesgo.

### Requisito 3 — Ubicaciones legibles

**Historia de usuario:** Como operador de campo, quiero ver ubicaciones comprensibles en las respuestas, para saber a dónde ir.

#### Criterios de aceptación

1. WHEN un incidente tiene calle, colonia o alcaldía THEN el asistente SHALL mostrar la ubicación como `calle, Col. colonia, alcaldía`, omitiendo las partes vacías.
2. WHEN un incidente no tiene calle, colonia ni alcaldía THEN el asistente SHALL mostrar "Ubicación no especificada".
3. El asistente SHALL NOT mostrar los textos `None`, `null`, `nan` ni `?` como parte de una ubicación.
4. WHEN un incidente tiene coordenadas confirmadas pero no tiene calle THEN el asistente SHALL mostrar las coordenadas con 4 decimales.
5. WHEN el asistente muestra un tipo de incidente THEN SHALL usar una etiqueta legible (por ejemplo "Drenaje obstruido") en lugar del identificador interno (`drenaje_obstruido`).

### Requisito 4 — Etiquetado correcto de los datos

**Historia de usuario:** Como usuario, quiero que la interfaz diga qué datos estoy viendo, para no confundir datos reales con datos de demostración.

#### Criterios de aceptación

1. WHEN la base contiene reportes con `origen = 'real'` THEN el sistema SHALL NOT mostrar el aviso "datos ficticios / DATOS DEMO" como mensaje general.
2. WHEN la base contiene reportes reales THEN el sistema SHALL indicar que son datos históricos oficiales (Locatel 0311 2023, C5 2022-2024) y que no representan el estado actual.
3. WHEN la base solo contiene reportes demo THEN el sistema SHALL mostrar el aviso de datos ficticios.
4. El aviso SHALL obtenerse de `GET /api/resumen`, no estar fijo en el HTML.

### Requisito 5 — Calidad de la base de datos

**Historia de usuario:** Como analista, quiero un catálogo de fuentes sin duplicados y que se conserve toda la información de ubicación disponible.

#### Criterios de aceptación

1. La tabla `fuentes` SHALL tener un único registro por fuente; los registros de marcador de posición sin conteo (`FUENTE-001` y `FUENTE-003`, duplicados de Locatel y C5) SHALL eliminarse o fusionarse.
2. WHEN el CSV de C5 o Locatel contiene un campo de dirección o colonia THEN el importador SHALL guardarlo en `calle` o `colonia`.
3. WHEN se agrupan reportes en un incidente THEN el incidente SHALL heredar la primera calle y colonia no vacías de sus reportes.
4. Los cambios de esquema o limpieza SHALL hacerse con un script que primero respalde `urbia.db`.

### Requisito 6 — No inventar datos (se mantiene)

1. El asistente SHALL NOT generar direcciones, colonias ni cifras que no existan en la base.
2. Cada respuesta SHALL seguir incluyendo fuente, confianza, fecha de corte y advertencia (RF-07.3 del spec principal).
