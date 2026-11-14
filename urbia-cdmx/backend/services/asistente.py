"""
URBIA CDMX — Asistente conversacional URBIA AI
Clasificador determinista (no requiere Bedrock ni LLM externo).
Responde SOLO con datos presentes en la base de datos.
"""
from typing import Dict, List, Optional
from .database import get_incidentes, get_reportes, get_resumen, get_fuentes
from .priorizacion import PESOS_DEFAULT, recalcular_todos


def _numero_a_texto(n: int) -> str:
    if n == 0:
        return "ninguno"
    return str(n)


def responder(pregunta: str) -> Dict:
    """
    Genera una respuesta basada en datos reales de la base de datos.
    Nunca inventa cifras. Si no hay datos disponibles, lo indica explícitamente.
    """
    p = pregunta.lower().strip()
    respuesta = None
    fuente = "Base de datos URBIA CDMX"
    confianza = "alta"
    fecha_corte = "datos cargados en esta sesión"

    # ── Pregunta 1: vialidades / incidentes más urgentes ────────────────────
    if any(kw in p for kw in ["urgent", "prioritar", "top", "más graves", "peores", "críticos", "10 vialidades"]):
        incidentes = get_incidentes()
        if not incidentes:
            return _sin_datos("No hay incidentes registrados en la base de datos.")
        # Emergencias primero, luego por puntaje
        incidentes.sort(key=lambda x: (
            0 if x.get("es_emergencia") else 1,
            -x.get("puntaje_total", 0)
        ))
        top = incidentes[:10]
        lineas = []
        for i, inc in enumerate(top, 1):
            # Construir ubicación más completa
            ubicacion_partes = []
            if inc.get('calle'):
                ubicacion_partes.append(inc.get('calle'))
            if inc.get('colonia'):
                ubicacion_partes.append(f"Col. {inc.get('colonia')}")
            if inc.get('alcaldia'):
                ubicacion_partes.append(inc.get('alcaldia'))
            
            ubicacion = ", ".join(ubicacion_partes) if ubicacion_partes else "Ubicación sin dirección específica"
            
            emergencia = " ⚠️ EMERGENCIA" if inc.get("es_emergencia") else ""
            lineas.append(
                f"{i}. {ubicacion} "
                f"| Tipo: {inc.get('tipo', '?')} | Puntaje: {inc.get('puntaje_total', 0):.1f}/100 "
                f"| Nivel: {inc.get('nivel_prioridad', '?').upper()}{emergencia}"
            )
        respuesta = (
            f"Las {len(top)} ubicaciones con mayor prioridad en la base de datos son:\n\n"
            + "\n".join(lineas)
            + f"\n\nTotal de incidentes en base de datos: {len(incidentes)}."
            + "\n\n💡 Tip: Para ver estas ubicaciones en el mapa con más detalles, ve a la sección '🗺️ Mapa de Riesgo' en el menú."
        )

    # ── Pregunta 2: por qué tiene prioridad alta ─────────────────────────────
    elif any(kw in p for kw in ["por qué", "porque", "justificacion", "justificación", "explica", "razón"]):
        # Buscar nombre de calle o alcaldía en la pregunta
        incidentes = get_incidentes()
        encontrado = None
        for inc in incidentes:
            calle = (inc.get("calle") or "").lower()
            alcaldia = (inc.get("alcaldia") or "").lower()
            if calle in p or alcaldia in p:
                encontrado = inc
                break
        if encontrado and encontrado.get("justificacion"):
            respuesta = (
                f"Justificación para **{encontrado.get('calle')}** ({encontrado.get('alcaldia')}):\n\n"
                f"{encontrado.get('justificacion')}"
            )
        elif encontrado:
            respuesta = f"Se encontró el incidente pero no tiene justificación calculada. Intenta recalcular prioridades."
        else:
            # Mostrar el de mayor prioridad como ejemplo
            if incidentes:
                top = incidentes[0]
                respuesta = (
                    f"No encontré la ubicación exacta en tu pregunta. "
                    f"El incidente de mayor prioridad actualmente es:\n\n"
                    f"**{top.get('calle')}** ({top.get('alcaldia')})\n"
                    f"{top.get('justificacion', 'Sin justificación disponible.')}"
                )
                confianza = "media"
            else:
                return _sin_datos("No hay incidentes registrados.")

    # ── Pregunta 3: coladeras / drenaje / lluvia ──────────────────────────────
    elif any(kw in p for kw in ["coladera", "drenaje", "lluvia", "inundaci", "hidráulic", "hidraulic"]):
        incidentes = get_incidentes({"categoria": "hidraulica"})
        if not incidentes:
            return _sin_datos("No hay incidentes hidráulicos registrados.")
        incidentes.sort(key=lambda x: -x.get("puntaje_total", 0))
        lineas = []
        for inc in incidentes[:8]:
            # Construir ubicación más completa
            ubicacion_partes = []
            if inc.get('calle'):
                ubicacion_partes.append(inc.get('calle'))
            if inc.get('colonia'):
                ubicacion_partes.append(f"Col. {inc.get('colonia')}")
            if inc.get('alcaldia'):
                ubicacion_partes.append(inc.get('alcaldia'))
            
            ubicacion = ", ".join(ubicacion_partes) if ubicacion_partes else "Ubicación no especificada"
            
            lineas.append(
                f"• {ubicacion} "
                f"— {inc.get('tipo', '?')} | Puntaje: {inc.get('puntaje_total', 0):.1f}/100 "
                f"| Reportes: {inc.get('total_reportes', 1)}"
            )
        respuesta = (
            f"Incidentes hidráulicos registrados (ordenados por prioridad):\n\n"
            + "\n".join(lineas)
            + "\n\n⚠️ La relación coladera obstruida → encharcamiento es un riesgo potencial, "
            "no se afirma causalidad sin inspección técnica."
        )

    # ── Pregunta 4: presupuesto ───────────────────────────────────────────────
    elif any(kw in p for kw in ["presupuesto", "pesos", "costo", "recursos", "cuánto"]):
        # Extraer número del texto si hay
        import re
        numeros = re.findall(r'[\d,]+', p)
        presupuesto = None
        for n in numeros:
            try:
                presupuesto = int(n.replace(",", ""))
                break
            except Exception:
                pass

        incidentes = get_incidentes()
        if not incidentes:
            return _sin_datos("No hay incidentes en la base de datos.")

        # Costos unitarios estimados (ficticios, marcados)
        costos_ref = {
            "bache": 15000, "bacheo": 15000, "grieta": 8000,
            "pavimento_deteriorado": 25000, "hundimiento": 40000,
            "coladera_obstruida": 5000, "drenaje_obstruido": 18000,
            "inundacion_vialidad": 35000, "encharcamiento": 8000,
            "vialidad_bloqueada": 20000,
        }

        lineas = ["⚠️ COSTOS FICTICIOS — Solo para demostración del MVP.\n"]
        total_estimado = 0
        seleccionados = []

        for inc in sorted(incidentes, key=lambda x: -x.get("puntaje_total", 0)):
            tipo = (inc.get("tipo") or "").lower()
            costo = costos_ref.get(tipo, 20000)
            if presupuesto and total_estimado + costo > presupuesto:
                continue
            total_estimado += costo
            seleccionados.append(inc)
            
            # Construir ubicación
            ubicacion_partes = []
            if inc.get('calle'):
                ubicacion_partes.append(inc.get('calle'))
            if inc.get('colonia'):
                ubicacion_partes.append(f"Col. {inc.get('colonia')}")
            if inc.get('alcaldia'):
                ubicacion_partes.append(inc.get('alcaldia'))
            ubicacion = ", ".join(ubicacion_partes) if ubicacion_partes else "Ubicación no especificada"
            
            lineas.append(
                f"• {ubicacion} "
                f"— {tipo} | Costo est.: ${costo:,} MXN"
            )

        if presupuesto:
            lineas.append(f"\nPresupuesto disponible: ${presupuesto:,} MXN")
        lineas.append(f"Total estimado de intervenciones seleccionadas: ${total_estimado:,} MXN")
        lineas.append(f"Intervenciones posibles: {len(seleccionados)}")
        respuesta = "\n".join(lineas)
        confianza = "baja — costos son referenciales sin levantamiento técnico"

    # ── Pregunta 5: autoridad responsable ────────────────────────────────────
    elif any(kw in p for kw in ["autoridad", "responsable", "dependencia", "alcaldía", "quién atiende"]):
        respuesta = (
            "La competencia institucional depende del tipo de infraestructura y la clasificación de la vialidad.\n\n"
            "Criterios generales (referencial, no reemplaza evaluación jurídica):\n"
            "• **Baches en vías locales** → Alcaldía correspondiente\n"
            "• **Baches en vías primarias o ejes viales** → SEMOVI / Secretaría de Obras CDMX\n"
            "• **Red de drenaje y alcantarillado** → SACMEX (Sistema de Aguas de la Ciudad de México)\n"
            "• **Emergencias viales** → SSC (Secretaría de Seguridad Ciudadana) + SEMOVI\n"
            "• **Riesgo de inundación** → SGIRPC (Gestión Integral de Riesgos y Protección Civil)\n\n"
            "Para cada incidente específico, URBIA muestra la dependencia sugerida en el ranking. "
            "Estado 'competencia por determinar' cuando no hay información suficiente.\n\n"
            "⚠️ Esta información es referencial. La asignación oficial requiere evaluación institucional."
        )
        confianza = "media — referencial, no es dictamen legal"

    # ── Pregunta 6: resumen general ──────────────────────────────────────────
    elif any(kw in p for kw in ["resumen", "total", "cuántos reportes", "estadísticas", "general"]):
        resumen = get_resumen()
        respuesta = (
            f"Resumen general de URBIA CDMX:\n\n"
            f"• Reportes registrados: {resumen['total_reportes']}\n"
            f"• Incidentes únicos estimados: {resumen['incidentes_unicos']}\n"
            f"• Casos abiertos: {resumen['casos_abiertos']}\n"
            f"• Casos críticos/altos: {resumen['casos_criticos']}\n"
            f"• Emergencias activas: {resumen['casos_emergencia']}\n"
            f"• Alcaldías analizadas: {resumen['alcaldias_analizadas']}\n\n"
            f"⚠️ {resumen['advertencia_datos']}"
        )

    # ── Pregunta 7: emergencias ───────────────────────────────────────────────
    elif any(kw in p for kw in ["emergencia", "crítico", "peligro inmediato"]):
        incidentes = get_incidentes({"estado": "emergencia"})
        emergencias = [i for i in incidentes if i.get("es_emergencia")]
        if not emergencias:
            respuesta = "No hay emergencias activas registradas en la base de datos en este momento."
        else:
            lineas = [f"⚠️ HAY {len(emergencias)} EMERGENCIA(S) ACTIVA(S):\n"]
            for em in emergencias:
                lineas.append(
                    f"• {em.get('calle', '?')} ({em.get('alcaldia', '?')}) "
                    f"— {em.get('tipo', '?')} | {em.get('descripcion', '')[:80]}..."
                )
            lineas.append("\nEstas emergencias requieren validación humana inmediata.")
            respuesta = "\n".join(lineas)

    # ── Fallback ──────────────────────────────────────────────────────────────
    else:
        resumen = get_resumen()
        respuesta = (
            f"Hola, soy URBIA AI. Puedo responder preguntas sobre los datos cargados en el sistema.\n\n"
            f"Actualmente tengo {resumen['total_reportes']} reportes y {resumen['incidentes_unicos']} incidentes únicos.\n\n"
            f"Puedes preguntarme:\n"
            f"• ¿Cuáles son las 10 vialidades más urgentes?\n"
            f"• ¿Por qué [calle] tiene prioridad alta?\n"
            f"• ¿Qué coladeras deben inspeccionarse antes de las lluvias?\n"
            f"• ¿Qué intervenciones se pueden hacer con $100,000 pesos?\n"
            f"• ¿Qué autoridad es responsable de esta ubicación?\n"
            f"• ¿Hay emergencias activas?"
        )
        confianza = "n/a"

    return {
        "respuesta": respuesta,
        "fuente": fuente,
        "confianza": confianza,
        "fecha_corte": fecha_corte,
        "advertencia": "Las respuestas se basan únicamente en los datos cargados en URBIA CDMX. No sustituyen evaluación técnica ni decisión institucional.",
    }


def _sin_datos(mensaje: str) -> Dict:
    return {
        "respuesta": f"No hay datos suficientes para responder: {mensaje}",
        "fuente": "Base de datos URBIA CDMX",
        "confianza": "n/a",
        "fecha_corte": "datos cargados en esta sesión",
        "advertencia": "Carga datos reales o de demostración para obtener respuestas.",
    }
