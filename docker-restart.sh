#!/bin/bash

echo "🔄 Reiniciando Musicalo..."

# Reiniciar el servicio
docker-compose restart musicalo

echo "✅ Bot reiniciado correctamente!"
echo ""
echo "📋 Para ver los logs: ./docker-logs.sh"
