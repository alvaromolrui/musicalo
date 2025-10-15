#!/bin/bash

# Script para deploy rápido usando la imagen de Docker Hub
# Uso: ./quick-deploy.sh

set -e

echo "🚀 Musicalo - Deploy Rápido"
echo "=================================="
echo ""

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor, instala Docker primero."
    exit 1
fi

# Verificar si existe el archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado. Copiando desde env.docker..."
    cp env.docker .env
    echo ""
    echo "📝 ¡IMPORTANTE! Edita el archivo .env con tus credenciales:"
    echo "   nano .env"
    echo ""
    echo "   Necesitas configurar:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - GEMINI_API_KEY"
    echo "   - LISTENBRAINZ_USERNAME"
    echo "   - NAVIDROME_URL, NAVIDROME_USERNAME, NAVIDROME_PASSWORD"
    echo ""
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p logs

echo "📥 Descargando última imagen de Docker Hub..."
docker pull alvaromolrui/musicalo:latest

echo ""
echo "🚀 Iniciando Musicalo..."

# Usar docker-compose de producción
docker-compose -f docker-compose.production.yml up -d

echo ""
echo "✅ ¡Bot iniciado correctamente!"
echo ""
echo "📋 Comandos útiles:"
echo "   Ver logs: docker-compose -f docker-compose.production.yml logs -f"
echo "   Parar: docker-compose -f docker-compose.production.yml down"
echo "   Reiniciar: docker-compose -f docker-compose.production.yml restart"
echo "   Estado: docker-compose -f docker-compose.production.yml ps"
echo ""
echo "📱 Busca tu bot en Telegram y escribe /start para comenzar"
echo "🌐 Ver en Docker Hub: https://hub.docker.com/r/alvaromolrui/musicalo"
