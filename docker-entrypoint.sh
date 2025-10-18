#!/bin/bash
set -e

echo "🎵 Iniciando Musicalo..."

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /app/logs/bot.log
}

# Crear directorio de logs si no existe
mkdir -p /app/logs

# Verificar variables de entorno críticas
log "Verificando configuración..."

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    log "❌ ERROR: TELEGRAM_BOT_TOKEN no está configurado"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    log "❌ ERROR: GEMINI_API_KEY no está configurado"
    exit 1
fi

if [ -z "$LISTENBRAINZ_USERNAME" ]; then
    log "⚠️  WARNING: LISTENBRAINZ_USERNAME no está configurado"
fi

log "✅ Configuración verificada"

# Mostrar configuración (sin tokens)
log "📋 Configuración:"
log "   - Navidrome URL: ${NAVIDROME_URL:-http://host.docker.internal:4533}"
log "   - ListenBrainz User: ${LISTENBRAINZ_USERNAME:-No configurado}"
log "   - Last.fm User: ${LASTFM_USERNAME:-No configurado}"
log "   - MusicBrainz: ${ENABLE_MUSICBRAINZ:-false} (Batch: ${MUSICBRAINZ_BATCH_SIZE:-20}, Max: ${MUSICBRAINZ_MAX_TOTAL:-100})"
log "   - Debug Mode: ${DEBUG:-False}"
log "   - Host: ${HOST:-0.0.0.0}"
log "   - Port: ${PORT:-8000}"

# Esperar a que Navidrome esté disponible (si está configurado)
if [ ! -z "$NAVIDROME_URL" ]; then
    log "🔍 Verificando conectividad con Navidrome..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$NAVIDROME_URL/app/" > /dev/null 2>&1; then
            log "✅ Navidrome está disponible"
            break
        else
            log "⏳ Esperando Navidrome... (intento $attempt/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log "⚠️  WARNING: No se pudo conectar con Navidrome, continuando..."
    fi
fi

# Bot usa modo polling (no necesita webhooks)
log "📡 Usando modo polling para comunicación con Telegram"

# Función para manejo de señales
cleanup() {
    log "🛑 Deteniendo bot..."
    log "✅ Bot detenido correctamente"
    exit 0
}

# Capturar señales para limpieza
trap cleanup SIGTERM SIGINT

# Iniciar el bot
log "🚀 Iniciando Musicalo..."
log "📱 Busca tu bot en Telegram y escribe /start para comenzar"

# Ejecutar el bot con logging
exec python start-bot.py 2>&1 | tee -a /app/logs/bot.log
