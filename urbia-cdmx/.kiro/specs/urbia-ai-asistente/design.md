# URBIA AI — Asistente como pantalla principal — Diseño

## Resumen

Cambios en tres capas: frontend (orden del menú, sección inicial, aviso dinámico, enlace al mapa), asistente (`backend/services/asistente.py`: formato de ubicación y tipo) y datos (importadores, agrupación y limpieza de `fuentes`).

## Frontend

### Archivos
- `frontend/index.html`
- `frontend/static/js/app.js`

### Navegación inicial
- `nav` en `index.html`: el enlace `data-section="chat"` es el primero y tiene `class="active"`.
- `#sec-chat` tiene `class="section active"`; `#sec-resumen` ya no.
- `#page-title` arranca con "URBIA AI — Asistente".
- El bloque de inicio de `app.js` ya llama `cargarSugerencias()`; se mantiene. `cargarResumen()` también se mantiene porque llena `#last-update` y la caché.

### Enlace al mapa desde el chat
El backend devuelve texto plano. Para que la sugerencia sea clicable sin interpretar HTML del servidor:
- La respuesta de `/api/chat` agrega el campo `"accion_sugerida": "mapa"` cuando la respuesta lista incidentes.
- `enviarMensaje()` en `app.js`, al recibir `accion_sugerida === "mapa"`, agrega un botón "🗺️ Ver en el mapa" debajo del mensaje.
- El botón llama a una función `irASeccion('mapa')`, que reutiliza la misma lógica de los enlaces del menú (extraer el handler actual a esa función).

### Aviso de datos dinámico
- `GET /api/resumen` agrega `tiene_datos_reales: bool` y `advertencia_datos` con texto según el caso.
- `cargarResumen()` reemplaza el contenido de `.demo-badge` (barra lateral) y de `.alert-warn` en `#sec-resumen` con ese texto.

| Caso | Texto |
|------|-------|
| Hay `origen='real'` | "Datos históricos oficiales: Locatel 0311 (2023) y C5 (2022-2024). No representan el estado actual." |
| Solo demo | "Datos ficticios para demostración. No representan incidentes reales." |

## Asistente (`backend/services/asistente.py`)

### Funciones nuevas
```python
TIPOS_LEGIBLES = {
    "drenaje_obstruido": "Drenaje obstruido",
    "coladera_obstruida": "Coladera obstruida",
    "inundacion_vialidad": "Inundación en vialidad",
    "encharcamiento": "Encharcamiento",
    "bache": "Bache", "grieta": "Grieta", "hundimiento": "Hundimiento",
    "pavimento_deteriorado": "Pavimento deteriorado",
    "choque_vial": "Choque vial", "atropello": "Atropello", ...
}

def _limpio(v) -> str | None:
    # None, "", "none", "null", "nan", "na", "?" -> None
def _ubicacion(inc) -> str:
    # calle, Col. colonia, alcaldía; si no hay calle y hay coords: añade "(lat, lon)"
    # si nada: "Ubicación no especificada"
def _tipo(inc) -> str:
    # TIPOS_LEGIBLES o tipo.replace("_", " ").capitalize()
```
Todas las ramas que listan incidentes (urgentes, justificación, hidráulica, presupuesto, emergencias) usan `_ubicacion` y `_tipo`. Esto elimina el código repetido que se agregó en tres ramas.

### Respuesta
```json
{
  "respuesta": "...",
  "fuente": "...", "confianza": "...", "fecha_corte": "...", "advertencia": "...",
  "accion_sugerida": "mapa" | null
}
```

## Datos

### Importadores (`backend/services/importador.py`)
- C5: si el CSV trae una columna de dirección (verificar el encabezado real del archivo descargado antes de mapear), guardarla en `calle`. Si no existe, se deja `None`; no se inventa.
- Locatel: `colonia` ya se toma de `colonia_datos`; añadir respaldo con `0311_colonia_registro` cuando `colonia_datos` esté vacío.

### Agrupación (`backend/services/priorizacion.py`)
- Al crear el incidente, si el reporte semilla no tiene calle o colonia, tomar la primera no vacía de los reportes agrupados.

### Script de mantenimiento `scripts/limpiar_fuentes.py`
1. Copiar `backend/data/urbia.db` a `backend/data/urbia.backup-<fecha>.db`.
2. Borrar `FUENTE-001` y `FUENTE-003` (duplicados de las fuentes reales con conteo).
3. Conservar `FUENTE-002` (SACMEX) y `FUENTE-004` (Atlas) marcadas como `disponible = 0` con nota "pendiente de integrar".
4. Imprimir el estado antes y después.

## Pruebas (`tests/test_motor.py`)

| Prueba | Verifica |
|--------|----------|
| `test_11_ubicacion_sin_none` | `_ubicacion` nunca contiene "None"/"?" para incidentes con campos vacíos |
| `test_12_ubicacion_completa` | calle + colonia + alcaldía se unen en el orden correcto |
| `test_13_tipo_legible` | `drenaje_obstruido` → "Drenaje obstruido" |
| `test_14_accion_mapa` | respuesta de hidráulica trae `accion_sugerida == "mapa"` |
| `test_15_aviso_datos_reales` | con un reporte `origen='real'`, `get_resumen()["tiene_datos_reales"]` es True |

## Riesgos
- Coordenadas en texto pueden ser poco útiles para el usuario; por eso el botón al mapa es la vía principal de detalle.
- Si el CSV de C5 no trae dirección, el Requisito 5.2 no mejorará los datos existentes; el spec lo acepta.
