# URBIA AI — Asistente como pantalla principal — Tareas

- [x] 1. Mostrar URBIA AI como pantalla inicial
  - [x] 1.1 Mover "URBIA AI" al primer lugar del menú en `frontend/index.html`
  - [x] 1.2 Marcar `#sec-chat` como sección activa y quitar `active` de `#sec-resumen`
  - [x] 1.3 Cambiar `#page-title` inicial a "URBIA AI — Asistente"
  - _Requisitos: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Sugerir el Mapa de Riesgo desde el chat
  - [x] 2.1 Mensaje de bienvenida que menciona el Mapa de Riesgo
  - [x] 2.2 Tip del mapa al final de la respuesta de "vialidades urgentes"
  - [ ] 2.3 Agregar `accion_sugerida: "mapa"` en las respuestas que listan incidentes (`asistente.py`)
  - [ ] 2.4 Extraer la navegación de `app.js` a `irASeccion(sec)` y usarla en el menú
  - [ ] 2.5 Mostrar botón "🗺️ Ver en el mapa" en `enviarMensaje()` cuando llegue `accion_sugerida`
  - _Requisitos: 2.1, 2.2, 2.3_

- [ ] 3. Ubicaciones y tipos legibles en el asistente
  - [x] 3.1 Unir calle, colonia y alcaldía en urgentes, hidráulica y presupuesto (código repetido)
  - [ ] 3.2 Crear `_limpio`, `_ubicacion`, `_tipo` y `TIPOS_LEGIBLES`; reemplazar el código repetido
  - [ ] 3.3 Aplicar `_ubicacion` también en las ramas de justificación y emergencias
  - [ ] 3.4 Mostrar coordenadas cuando no hay calle y sí hay coords confirmadas
  - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 4. Aviso de datos dinámico
  - [ ] 4.1 Agregar `tiene_datos_reales` y texto condicional a `get_resumen()` en `database.py`
  - [ ] 4.2 Llenar `.demo-badge` y la alerta del Resumen desde `cargarResumen()`
  - [ ] 4.3 Quitar el texto fijo "DATOS DEMO / ficticios" del HTML
  - _Requisitos: 4.1, 4.2, 4.3, 4.4_

- [ ] 5. Calidad de la base de datos
  - [ ] 5.1 Crear `scripts/limpiar_fuentes.py` con respaldo previo de `urbia.db`
  - [ ] 5.2 Ejecutarlo y verificar que `fuentes` queda sin duplicados de Locatel y C5
  - [ ] 5.3 Revisar encabezados reales del CSV de C5 y mapear dirección a `calle` si existe
  - [ ] 5.4 Respaldo de colonia con `0311_colonia_registro` en el importador de Locatel
  - [ ] 5.5 Heredar calle/colonia no vacías al agrupar incidentes en `priorizacion.py`
  - [ ] 5.6 Reimportar datos y comparar conteos de calle/colonia (antes: 13 / 2,220 de 6,577)
  - _Requisitos: 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Pruebas
  - [ ] 6.1 Agregar pruebas 11–15 de `design.md` a `tests/test_motor.py`
  - [ ] 6.2 Correr la suite completa (10 existentes + 5 nuevas)
  - _Requisitos: 3.x, 2.2, 4.1, 6.1_
