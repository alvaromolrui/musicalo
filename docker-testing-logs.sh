#!/bin/bash

# Script para ver logs de la versión de testing
# Uso: ./docker-testing-logs.sh [--tail N]

if [ "$1" == "--tail" ]; then
    TAIL=${2:-100}
    docker-compose -f docker-compose.testing.yml logs --tail=$TAIL
else
    docker-compose -f docker-compose.testing.yml logs -f
fi

