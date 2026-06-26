#!/bin/bash
set -e

echo "🎵 Iniciando Musicalo..."

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /app/logs/bot.log
}

mkdir -p /app/logs

MODE="${START_MODE:-telegram}"
log "Modo de arranque: $MODE"

# --- Validación de variables críticas ---

if [ -z "$GEMINI_API_KEY" ]; then
    log "❌ ERROR: GEMINI_API_KEY no está configurado"
    exit 1
fi

# TELEGRAM_BOT_TOKEN solo es obligatorio en modos que usan Telegram
if [ "$MODE" = "telegram" ] || [ "$MODE" = "both" ]; then
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        log "❌ ERROR: TELEGRAM_BOT_TOKEN no está configurado (requerido en modo '$MODE')"
        exit 1
    fi
fi

if [ -z "$LISTENBRAINZ_USERNAME" ]; then
    log "⚠️  WARNING: LISTENBRAINZ_USERNAME no está configurado"
fi

log "✅ Configuración verificada"
log "📋 Configuración:"
log "   - Modo: $MODE"
log "   - Navidrome URL: ${NAVIDROME_URL:-http://host.docker.internal:4533}"
log "   - ListenBrainz User: ${LISTENBRAINZ_USERNAME:-No configurado}"
log "   - MusicBrainz: ${ENABLE_MUSICBRAINZ:-false}"
log "   - Host: ${HOST:-0.0.0.0} | Port: ${PORT:-8000}"

# --- Esperar a Navidrome (si está configurado) ---
if [ ! -z "$NAVIDROME_URL" ]; then
    log "🔍 Verificando conectividad con Navidrome..."
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$NAVIDROME_URL/app/" > /dev/null 2>&1; then
            log "✅ Navidrome disponible"
            break
        else
            log "⏳ Esperando Navidrome... ($attempt/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    if [ $attempt -gt $max_attempts ]; then
        log "⚠️  No se pudo conectar con Navidrome, continuando..."
    fi
fi

# --- Señales ---
cleanup() {
    log "🛑 Deteniendo Musicalo..."
    exit 0
}
trap cleanup SIGTERM SIGINT

# --- Arrancar ---
log "🚀 Arrancando en modo: $MODE"
exec python start-bot.py 2>&1 | tee -a /app/logs/bot.log
