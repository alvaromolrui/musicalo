# Music Agent Bot 🎵🤖

Un bot de Telegram inteligente que utiliza IA para generar recomendaciones musicales personalizadas basadas en tu biblioteca de Navidrome y tus scrobbles de ListenBrainz.

## ✨ Características

- **🤖 Bot de Telegram**: Interfaz simple y accesible desde cualquier dispositivo
- **🎵 Integración con Navidrome**: Acceso completo a tu biblioteca musical autoalojada
- **📊 Scrobbles de ListenBrainz**: Análisis de tus hábitos de escucha y patrones (open source)
- **🧠 Recomendaciones con IA**: Sistema inteligente usando Google Gemini que aprende de tus gustos
- **💬 Interacción natural**: Chat directo con comandos simples y botones interactivos
- **📱 Acceso móvil**: Optimizado para usar desde tu smartphone

## 🏗️ Arquitectura

### Bot de Telegram
- **Comandos simples**: `/recommend`, `/library`, `/stats`, `/search`
- **Botones interactivos**: Me gusta, no me gusta, más recomendaciones
- **Notificaciones**: Alertas sobre nueva música y descubrimientos
- **Conversación natural**: Interacción fluida con la IA

### Backend (Python + FastAPI)
- **Servicios integrados**: 
  - `NavidromeService`: Conexión con tu servidor Navidrome
  - `ListenBrainzService`: Integración con la API de ListenBrainz (open source)
  - `MusicRecommendationService`: IA con Google Gemini para recomendaciones personalizadas
  - `TelegramService`: Manejo de interacciones del bot

## 🚀 Instalación

### Prerrequisitos
- **Docker y Docker Compose** instalados
- Servidor Navidrome funcionando
- Cuenta de ListenBrainz (opcional: token de API)
- API key de Google Gemini
- Token de bot de Telegram

### Instalación con Docker (Recomendado)

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd musicAgent
```

2. **Configurar entorno**
```bash
# Copiar archivo de configuración para Docker
cp env.docker .env

# Editar .env con tus credenciales
nano .env
```

3. **Crear bot de Telegram**
   - Busca [@BotFather](https://t.me/botfather) en Telegram
   - Crea un nuevo bot con `/newbot`
   - Guarda el token en tu archivo `.env`

4. **Ejecutar con Docker Compose**
```bash
# Opción 1: Script automático
./docker-start.sh

# Opción 2: Manual
docker-compose up -d

# Opción 3: Windows
docker-start.sh
```

### Instalación Manual (Sin Docker)

Si prefieres instalar sin Docker:

1. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

2. **Configurar entorno**
```bash
cp env.example .env
nano .env
```

3. **Ejecutar directamente**
```bash
python start-bot.py
```

## ⚙️ Configuración

### Variables de entorno (.env)

**Para Docker:**
```env
# Navidrome Configuration (usar host.docker.internal para Docker)
NAVIDROME_URL=http://host.docker.internal:4533
NAVIDROME_USERNAME=admin
NAVIDROME_PASSWORD=password

# ListenBrainz Configuration
LISTENBRAINZ_USERNAME=your_listenbrainz_username
LISTENBRAINZ_TOKEN=your_listenbrainz_token

# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
# Solo para webhooks con IP fija
# TELEGRAM_WEBHOOK_URL=http://tu-ip-publica:8000

# Application Configuration
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

**Para instalación manual:**
```env
# Navidrome Configuration
NAVIDROME_URL=http://localhost:4533
NAVIDROME_USERNAME=admin
NAVIDROME_PASSWORD=password

# ListenBrainz Configuration
LISTENBRAINZ_USERNAME=your_listenbrainz_username
LISTENBRAINZ_TOKEN=your_listenbrainz_token

# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# Application Configuration
DEBUG=True
HOST=localhost
PORT=8000
```

### Obtener Credenciales

#### Bot de Telegram
1. Busca [@BotFather](https://t.me/botfather) en Telegram
2. Envía `/newbot` y sigue las instrucciones
3. Elige un nombre y username para tu bot
4. Guarda el token que te proporciona

#### ListenBrainz
1. Ve a [ListenBrainz](https://listenbrainz.org/)
2. Regístrate con tu cuenta de MusicBrainz
3. Opcional: Obtén un token de API para límites más altos

#### Google Gemini API
1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crea una nueva API key
3. Es gratuita hasta 15 requests por minuto

## 📱 Uso del Bot

### Comandos Principales

- **`/start`** - Iniciar el bot y ver el menú principal
- **`/help`** - Mostrar ayuda detallada
- **`/recommend`** - Obtener recomendaciones personalizadas con IA
- **`/library`** - Explorar tu biblioteca musical
- **`/stats`** - Ver estadísticas de escucha
- **`/search <término>`** - Buscar música en tu biblioteca

### Ejemplos de Uso

```
/recommend          # Obtener recomendaciones
/library            # Ver biblioteca
/stats              # Ver estadísticas
/search queen       # Buscar Queen
/search bohemian    # Buscar "bohemian"
```

### Interacciones

- **Botones inline**: ❤️ Me gusta, 👎 No me gusta, 🔄 Más recomendaciones
- **Teclado personalizado**: Botones rápidos para comandos comunes
- **Notificaciones**: Alertas sobre nueva música y descubrimientos

## 🤖 Comandos del Bot

### Comandos Básicos
- **`/start`** - Iniciar bot y mostrar bienvenida
- **`/help`** - Ayuda detallada con ejemplos

### Comandos de Música
- **`/recommend`** - Recomendaciones personalizadas con IA
- **`/library`** - Explorar biblioteca musical
- **`/stats`** - Estadísticas de escucha y patrones
- **`/search <término>`** - Buscar canciones, artistas o álbumes

### Interacciones
- **Botones de reacción**: ❤️ Me gusta, 👎 No me gusta
- **Navegación**: 🔄 Más recomendaciones, 📚 Ver biblioteca
- **Acciones**: 🎵 Reproducir en Navidrome

## 🧠 Algoritmo de Recomendaciones

El sistema utiliza múltiples enfoques:

1. **Análisis de perfil**: Patrones de escucha, géneros favoritos, diversidad
2. **IA generativa**: Google Gemini para sugerencias contextuales
3. **Similitud musical**: Artistas y géneros relacionados
4. **Filtrado colaborativo**: Basado en usuarios con gustos similares

## 🎨 Tecnologías

### Backend
- **python-telegram-bot**: Framework para bots de Telegram
- **FastAPI**: API REST opcional para webhooks
- **Google Gemini**: IA para recomendaciones contextuales
- **httpx**: Cliente HTTP asíncrono
- **Pydantic**: Validación de datos

### Bot
- **python-telegram-bot 20.7**: Framework moderno para bots
- **Inline Keyboards**: Botones interactivos
- **Reply Keyboards**: Teclados personalizados
- **Callback Handlers**: Manejo de interacciones

## 📊 Características de la IA

- **Análisis de género**: Identificación automática de preferencias
- **Patrones temporales**: Horarios de escucha preferidos
- **Diversidad musical**: Medición de amplitud de gustos
- **Descubrimiento**: Sugerencias para expandir horizontes
- **Explicabilidad**: Razones claras para cada recomendación

## 🔮 Roadmap

- [ ] **Notificaciones inteligentes**: Alertas basadas en patrones de escucha
- [ ] **Playlists automáticas**: Creación de playlists por IA
- [ ] **Integración con Spotify**: Acceso a biblioteca de Spotify
- [ ] **Recomendaciones colaborativas**: Basadas en usuarios similares
- [ ] **Análisis de sentimientos**: Recomendaciones por estado de ánimo
- [ ] **Modo conversacional**: Chat natural con la IA
- [ ] **Estadísticas avanzadas**: Gráficos y análisis detallados
- [ ] **Sincronización múltiple**: Múltiples cuentas de música

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [Navidrome](https://github.com/navidrome/navidrome) por el excelente servidor de música
- [ListenBrainz](https://listenbrainz.org/) por la API de scrobbling open source
- [Google Gemini](https://ai.google.dev/) por las capacidades de IA
- La comunidad de desarrolladores de música open source

## 🐳 Gestión con Docker

### Scripts de gestión incluidos:

```bash
# Iniciar el bot
./docker-start.sh

# Ver logs en tiempo real
./docker-logs.sh

# Ver estado del bot
./docker-status.sh

# Reiniciar el bot
./docker-restart.sh

# Actualizar el bot
./docker-update.sh

# Parar el bot
./docker-stop.sh
```

### Comandos Docker Compose manuales:

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Reiniciar
docker-compose restart

# Ver estado
docker-compose ps
```

### Características de Docker:

- ✅ **Aislamiento**: El bot corre en su propio contenedor
- ✅ **Reinicio automático**: Si falla, se reinicia automáticamente
- ✅ **Logs persistentes**: Los logs se guardan en `./logs/`
- ✅ **Health checks**: Monitoreo automático del estado
- ✅ **Límites de recursos**: Control de memoria y CPU
- ✅ **Nginx opcional**: Proxy reverso con SSL

## 🚀 Inicio Rápido

### Con Docker (Recomendado):
```bash
# 1. Configurar .env con tus credenciales
cp env.docker .env
# Editar .env con tu token de bot, API keys, etc.

# 2. Ejecutar con Docker
./docker-start.sh

# 3. Buscar tu bot en Telegram y escribir /start
```

### Sin Docker:
```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar .env con tus credenciales
cp env.example .env
# Editar .env con tu token de bot, API keys, etc.

# 3. Ejecutar el bot
python start-bot.py

# 4. Buscar tu bot en Telegram y escribir /start
```

---

**Music Agent Bot** - Descubre nueva música con el poder de la IA y la simplicidad de Telegram 🎵🤖
