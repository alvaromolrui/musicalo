#!/bin/bash

# Script para detener la versión de testing
# Uso: ./docker-testing-stop.sh

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Deteniendo Musicalo (Testing)...${NC}"

docker-compose -f docker-compose.testing.yml down

echo -e "${GREEN}✅ Contenedor de testing detenido${NC}"

