# 🚀 Inicio Rápido - Testing

## En tu máquina local (para construir la imagen)

```bash
# 1. Asegúrate de estar en la rama correcta
git checkout feature/ai-natural-language-interaction

# 2. Construir y subir imagen de testing
./build-testing.sh
```

## En tu servidor (para desplegar)

```bash
# 1. Conectar al servidor
ssh tu-usuario@tu-servidor

# 2. Ir al proyecto
cd /ruta/a/musicalo

# 3. Actualizar código
git fetch
git checkout feature/ai-natural-language-interaction
git pull

# 4. Configurar variables de entorno
cp env.testing .env.testing
nano .env.testing
# ⚠️ IMPORTANTE: Configurar TELEGRAM_BOT_TOKEN_TESTING

# 5. Iniciar testing
./docker-testing-start.sh

# 6. Ver logs
./docker-testing-logs.sh
```

## Crear Bot de Telegram para Testing

1. Abre Telegram
2. Busca `@BotFather`
3. Envía `/newbot`
4. Sigue las instrucciones
5. Copia el token a `.env.testing`

## Comandos Útiles

```bash
# Iniciar
./docker-testing-start.sh

# Ver logs
./docker-testing-logs.sh

# Detener
./docker-testing-stop.sh

# Reiniciar
./docker-testing-restart.sh

# Estado
docker-compose -f docker-compose.testing.yml ps
```

## ✨ Probar la Nueva Funcionalidad

En Telegram, escribe directamente (sin comandos):

- "Recomiéndame música rock"
- "Busca Queen"
- "Muéstrame mis estadísticas"
- "¿Qué es el jazz?"

El bot interpretará tu mensaje y ejecutará la acción apropiada. 🎵

## 📖 Documentación Completa

Ver `TESTING.md` para instrucciones detalladas.

