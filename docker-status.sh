#!/bin/bash

echo "📊 Estado de Musicalo:"
echo ""

# Mostrar estado de los servicios
docker-compose ps

echo ""
echo "🔍 Información detallada:"

# Verificar si el contenedor está corriendo
if docker-compose ps | grep -q "musicalo.*Up"; then
    echo "✅ Bot está corriendo"
    
    # Mostrar uso de recursos
    echo ""
    echo "💾 Uso de recursos:"
    docker stats musicalo --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    # Mostrar logs recientes
    echo ""
    echo "📋 Últimas 10 líneas de logs:"
    docker-compose logs --tail=10 musicalo
else
    echo "❌ Bot no está corriendo"
    echo ""
    echo "💡 Para iniciarlo: ./docker-start.sh"
fi
