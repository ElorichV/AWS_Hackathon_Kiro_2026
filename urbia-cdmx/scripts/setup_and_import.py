#!/usr/bin/env python3
"""
URBIA CDMX — Script de configuración e importación de datos reales.
Ejecutar con: python3 scripts/setup_and_import.py
"""
import sys
import os
import signal
import subprocess
import time
import urllib.request
import json

# Asegurar que el path del proyecto esté disponible
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

def log(msg):
    print(f"  {msg}", flush=True)

def paso(titulo):
    print(f"\n{'='*55}")
    print(f"  {titulo}")
    print(f"{'='*55}")

# ── PASO 1: Limpiar DB y reiniciar ───────────────────────────────────────────
paso("PASO 1: Preparar entorno")

db_path = os.path.join(PROJECT_DIR, "backend", "data", "urbia.db")
if os.path.exists(db_path):
    os.remove(db_path)
    log(f"✅ Base de datos anterior eliminada")
else:
    log(f"ℹ️  No había base de datos previa")

# Matar cualquier uvicorn corriendo
os.system("pkill -f 'uvicorn backend.main' 2>/dev/null")
time.sleep(1)
log("✅ Procesos anteriores terminados")

# ── PASO 2: Iniciar servidor ──────────────────────────────────────────────────
paso("PASO 2: Iniciar servidor URBIA")

log_file = "/tmp/urbia_setup.log"
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app",
     "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
    cwd=PROJECT_DIR,
    stdout=open(log_file, "w"),
    stderr=subprocess.STDOUT,
)
log(f"✅ Servidor iniciado (PID {proc.pid})")
log("   Esperando que levante...")
time.sleep(5)

# Verificar que responde
try:
    resp = urllib.request.urlopen("http://localhost:8000/api/resumen", timeout=10)
    data = json.loads(resp.read())
    log(f"✅ Servidor respondiendo — {data['total_reportes']} reportes demo cargados")
except Exception as e:
    log(f"❌ Servidor no responde: {e}")
    log("   Revisa el log en: " + log_file)
    sys.exit(1)

# ── PASO 3: Importar datos reales ─────────────────────────────────────────────
paso("PASO 3: Importar datos reales de la CDMX")
log("   Descargando 0311 Locatel 2022 y C5 Incidentes Viales...")
log("   (esto puede tomar 30-60 segundos según tu conexión)")

try:
    req = urllib.request.Request(
        "http://localhost:8000/api/importar-real",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=120)
    resultado = json.loads(resp.read())

    log(f"✅ {resultado['mensaje']}")
    for r in resultado.get("resultados", []):
        estado = "✅" if r["estado"] == "ok" else "❌"
        log(f"   {estado} {r['fuente']}: {r.get('importados', 0)} registros — {r.get('advertencia', r.get('error',''))}")
    log(f"\n   ⚠️  {resultado['advertencia_general']}")
except Exception as e:
    log(f"❌ Error en importación: {e}")
    log("   El sistema seguirá funcionando con datos DEMO")

# ── PASO 4: Resumen final ─────────────────────────────────────────────────────
paso("PASO 4: Estado final")

try:
    resp = urllib.request.urlopen("http://localhost:8000/api/resumen", timeout=10)
    data = json.loads(resp.read())
    log(f"📊 Reportes totales:       {data['total_reportes']}")
    log(f"📍 Incidentes únicos:      {data['incidentes_unicos']}")
    log(f"🔴 Casos abiertos:         {data['casos_abiertos']}")
    log(f"⚠️  Críticos/Altos:         {data['casos_criticos']}")
    log(f"🚨 Emergencias activas:    {data['casos_emergencia']}")
    log(f"🏙️  Alcaldías analizadas:   {data['alcaldias_analizadas']}")
except Exception as e:
    log(f"Error obteniendo resumen: {e}")

print(f"\n{'='*55}")
print(f"  ✅ URBIA CDMX listo")
print(f"  🌐 Dashboard:  http://localhost:8000")
print(f"  📖 API Docs:   http://localhost:8000/docs")
print(f"  🔑 PID servidor: {proc.pid}")
print(f"  (Ctrl+C para detener el servidor)")
print(f"{'='*55}\n")

# Mantener vivo
try:
    proc.wait()
except KeyboardInterrupt:
    log("Deteniendo servidor...")
    proc.terminate()
    proc.wait()
    log("Servidor detenido.")
