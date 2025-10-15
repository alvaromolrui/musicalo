#!/bin/bash

echo "📋 Mostrando logs de Musicalo..."
echo "🛑 Presiona Ctrl+C para salir"
echo ""

# Mostrar logs en tiempo real
docker-compose logs -f musicalo
