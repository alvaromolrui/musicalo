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
echo -e "${BLUE}📋 Próximos pasos:${NC}"
echo "1. En tu servidor, detén el contenedor de pruebas si existe:"
echo "   docker-compose -f docker-compose.testing.yml down"
echo ""
echo "2. Descarga la nueva imagen:"
echo "   docker pull $FULL_IMAGE"
echo ""
echo "3. Inicia el contenedor de pruebas:"
echo "   docker-compose -f docker-compose.testing.yml up -d"
echo ""
echo "4. Verifica los logs:"
echo "   docker-compose -f docker-compose.testing.yml logs -f"
echo ""

