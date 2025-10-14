#!/bin/bash

echo "📋 Mostrando logs de Music Agent Bot..."
echo "🛑 Presiona Ctrl+C para salir"
echo ""

# Mostrar logs en tiempo real
docker-compose logs -f music-agent-bot
