#!/bin/bash

echo "🎵 Iniciando Music Agent Bot con Docker Compose..."

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor, instala Docker primero."
    exit 1
fi

# Verificar si Docker Compose está instalado
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose no está instalado. Por favor, instala Docker Compose primero."
    exit 1
fi

# Verificar si existe el archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado. Copiando desde env.docker..."
    cp env.docker .env
    echo "📝 Por favor, edita el archivo .env con tus credenciales antes de continuar."
    echo "   nano .env"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p logs

# Crear directorio de configuración si no existe
mkdir -p config

# Construir y ejecutar
echo "🔨 Construyendo imagen..."
docker-compose build

echo "🚀 Iniciando servicios..."
docker-compose up -d

echo "✅ Bot iniciado correctamente!"
echo ""
echo "📋 Comandos útiles:"
echo "   Ver logs: docker-compose logs -f"
echo "   Parar: docker-compose down"
echo "   Reiniciar: docker-compose restart"
echo "   Estado: docker-compose ps"
echo ""
echo "📱 Busca tu bot en Telegram y escribe /start para comenzar"
