#!/bin/bash

echo "🔄 Reiniciando Music Agent Bot..."

# Reiniciar el servicio
docker-compose restart music-agent-bot

echo "✅ Bot reiniciado correctamente!"
echo ""
echo "📋 Para ver los logs: ./docker-logs.sh"
