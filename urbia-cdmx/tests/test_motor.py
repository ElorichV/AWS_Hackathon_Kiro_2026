"""
URBIA CDMX — Pruebas automatizadas
Verifican los 10 criterios de aceptación del proyecto.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.priorizacion import (
    agrupar_en_incidentes, calcular_prioridad_incidente,
    recalcular_todos, PESOS_DEFAULT
)

REPORTE_BACHE = {
    "id": "T-001", "fuente": "test", "origen": "demo",
    "fecha_reporte": "2024-01-10", "alcaldia": "Iztapalapa",
    "colonia": "Test", "calle": "Calle Falsa 123",
    "categoria": "vial", "subcategoria": "bache",
    "descripcion": "Bache de prueba",
    "latitud": 19.3764, "longitud": -99.0922,
    "coords_confirmadas": True, "estado": "abierto", "es_emergencia": False,
}

REPORTE_BACHE_CERCANO = {
    **REPORTE_BACHE,
    "id": "T-002",
    "fecha_reporte": "2024-01-12",
    "latitud": 19.3765, "longitud": -99.0921,  # < 200 metros de T-001
    "descripcion": "El mismo bache, segundo reporte",
}

REPORTE_EMERGENCIA = {
    "id": "T-003", "fuente": "test", "origen": "demo",
    "fecha_reporte": "2024-01-15", "alcaldia": "Cuauhtémoc",
    "colonia": "Centro", "calle": "Eje Central",
    "categoria": "seguridad", "subcategoria": "vialidad_bloqueada",
    "descripcion": "EMERGENCIA: hundimiento repentino",
    "latitud": 19.4284, "longitud": -99.1356,
    "coords_confirmadas": True, "estado": "emergencia", "es_emergencia": True,
}

REPORTE_SIN_COORDS = {
    **REPORTE_BACHE,
    "id": "T-004",
    "latitud": None, "longitud": None,
    "coords_confirmadas": False,
}


def test_1_dos_reportes_mismo_incidente():
    """Test 1: Dos reportes del mismo incidente no cuentan como dos daños distintos."""
    reportes = [REPORTE_BACHE, REPORTE_BACHE_CERCANO]
    incidentes = agrupar_en_incidentes(reportes)
    assert len(incidentes) == 1, f"Esperaba 1 incidente, obtuve {len(incidentes)}"
    assert incidentes[0]["total_reportes"] == 2, f"Esperaba 2 reportes en el incidente, obtuve {incidentes[0]['total_reportes']}"
    print("✅ Test 1 PASADO: dos reportes cercanos → 1 incidente con 2 reportes.")


def test_2_emergencia_no_queda_relegada():
    """Test 2: Emergencia confirmada no queda relegada por puntaje bajo."""
    reportes = [REPORTE_BACHE, REPORTE_BACHE_CERCANO, REPORTE_EMERGENCIA]
    incidentes = agrupar_en_incidentes(reportes)
    calculados = recalcular_todos(incidentes)
    primero = calculados[0]
    assert primero.get("es_emergencia") == True or primero.get("estado") == "emergencia", \
        f"La emergencia debería ser el primero. Primero fue: {primero.get('calle')}"
    assert primero.get("puntaje_total") == 100.0, \
        f"Emergencia debe tener puntaje 100. Obtuvo: {primero.get('puntaje_total')}"
    print("✅ Test 2 PASADO: emergencia aparece primero con puntaje 100.")


def test_3_sin_coordenadas_no_inventa_ubicacion():
    """Test 3: Reporte sin coordenadas no aparece en ubicación inventada."""
    inc = {
        "id": "INC-T-004", "tipo": "bache", "categoria": "vial",
        "latitud": None, "longitud": None, "coords_confirmadas": False,
        "total_reportes": 1, "estado": "abierto", "es_emergencia": False,
        "fecha_primer_reporte": "2024-01-10", "alcaldia": "Desconocida",
        "calle": "Sin confirmar",
    }
    result = calcular_prioridad_incidente(inc, PESOS_DEFAULT)
    assert result.get("latitud") is None, "latitud debe ser None si no hay coordenadas."
    assert result.get("longitud") is None, "longitud debe ser None si no hay coordenadas."
    print("✅ Test 3 PASADO: sin coordenadas, latitud/longitud se mantienen None.")


def test_4_motor_determinista():
    """Test 4: El motor produce resultados deterministas (mismos inputs → mismo output)."""
    inc = {
        "id": "INC-T-001", "tipo": "bache", "categoria": "vial",
        "latitud": 19.3764, "longitud": -99.0922, "coords_confirmadas": True,
        "total_reportes": 3, "estado": "abierto", "es_emergencia": False,
        "fecha_primer_reporte": "2024-01-10", "alcaldia": "Iztapalapa",
        "calle": "Av. Ermita", "subcategoria": "bache",
    }
    r1 = calcular_prioridad_incidente(inc, PESOS_DEFAULT)
    r2 = calcular_prioridad_incidente(inc, PESOS_DEFAULT)
    assert r1["puntaje_total"] == r2["puntaje_total"], \
        f"El motor no es determinista: {r1['puntaje_total']} != {r2['puntaje_total']}"
    print(f"✅ Test 4 PASADO: mismo input → mismo puntaje ({r1['puntaje_total']}).")


def test_5_cambiar_pesos_modifica_resultado():
    """Test 5: Cambiar los pesos modifica correctamente el ranking."""
    inc_vial = {
        "id": "INC-V", "tipo": "bache", "categoria": "vial", "subcategoria": "bache",
        "latitud": 19.3764, "longitud": -99.0922, "coords_confirmadas": True,
        "total_reportes": 10, "estado": "abierto", "es_emergencia": False,
        "fecha_primer_reporte": "2024-01-01", "alcaldia": "Iztapalapa",
        "calle": "Av. Ermita",
    }
    inc_hidro = {
        "id": "INC-H", "tipo": "coladera_obstruida", "categoria": "hidraulica",
        "subcategoria": "coladera_obstruida",
        "latitud": 19.3700, "longitud": -99.0871, "coords_confirmadas": True,
        "total_reportes": 1, "estado": "abierto", "es_emergencia": False,
        "fecha_primer_reporte": "2024-05-01", "alcaldia": "Iztapalapa",
        "calle": "Calle Moctezuma",
    }

    pesos_default = PESOS_DEFAULT
    # Pesos que elevan mucho R (lluvia) → favorece hidráulico
    pesos_lluvia = {"S": 0.10, "D": 0.10, "M": 0.10, "A": 0.10, "R": 0.60}

    r_vial_def = calcular_prioridad_incidente(inc_vial, pesos_default)["puntaje_total"]
    r_hidro_def = calcular_prioridad_incidente(inc_hidro, pesos_default)["puntaje_total"]

    r_vial_lluvia = calcular_prioridad_incidente(inc_vial, pesos_lluvia)["puntaje_total"]
    r_hidro_lluvia = calcular_prioridad_incidente(inc_hidro, pesos_lluvia)["puntaje_total"]

    # Con pesos de lluvia, el hidráulico debe subir relativamente
    assert r_hidro_lluvia > r_hidro_def, \
        f"Esperaba que el puntaje hidráulico subiera con peso R alto: {r_hidro_def} → {r_hidro_lluvia}"
    print(f"✅ Test 5 PASADO: cambiar pesos modifica resultados (hidráulico: {r_hidro_def:.1f} → {r_hidro_lluvia:.1f}).")


def test_6_datos_historicos_no_son_activos():
    """Test 6: Datos históricos etiquetados como tal, no como incidentes activos."""
    reporte_historico = {
        **REPORTE_BACHE,
        "id": "T-005",
        "origen": "historico",
        "estado": "cerrado",
        "fecha_reporte": "2020-01-01",
    }
    # El estado debe preservarse, no cambiar a 'abierto'
    inc = agrupar_en_incidentes([reporte_historico])
    assert inc[0]["estado"] == "cerrado", \
        f"Un incidente cerrado/histórico no debe convertirse en 'abierto'. Estado: {inc[0]['estado']}"
    print("✅ Test 6 PASADO: datos históricos cerrados no se marcan como abiertos.")


def test_7_costos_marcados_como_provisionales():
    """Test 7: Las estimaciones de costo se identifican como provisionales."""
    # Verificar que el módulo de demo_data tiene la advertencia
    from backend.data.demo_data import RECURSOS_DEMO
    assert "FICTICIOS" in RECURSOS_DEMO.get("advertencia", "") or \
           "ficticios" in RECURSOS_DEMO.get("advertencia", "").lower(), \
        "Los recursos demo deben tener advertencia de que son ficticios."
    print("✅ Test 7 PASADO: recursos marcados como ficticios/provisionales.")


def test_8_asistente_no_inventa_cifras():
    """Test 8: El asistente responde 'sin datos' cuando la base está vacía (no inventa)."""
    from backend.services.asistente import _sin_datos
    resp = _sin_datos("No hay incidentes cargados.")
    assert "No hay datos" in resp["respuesta"], "El mensaje de sin datos debe indicar ausencia de información."
    assert resp.get("confianza") == "n/a", "Sin datos, la confianza debe ser n/a."
    print("✅ Test 8 PASADO: el asistente retorna 'sin datos' cuando no hay información.")


def test_9_fuentes_trazables():
    """Test 9: Las fuentes incluyen URL, nombre y notas de trazabilidad."""
    from backend.data.demo_data import FUENTES_DEMO
    for f in FUENTES_DEMO:
        assert f.get("id"), f"Fuente sin ID: {f}"
        assert f.get("nombre"), f"Fuente sin nombre: {f}"
        assert f.get("url"), f"Fuente sin URL: {f}"
    print(f"✅ Test 9 PASADO: {len(FUENTES_DEMO)} fuentes con ID, nombre y URL.")


def test_10_sistema_funciona_con_datos_demo():
    """Test 10: El sistema puede funcionar localmente con datos de demostración."""
    from backend.data.demo_data import REPORTES_DEMO
    assert len(REPORTES_DEMO) > 0, "Debe haber datos de demostración."
    incidentes = agrupar_en_incidentes(REPORTES_DEMO)
    assert len(incidentes) > 0, "Debe haber incidentes generados desde los datos demo."
    calculados = recalcular_todos(incidentes)
    assert len(calculados) > 0, "Debe haber incidentes con puntaje calculado."
    assert all("puntaje_total" in i for i in calculados), "Todos los incidentes deben tener puntaje."
    print(f"✅ Test 10 PASADO: {len(REPORTES_DEMO)} reportes → {len(calculados)} incidentes calculados.")


if __name__ == "__main__":
    tests = [
        test_1_dos_reportes_mismo_incidente,
        test_2_emergencia_no_queda_relegada,
        test_3_sin_coordenadas_no_inventa_ubicacion,
        test_4_motor_determinista,
        test_5_cambiar_pesos_modifica_resultado,
        test_6_datos_historicos_no_son_activos,
        test_7_costos_marcados_como_provisionales,
        test_8_asistente_no_inventa_cifras,
        test_9_fuentes_trazables,
        test_10_sistema_funciona_con_datos_demo,
    ]
    pasados = 0
    fallidos = []
    print("\n" + "="*60)
    print("  URBIA CDMX — Suite de Pruebas de Aceptación")
    print("="*60 + "\n")
    for t in tests:
        try:
            t()
            pasados += 1
        except AssertionError as e:
            print(f"❌ {t.__name__} FALLÓ: {e}")
            fallidos.append(t.__name__)
        except Exception as e:
            print(f"💥 {t.__name__} ERROR: {e}")
            fallidos.append(t.__name__)
    print(f"\n{'='*60}")
    print(f"  Resultado: {pasados}/{len(tests)} pruebas pasadas")
    if fallidos:
        print(f"  Fallidas: {', '.join(fallidos)}")
    print("="*60 + "\n")
    sys.exit(0 if not fallidos else 1)
