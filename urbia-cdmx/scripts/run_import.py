#!/usr/bin/env python3
"""
Arranca servidor y ejecuta importación de datos reales.
Uso: /usr/bin/python3 scripts/run_import.py
"""
import sys, os, time, subprocess, urllib.request, json

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

DB = os.path.join(PROJECT, "backend", "data", "urbia.db")
if os.path.exists(DB):
    os.remove(DB)
    print("✅ DB limpia")

os.system("pkill -f 'uvicorn backend.main' 2>/dev/null")
time.sleep(2)

LOG = open("/tmp/urbia_final.log", "w")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app",
     "--host", "0.0.0.0", "--port", "8000"],
    cwd=PROJECT, stdout=LOG, stderr=subprocess.STDOUT
)
print(f"✅ Servidor PID {proc.pid} — esperando 7s...")
time.sleep(7)

# Verificar
try:
    d = json.loads(urllib.request.urlopen("http://localhost:8000/api/resumen", timeout=10).read())
    print(f"✅ Online — {d['total_reportes']} reportes demo")
except Exception as e:
    print(f"❌ No responde: {e}")
    print(open("/tmp/urbia_final.log").read()[-800:])
    sys.exit(1)

# Importar datos reales
print("\n📥 Importando datos reales CDMX (Locatel + C5)...")
try:
    req = urllib.request.Request(
        "http://localhost:8000/api/importar-real",
        data=b"{}", headers={"Content-Type": "application/json"}, method="POST"
    )
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    print(f"✅ {r['mensaje']}")
    for x in r.get("resultados", []):
        icon = "✅" if x["estado"] == "ok" else "❌"
        print(f"   {icon} {x['fuente']}: {x.get('importados',0)} registros")
        if x.get("error"):
            print(f"      Error: {x['error']}")
except Exception as e:
    print(f"❌ Importación falló: {e}")

# Resumen final
d = json.loads(urllib.request.urlopen("http://localhost:8000/api/resumen", timeout=10).read())
print(f"""
{'='*50}
  URBIA CDMX — DATOS CARGADOS
{'='*50}
  Reportes totales:      {d['total_reportes']}
  Incidentes únicos:     {d['incidentes_unicos']}
  Casos abiertos:        {d['casos_abiertos']}
  Críticos/Altos:        {d['casos_criticos']}
  Emergencias activas:   {d['casos_emergencia']}
  Alcaldías analizadas:  {d['alcaldias_analizadas']}
{'='*50}
  🌐 http://localhost:8000
  📖 http://localhost:8000/docs
{'='*50}
""")

print("Servidor corriendo. Ctrl+C para detener.")
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    print("Servidor detenido.")
