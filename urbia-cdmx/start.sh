#!/bin/bash
# URBIA CDMX — Script de inicio
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         URBIA CDMX — MVP v0.1                   ║"
echo "║  Plataforma de Infraestructura Urbana CDMX       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 no encontrado. Instálalo en https://python.org"
  exit 1
fi

echo "✅ Python: $(python3 --version)"

# Verificar dependencias
echo "📦 Verificando dependencias..."
python3 -m pip install --user fastapi uvicorn pydantic requests python-multipart 2>/dev/null | grep -E "Successfully|already" | head -5

# Limpiar base de datos anterior (opcional, para demo limpia)
if [ -f "backend/data/urbia.db" ]; then
  echo "🗃️  Base de datos existente encontrada."
else
  echo "🆕 Se creará base de datos nueva con datos de demostración."
fi

echo ""
echo "🚀 Iniciando servidor URBIA CDMX..."
echo "   URL: http://localhost:8000"
echo "   API: http://localhost:8000/docs"
echo ""
echo "   Presiona Ctrl+C para detener."
echo ""

python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
