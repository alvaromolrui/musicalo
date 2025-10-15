# Musicalo 🎵🤖

[![Version](https://img.shields.io/badge/Version-1.1.1--alpha-orange.svg)](VERSION)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-alvaromolrui%2Fmusicalo-blue?logo=docker)](https://hub.docker.com/r/alvaromolrui/musicalo)
[![GitHub](https://img.shields.io/badge/GitHub-alvaromolrui%2Fmusicalo-black?logo=github)](https://github.com/alvaromolrui/musicalo)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://telegram.org)

Un bot de Telegram inteligente que utiliza IA para generar recomendaciones musicales personalizadas basadas en tu biblioteca de Navidrome y tus scrobbles de ListenBrainz o Last.fm.

## ✨ Características

- **🤖 Lenguaje Natural**: Habla directamente con el bot sin necesidad de comandos
- **🎨 Peticiones Específicas (NUEVO)**: Describe exactamente lo que buscas con todos los detalles
- **🎯 IA Contextual**: Gemini AI entiende intenciones y responde con tus datos reales
- **🎵 Integración con Navidrome**: Acceso completo a tu biblioteca musical autoalojada
- **📊 Scrobbles de Last.fm/ListenBrainz**: Análisis de tus hábitos de escucha y patrones
- **🧠 Recomendaciones Inteligentes**: Sistema usando Google Gemini que aprende de tus gustos
- **🔄 Variedad**: Diferentes recomendaciones cada vez
- **📱 Acceso móvil**: Optimizado para usar desde tu smartphone
- **🔒 Bot Privado (NUEVO)**: Restringe el acceso solo a usuarios autorizados

### 🎨 Recomendaciones Ultra-Específicas

Ahora puedes ser todo lo específico que quieras en tus peticiones:

```
✅ "Rock progresivo de los 70s con sintetizadores"
✅ "Música energética con buenos solos de guitarra"
✅ "Jazz suave instrumental para estudiar"
✅ "Metal melódico con voces limpias"
✅ "Álbumes conceptuales melancólicos"
```

La IA entiende múltiples criterios y genera recomendaciones precisas que cumplen **todos** tus requisitos.

## 🏗️ Arquitectura

### Bot de Telegram
- **💬 Lenguaje Natural**: Escribe directamente sin comandos (ej: "recomiéndame un disco de Pink Floyd")
- **🎯 Comandos tradicionales**: `/recommend`, `/library`, `/stats`, `/search` (también funcionan)
- **🔘 Botones interactivos**: Me gusta, no me gusta, más recomendaciones
- **📊 Respuestas contextuales**: La IA usa tus datos reales de escucha
- **🎵 Recomendaciones variadas**: Diferentes sugerencias cada vez
- **🔄 Polling Mode**: No requiere configuración de webhooks, SSL ni puertos públicos

### Backend (Python + Telegram Bot API)
- **Servicios integrados**: 
  - `NavidromeService`: Conexión con tu servidor Navidrome
  - `ListenBrainzService`: Integración con la API de ListenBrainz (open source)
  - `LastFMService`: Integración con Last.fm para descubrimiento de música
  - `MusicRecommendationService`: IA con Google Gemini para recomendaciones personalizadas
  - `TelegramService`: Manejo de interacciones del bot en modo polling

## 🚀 Instalación

### Prerrequisitos
- **Docker y Docker Compose** (recomendado) o Python 3.11+
- Servidor **Navidrome** funcionando
- Cuenta de **ListenBrainz** o **Last.fm**
- **API key de Google Gemini** (gratuita)
- **Token de bot de Telegram**

> **Nota:** El bot usa **polling** para comunicarse con Telegram. No necesitas configurar webhooks, SSL, ni exponer puertos públicos.

### 🐳 Opción 1: Docker (Recomendado)

**Usando imagen de Docker Hub (más rápido):**

```bash
# 1. Clonar repositorio
git clone https://github.com/alvaromolrui/musicalo.git
cd musicalo

# 2. Configurar credenciales
cp env.example .env
nano .env  # Editar con tus credenciales

# 3. Iniciar con imagen pre-construida
docker-compose -f docker-compose.production.yml up -d
```

**Construyendo imagen localmente:**

```bash
# 1. Clonar y configurar (igual que arriba)
git clone https://github.com/alvaromolrui/musicalo.git
cd musicalo
cp env.example .env
nano .env

# 2. Construir e iniciar
docker-compose up -d
```

**Comandos útiles:**
```bash
./docker-start.sh      # Iniciar
./docker-logs.sh       # Ver logs
./docker-restart.sh    # Reiniciar
./docker-stop.sh       # Detener
```

### 📦 Opción 2: Instalación Manual (Sin Docker)

```bash
# 1. Clonar repositorio
git clone https://github.com/alvaromolrui/musicalo.git
cd musicalo

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar
cp env.example .env
nano .env
# Cambiar NAVIDROME_URL a: http://localhost:4533
# (para instalación local sin Docker)

# 4. Ejecutar
python start-bot.py
```

## ⚙️ Configuración

Copia el archivo `env.example` a `.env` y configura tus credenciales:

```bash
cp env.example .env
nano .env
```

El archivo `.env` está completamente documentado con comentarios explicativos para cada variable.

**Variables principales:**
- `NAVIDROME_URL`: URL de tu servidor Navidrome
- `LISTENBRAINZ_USERNAME` o `LASTFM_API_KEY`: Tu cuenta de scrobbling
- `GEMINI_API_KEY`: API key de Google Gemini (gratuita)
- `TELEGRAM_BOT_TOKEN`: Token de tu bot de Telegram (REQUERIDO)
- `TELEGRAM_ALLOWED_USER_IDS`: IDs permitidos para bot privado (RECOMENDADO)

> **Importante:** El bot usa **polling** por defecto. No necesitas configurar `TELEGRAM_WEBHOOK_URL`.

### Obtener Credenciales

#### Bot de Telegram
1. Busca [@BotFather](https://t.me/botfather) en Telegram
2. Envía `/newbot` y sigue las instrucciones
3. Elige un nombre y username para tu bot
4. Guarda el token que te proporciona

#### Obtener tu ID de Usuario (Para Bot Privado)
1. Busca [@userinfobot](https://t.me/userinfobot) en Telegram
2. Inicia conversación y el bot te mostrará tu ID
3. Copia el número de ID y agrégalo a `TELEGRAM_ALLOWED_USER_IDS` en tu archivo `.env`
4. Puedes agregar múltiples IDs separados por comas (ej: `123456789,987654321`)

#### ListenBrainz
1. Ve a [ListenBrainz](https://listenbrainz.org/)
2. Regístrate con tu cuenta de MusicBrainz
3. Opcional: Obtén un token de API para límites más altos

#### Google Gemini API
1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crea una nueva API key
3. Es gratuita hasta 15 requests por minuto

## 🔒 Seguridad: Bot Privado

Por defecto, cualquier usuario de Telegram puede interactuar con tu bot. Para hacerlo **privado y seguro**, configura la variable `TELEGRAM_ALLOWED_USER_IDS` con tu ID de usuario de Telegram.

### 🔐 Configurar Bot Privado

**Paso 1: Obtener tu ID de Usuario**
1. Abre Telegram y busca el bot [@userinfobot](https://t.me/userinfobot)
2. Inicia conversación con el bot
3. El bot te mostrará tu información, incluyendo tu **User ID** (un número como `123456789`)
4. Copia ese número

**Paso 2: Configurar IDs Permitidos**

Edita tu archivo `.env` y agrega tu ID:

```env
# Solo tú puedes usar el bot
TELEGRAM_ALLOWED_USER_IDS=123456789

# O múltiples usuarios (separados por comas)
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321,555444333
```

**Paso 3: Reiniciar el Bot**

```bash
# Si usas Docker
./docker-restart.sh

# Si lo ejecutas manualmente
python start-bot.py
```

### ✅ Verificar Configuración

Al iniciar, el bot mostrará en los logs:
- `🔒 Bot configurado en modo privado para N usuario(s)` - ✅ Está protegido
- `⚠️ Bot en modo público` - ⚠️ Cualquiera puede usarlo

### 🚫 ¿Qué pasa si alguien no autorizado intenta usar el bot?

Recibirá un mensaje como:
```
🚫 Acceso Denegado

Este bot es privado y solo puede ser usado por usuarios autorizados.

Tu ID de usuario es: 999888777

Si crees que deberías tener acceso, contacta con el administrador 
del bot y proporciona tu ID de usuario.
```

## 📱 Uso del Bot

### 💬 Lenguaje Natural (NUEVO - v1.1.0)

¡Ahora puedes hablar directamente con el bot sin comandos!

**Ejemplos:**
```
"recomiéndame un disco de algún grupo similar a Pink Floyd"
"¿cuál fue mi última canción?"
"dame 3 artistas parecidos a Queen"
"¿qué he escuchado hoy de rock?"
"busca música de Queen en mi biblioteca"
"¿qué es el jazz?" (preguntas generales sobre música)
```

La IA entiende tu intención y responde usando tus datos reales de Last.fm/ListenBrainz.

### 🎯 Comandos Tradicionales (también funcionan)

- **`/start`** - Iniciar el bot y ver el menú principal
- **`/help`** - Mostrar ayuda detallada
- **`/recommend`** - Obtener recomendaciones personalizadas con IA
- **`/library`** - Explorar tu biblioteca musical
- **`/stats`** - Ver estadísticas de escucha
- **`/search <término>`** - Buscar música en tu biblioteca
- **`/ask <pregunta>`** - Hacer preguntas sobre música

### Ejemplos con Comandos

```
/recommend                    # Recomendaciones generales
/recommend album rock         # Álbumes de rock
/recommend similar Queen      # Música similar a Queen
/library                      # Ver biblioteca
/stats                        # Ver estadísticas
/search queen                 # Buscar Queen
/ask ¿qué es el blues?       # Pregunta sobre música
```

### 🔘 Interacciones

- **Botones inline**: ❤️ Me gusta, 👎 No me gusta, 🔄 Más recomendaciones
- **Teclado personalizado**: Botones rápidos para comandos comunes
- **Respuestas conversacionales**: La IA responde de forma natural

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
- **python-telegram-bot 20.7**: Framework moderno para bots (modo polling)
- **Google Gemini**: IA para recomendaciones contextuales
- **httpx**: Cliente HTTP asíncrono para APIs
- **Pydantic**: Validación de datos
- **FastAPI**: API REST (opcional, no usado por defecto)

### Bot
- **Polling Mode**: Conexión persistente con Telegram (sin necesidad de webhooks)
- **Inline Keyboards**: Botones interactivos
- **Reply Keyboards**: Teclados personalizados
- **Callback Handlers**: Manejo de interacciones
- **Async/Await**: Operaciones asíncronas para mejor rendimiento

## 📊 Características de la IA

- **Análisis de género**: Identificación automática de preferencias
- **Patrones temporales**: Horarios de escucha preferidos
- **Diversidad musical**: Medición de amplitud de gustos
- **Descubrimiento**: Sugerencias para expandir horizontes
- **Explicabilidad**: Razones claras para cada recomendación

## 🔮 Roadmap

- [x] **Modo conversacional**: Chat natural con la IA ✅ (v1.1.0)
- [x] **Bot privado**: Control de acceso por usuario ✅ (v1.1.1)
- [ ] **Notificaciones inteligentes**: Alertas basadas en patrones de escucha
- [ ] **Playlists automáticas**: Creación de playlists por IA
- [ ] **Integración con Spotify**: Acceso a biblioteca de Spotify
- [ ] **Recomendaciones colaborativas**: Basadas en usuarios similares
- [ ] **Análisis de sentimientos**: Recomendaciones por estado de ánimo
- [ ] **Estadísticas avanzadas**: Gráficos y análisis detallados
- [ ] **Sincronización múltiple**: Múltiples cuentas de música

## 👨‍💻 Para Desarrolladores

### 🔧 Build y Push Manual

Si quieres construir y subir la imagen manualmente:

```bash
# Build y push a Docker Hub
./build-and-push.sh [version]

# Ejemplos:
./build-and-push.sh latest
./build-and-push.sh v1.0.0
./build-and-push.sh dev
```

### 🔄 CI/CD Automático

El repositorio incluye GitHub Actions que automáticamente:

- ✅ **Construye la imagen** en cada push a `main`
- ✅ **Sube a Docker Hub** como `alvaromolrui/musicalo:latest`
- ✅ **Multiplataforma** (AMD64 y ARM64)
- ✅ **Cache optimizado** para builds más rápidos
- ✅ **Tags automáticos** para releases

### 📦 Configurar GitHub Actions

Para que funcione el CI/CD automático:

1. **Ve a GitHub** → Tu repositorio → Settings → Secrets
2. **Añade estos secrets:**
   - `DOCKER_USERNAME`: `alvaromolrui`
   - `DOCKER_PASSWORD`: Tu token de Docker Hub

3. **Obtener token de Docker Hub:**
   - Ve a [hub.docker.com](https://hub.docker.com)
   - Settings → Security → New Access Token
   - Copia el token y pégalo en `DOCKER_PASSWORD`

### 🏷️ Releases y Versionado

```bash
# Crear release con tag
git tag v1.0.0
git push origin v1.0.0

# Esto automáticamente creará:
# - alvaromolrui/musicalo:v1.0.0
# - alvaromolrui/musicalo:1.0
# - alvaromolrui/musicalo:latest (si es la rama main)
```

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

### Archivos Docker Compose

El proyecto incluye dos configuraciones:

- **`docker-compose.yml`**: Construye la imagen localmente (para desarrollo)
- **`docker-compose.production.yml`**: Usa imagen de Docker Hub (para producción)

Usa el que prefieras según tus necesidades.

### Scripts de gestión incluidos

```bash
./docker-start.sh      # Iniciar el bot
./docker-logs.sh       # Ver logs en tiempo real
./docker-status.sh     # Ver estado del bot
./docker-restart.sh    # Reiniciar el bot
./docker-update.sh     # Actualizar el bot
./docker-stop.sh       # Detener el bot
```

### Comandos Docker Compose manuales

```bash
# Con imagen de Docker Hub (producción)
docker-compose -f docker-compose.production.yml up -d
docker-compose -f docker-compose.production.yml logs -f
docker-compose -f docker-compose.production.yml down

# Con build local (desarrollo)
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

**Musicalo** - Descubre nueva música con el poder de la IA y la simplicidad de Telegram 🎵🤖
