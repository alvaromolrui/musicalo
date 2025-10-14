#!/bin/bash

echo "🛑 Deteniendo Music Agent Bot..."

# Verificar si el contenedor está corriendo
if docker-compose ps | grep -q "music-agent-bot.*Up"; then
    echo "🔄 Deteniendo servicios..."
    docker-compose down
    echo "✅ Bot detenido correctamente"
else
    echo "ℹ️  El bot no está corriendo"
fi
