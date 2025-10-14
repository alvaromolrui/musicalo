#!/bin/bash

# Script para construir y subir la imagen a Docker Hub
# Uso: ./build-and-push.sh [version]

set -e

# Configuración
DOCKER_USERNAME="alvaromolrui"
IMAGE_NAME="musicalo"
VERSION=${1:-latest}
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$VERSION"

echo "🎵 Music Agent Bot - Build and Push"
echo "=================================="
echo ""

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor, instala Docker primero."
    exit 1
fi

# Verificar que estamos logueados en Docker Hub
if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
    echo "🔐 Iniciando sesión en Docker Hub..."
    docker login
fi

echo "🏗️ Construyendo imagen: $FULL_IMAGE_NAME"
echo ""

# Construir imagen
docker build -t $FULL_IMAGE_NAME .

# También taggear como latest si no es latest
if [ "$VERSION" != "latest" ]; then
    echo "🏷️ Taggeando como latest..."
    docker tag $FULL_IMAGE_NAME $DOCKER_USERNAME/$IMAGE_NAME:latest
fi

echo ""
echo "📤 Subiendo a Docker Hub..."

# Push de la imagen
docker push $FULL_IMAGE_NAME

if [ "$VERSION" != "latest" ]; then
    docker push $DOCKER_USERNAME/$IMAGE_NAME:latest
fi

echo ""
echo "✅ ¡Imagen subida correctamente!"
echo ""
echo "🐳 Para usar la imagen:"
echo "   docker pull $FULL_IMAGE_NAME"
echo "   docker run -d --name music-agent-bot $FULL_IMAGE_NAME"
echo ""
echo "📋 O con docker-compose:"
echo "   docker-compose -f docker-compose.production.yml up -d"
echo ""
echo "🌐 Ver en Docker Hub: https://hub.docker.com/r/$DOCKER_USERNAME/$IMAGE_NAME"
