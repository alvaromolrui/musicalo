#!/bin/bash

# Script para reiniciar la versión de testing
# Uso: ./docker-testing-restart.sh

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}🔄 Reiniciando Musicalo (Testing)...${NC}"

docker-compose -f docker-compose.testing.yml restart

sleep 2

echo -e "${GREEN}✅ Contenedor de testing reiniciado${NC}"
echo ""
docker-compose -f docker-compose.testing.yml ps

