#!/bin/bash

# Script para construir y subir imagen de pruebas de Docker
# Uso: ./build-testing.sh

set -e

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Construyendo imagen de pruebas de Musicalo...${NC}"

# Obtener la rama actual
BRANCH=$(git branch --show-current)
echo -e "${GREEN}📌 Rama actual: $BRANCH${NC}"

# Definir variables
IMAGE_NAME="alvaromolrui/musicalo"
TAG="testing"
FULL_IMAGE="$IMAGE_NAME:$TAG"

# Verificar que estamos en la rama de pruebas
if [ "$BRANCH" != "feature/ai-natural-language-interaction" ]; then
    echo -e "${RED}⚠️  Advertencia: No estás en la rama feature/ai-natural-language-interaction${NC}"
    echo -e "${RED}   Rama actual: $BRANCH${NC}"
    read -p "¿Continuar de todos modos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Construcción cancelada${NC}"
        exit 1
    fi
fi

# Construir la imagen
echo -e "${BLUE}🔨 Construyendo imagen Docker...${NC}"
docker build -t $FULL_IMAGE .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Imagen construida exitosamente: $FULL_IMAGE${NC}"
else
    echo -e "${RED}❌ Error construyendo la imagen${NC}"
    exit 1
fi

# Preguntar si quiere subir a Docker Hub
read -p "¿Subir imagen a Docker Hub? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}📤 Subiendo imagen a Docker Hub...${NC}"
    docker push $FULL_IMAGE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Imagen subida exitosamente a Docker Hub${NC}"
        echo -e "${GREEN}   Imagen: $FULL_IMAGE${NC}"
    else
        echo -e "${RED}❌ Error subiendo la imagen${NC}"
        echo -e "${RED}   Asegúrate de estar autenticado: docker login${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎉 Proceso completado${NC}"
echo ""
echo -e "${BLUE}📋 Para probar en tu servidor:${NC}"
echo ""
echo "Opción 1 - Editar docker-compose.yml:"
echo "  1. Cambiar 'image: alvaromolrui/musicalo:latest'"
echo "     por 'image: alvaromolrui/musicalo:testing'"
echo "  2. docker-compose pull"
echo "  3. docker-compose down && docker-compose up -d"
echo ""
echo "Opción 2 - Comando rápido:"
echo "  docker-compose down"
echo "  docker run -d --name musicalo-testing --env-file .env -p 8000:8000 $FULL_IMAGE"
echo ""
echo "Ver logs:"
echo "  docker logs -f musicalo-testing"
echo ""

