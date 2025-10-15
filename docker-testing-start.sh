#!/bin/bash

# Script para iniciar la versión de testing en el servidor
# Uso: ./docker-testing-start.sh

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🧪 Iniciando Musicalo (Testing)...${NC}"

# Verificar que existe .env.testing
if [ ! -f .env.testing ]; then
    echo -e "${YELLOW}⚠️  No se encontró .env.testing${NC}"
    echo -e "${YELLOW}   Creando desde env.testing...${NC}"
    
    if [ -f env.testing ]; then
        cp env.testing .env.testing
        echo -e "${GREEN}✅ Archivo .env.testing creado${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANTE: Edita .env.testing con tus credenciales antes de continuar${NC}"
        echo ""
        read -p "Presiona Enter cuando hayas configurado .env.testing..."
    else
        echo -e "${YELLOW}❌ No se encontró env.testing. Asegúrate de estar en el directorio correcto.${NC}"
        exit 1
    fi
fi

# Verificar que TELEGRAM_BOT_TOKEN_TESTING está configurado
if ! grep -q "^TELEGRAM_BOT_TOKEN_TESTING=.\\+" .env.testing; then
    echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN_TESTING no está configurado en .env.testing${NC}"
    echo -e "${YELLOW}   Debes crear un bot de Telegram separado para testing con @BotFather${NC}"
    exit 1
fi

# Verificar que estamos en la rama correcta
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "feature/ai-natural-language-interaction" ]; then
    echo -e "${YELLOW}⚠️  No estás en la rama feature/ai-natural-language-interaction${NC}"
    echo -e "${YELLOW}   Rama actual: $BRANCH${NC}"
    read -p "¿Continuar de todos modos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Descargar imagen actualizada
echo -e "${BLUE}📥 Descargando imagen de testing...${NC}"
docker pull alvaromolrui/musicalo:testing

# Iniciar contenedor
echo -e "${BLUE}🚀 Iniciando contenedor...${NC}"
docker-compose -f docker-compose.testing.yml --env-file .env.testing up -d

# Esperar un momento
sleep 2

# Verificar estado
echo ""
echo -e "${GREEN}✅ Contenedor iniciado${NC}"
echo ""
docker-compose -f docker-compose.testing.yml ps

echo ""
echo -e "${BLUE}📋 Comandos útiles:${NC}"
echo "  Ver logs:     docker-compose -f docker-compose.testing.yml logs -f"
echo "  Detener:      docker-compose -f docker-compose.testing.yml down"
echo "  Reiniciar:    docker-compose -f docker-compose.testing.yml restart"
echo "  Estado:       docker-compose -f docker-compose.testing.yml ps"
echo ""

