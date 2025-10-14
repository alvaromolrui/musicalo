#!/bin/bash

echo "🔄 Actualizando Music Agent Bot..."

# Parar el servicio
echo "🛑 Deteniendo bot..."
docker-compose down

# Construir nueva imagen
echo "🔨 Construyendo nueva imagen..."
docker-compose build --no-cache

# Eliminar imágenes antiguas
echo "🗑️  Limpiando imágenes antiguas..."
docker image prune -f

# Iniciar el servicio
echo "🚀 Iniciando bot actualizado..."
docker-compose up -d

echo "✅ Bot actualizado correctamente!"
echo ""
echo "📋 Para ver los logs: ./docker-logs.sh"
