# 🧪 Guía de Despliegue - Versión de Pruebas

Esta guía te ayudará a desplegar la **versión de pruebas** de Musicalo en Docker, en paralelo con tu versión de producción.

## 🎯 Características de la Versión de Pruebas

- ✅ **Nueva funcionalidad**: Interacción con lenguaje natural usando Gemini AI Function Calling
- ✅ Corre en **paralelo** con producción (puerto diferente)
- ✅ Bot de Telegram **separado** (para no interferir con producción)
- ✅ Logs y configuración **independientes**
- ✅ Puede compartir credenciales de Navidrome, Last.fm y Gemini

## 📋 Requisitos Previos

### 1. Crear un Bot de Telegram para Pruebas

**¡MUY IMPORTANTE!** Debes crear un bot de Telegram separado para testing:

1. Abre Telegram y habla con [@BotFather](https://t.me/BotFather)
2. Usa el comando `/newbot`
3. Dale un nombre (ej: "Musicalo Test Bot")
4. Elige un username (ej: "musicalo_test_bot")
5. **Guarda el token** que te proporciona BotFather

### 2. Tener Docker y Docker Compose Instalados

```bash
docker --version
docker-compose --version
```

## 🚀 Despliegue en el Servidor

### Opción A: Usando la Imagen Pre-construida (Recomendado)

#### 1. En tu máquina local (opcional - solo si quieres construir)

Si quieres construir y subir la imagen desde tu máquina:

```bash
# Asegúrate de estar en la rama correcta
git checkout feature/ai-natural-language-interaction

# Construir y subir la imagen
chmod +x build-testing.sh
./build-testing.sh
```

#### 2. En tu servidor

```bash
# 1. Conectar al servidor
ssh tu-usuario@tu-servidor

# 2. Ir al directorio del proyecto
cd /ruta/a/musicalo

# 3. Hacer pull de la rama de testing
git fetch
git checkout feature/ai-natural-language-interaction

# 4. Copiar el archivo de variables de entorno
cp env.testing .env.testing

# 5. Editar las variables de entorno
nano .env.testing

# IMPORTANTE: Configurar al menos:
# - TELEGRAM_BOT_TOKEN_TESTING (el token del bot de pruebas)
# - GEMINI_API_KEY
# - NAVIDROME_URL, NAVIDROME_USERNAME, NAVIDROME_PASSWORD

# 6. Descargar la imagen de testing
docker pull alvaromolrui/musicalo:testing

# 7. Iniciar el contenedor de testing
docker-compose -f docker-compose.testing.yml --env-file .env.testing up -d

# 8. Verificar que está corriendo
docker-compose -f docker-compose.testing.yml ps

# 9. Ver los logs en tiempo real
docker-compose -f docker-compose.testing.yml logs -f
```

### Opción B: Construir Directamente en el Servidor

```bash
# 1-5. Igual que la Opción A

# 6. Construir la imagen localmente en el servidor
docker build -t alvaromolrui/musicalo:testing .

# 7. Iniciar el contenedor
docker-compose -f docker-compose.testing.yml --env-file .env.testing up -d
```

## 🔍 Verificación

### 1. Verificar que el contenedor está corriendo

```bash
docker ps | grep musicalo-testing
```

Deberías ver algo como:
```
CONTAINER ID   IMAGE                           STATUS         PORTS
abc123def456   alvaromolrui/musicalo:testing   Up 2 minutes   0.0.0.0:8001->8000/tcp
```

### 2. Ver los logs

```bash
# Logs en tiempo real
docker-compose -f docker-compose.testing.yml logs -f

# Últimas 100 líneas
docker-compose -f docker-compose.testing.yml logs --tail=100
```

### 3. Probar el bot en Telegram

1. Busca tu bot de pruebas en Telegram (el que creaste con BotFather)
2. Envía `/start`
3. **Prueba el lenguaje natural**:
   - "Recomiéndame música rock"
   - "Busca Queen en mi biblioteca"
   - "Muéstrame mis estadísticas"
   - "¿Qué es el jazz?"

## 🎭 Comparación: Producción vs Testing

| Aspecto | Producción | Testing |
|---------|-----------|---------|
| **Puerto** | 8000 | 8001 |
| **Container Name** | `musicalo` | `musicalo-testing` |
| **Docker Image** | `alvaromolrui/musicalo:latest` | `alvaromolrui/musicalo:testing` |
| **Bot Token** | Token de producción | Token de testing (diferente) |
| **Docker Compose** | `docker-compose.yml` | `docker-compose.testing.yml` |
| **ENV File** | `.env` | `.env.testing` |
| **Logs Volume** | `logs` | `logs-testing` |
| **Network** | `musicalo-network` | `musicalo-testing-network` |

## 🔄 Actualizar la Versión de Testing

```bash
# 1. Hacer pull de los últimos cambios
git checkout feature/ai-natural-language-interaction
git pull

# 2. Detener el contenedor actual
docker-compose -f docker-compose.testing.yml down

# 3. Descargar la imagen actualizada
docker pull alvaromolrui/musicalo:testing

# 4. Iniciar con la nueva imagen
docker-compose -f docker-compose.testing.yml --env-file .env.testing up -d

# 5. Verificar logs
docker-compose -f docker-compose.testing.yml logs -f
```

## 🛑 Detener la Versión de Testing

```bash
# Detener y eliminar contenedor
docker-compose -f docker-compose.testing.yml down

# Detener pero mantener el contenedor
docker-compose -f docker-compose.testing.yml stop

# Reiniciar
docker-compose -f docker-compose.testing.yml restart
```

## 🐛 Troubleshooting

### El bot no responde

```bash
# Verificar logs
docker-compose -f docker-compose.testing.yml logs -f musicalo-testing

# Verificar que el token es correcto
docker-compose -f docker-compose.testing.yml exec musicalo-testing env | grep TELEGRAM
```

### Puerto 8001 ocupado

Edita `docker-compose.testing.yml` y cambia el puerto:
```yaml
ports:
  - "8002:8000"  # Cambiar 8001 por otro puerto
```

### Problemas con Gemini AI

```bash
# Verificar la API key
docker-compose -f docker-compose.testing.yml exec musicalo-testing env | grep GEMINI

# Ver logs específicos de Gemini
docker-compose -f docker-compose.testing.yml logs -f | grep -i gemini
```

## ✅ Testing Completado - Pasar a Producción

Una vez que hayas probado y estés satisfecho con la versión de testing:

```bash
# 1. Hacer merge a main
git checkout main
git merge feature/ai-natural-language-interaction

# 2. Construir y subir imagen de producción
./build-and-push.sh  # o tu script de producción

# 3. Actualizar producción
docker-compose pull
docker-compose up -d

# 4. Detener testing (opcional)
docker-compose -f docker-compose.testing.yml down
```

## 📚 Más Información

- **Nueva funcionalidad**: Lenguaje natural con IA (ver README principal)
- **Arquitectura**: Ver `README.md`
- **API de Gemini**: https://ai.google.dev/docs

## 🆘 Soporte

Si tienes problemas:
1. Revisa los logs: `docker-compose -f docker-compose.testing.yml logs -f`
2. Verifica las variables de entorno en `.env.testing`
3. Asegúrate de que el bot de Telegram es correcto y diferente al de producción

