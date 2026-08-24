# Musicalo 🎵🤖

[![Version](https://img.shields.io/badge/Version-4.2.1-blue.svg)](VERSION)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-alvaromolrui%2Fmusicalo-blue?logo=docker)](https://hub.docker.com/r/alvaromolrui/musicalo)
[![Frontend](https://img.shields.io/badge/Docker%20Hub-alvaromolrui%2Fmusicalo--frontend-blue?logo=docker)](https://hub.docker.com/r/alvaromolrui/musicalo-frontend)
[![GitHub](https://img.shields.io/badge/GitHub-alvaromolrui%2Fmusicalo-black?logo=github)](https://github.com/alvaromolrui/musicalo)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://telegram.org)
[![Chainlit](https://img.shields.io/badge/Web%20UI-Chainlit-orange)](https://chainlit.io)

Asistente musical con IA que combina un bot de Telegram y una interfaz web (Chainlit). Genera recomendaciones personalizadas basadas en tu biblioteca de Navidrome y tus escuchas de Koito o ListenBrainz.

## ✨ Características

- **🤖 Lenguaje Natural**: Habla directamente con el bot sin necesidad de comandos
- **🎨 Peticiones Específicas**: Describe exactamente lo que buscas con todos los detalles
- **🛠️ Agente con herramientas**: un único agente conversacional (Gemini con function calling) decide qué consultar - biblioteca, historial, similares, lanzamientos - y redacta la respuesta con su propia voz, sin plantillas fijas ni clasificador previo
- **🎯 IA Contextual**: Gemini AI entiende intenciones y responde con tus datos reales
- **🎵 Integración con Navidrome**: Acceso completo a tu biblioteca musical autoalojada
- **📊 Historial de escucha (Koito o ListenBrainz)**: Análisis de tus hábitos y patrones, open-source y sin límites. Koito tiene prioridad si lo configuras (`KOITO_URL`); si no, se usa ListenBrainz
- **🎶 MusicBrainz**: Metadatos detallados y descubrimiento basado en relaciones entre artistas
- **🎤 Playlists desde conciertos reales**: pide un setlist de setlist.fm por artista/ciudad o pega el enlace, y te la arma emparejando canciones contra tu biblioteca
- **🔔 Aviso de lanzamientos nuevos**: comprueba periódicamente si hay álbumes/EPs/singles nuevos de artistas de tu biblioteca y te avisa por [ntfy](https://ntfy.sh) y/o Telegram (opcional, manda por los canales que tengas configurados)
- **🔄 Variedad**: Diferentes recomendaciones cada vez
- **🎧 Now Playing**: Consulta qué se está reproduciendo actualmente en todos tus reproductores
- **📱 Acceso móvil**: Optimizado para usar desde tu smartphone
- **🔒 Bot Privado**: Restringe el acceso solo a usuarios autorizados
- **🎵 Playlists M3U**: Generación automática de playlists compatibles con Navidrome

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

### 🤖 Un agente con herramientas, no un árbol de decisiones

Musicalo no clasifica tu mensaje en categorías fijas para decidir qué hacer. Cada mensaje lo recibe un único agente conversacional (Gemini con *function calling*) que decide por sí mismo qué necesita consultar, llama directamente a las herramientas que le hacen falta - encadenando varias si hace falta - y redacta la respuesta final con su propia voz. No hay plantillas de texto ni un clasificador de intenciones decidiendo por él antes de que responda.

**Herramientas disponibles para el agente:**

| Herramienta | Para qué |
|---|---|
| `buscar_biblioteca` | Buscar canciones/álbumes/artistas por texto libre en Navidrome |
| `filtrar_biblioteca` | Explorar la biblioteca por género y/o año |
| `top_artistas` / `top_tracks` / `top_albumes` | Lo más escuchado en un periodo (Koito o ListenBrainz) |
| `escuchas_recientes` | Últimas canciones escuchadas, en orden cronológico |
| `artistas_similares` | Descubrimiento de música nueva (historial + MusicBrainz + IA como último recurso) |
| `lanzamientos_artista` | Últimos álbumes/EPs de un artista (MusicBrainz) |
| `now_playing` | Qué se está reproduciendo ahora en Navidrome |
| `crear_playlist` | Crea la playlist real en Navidrome con las canciones que el propio agente eligió |
| `buscar_setlist_concierto` / `crear_playlist_desde_setlist` | Playlist a partir de un concierto real, buscando por artista/ciudad/fecha o a partir de un enlace de setlist.fm |

Las herramientas de historial y setlist.fm solo se activan si tienes esos servicios configurados (Koito/ListenBrainz, `SETLISTFM_API_KEY`).

**Memoria real de la conversación:** el historial se le pasa al modelo como turnos nativos, no como un resumen de texto reinyectado en cada mensaje - así que "quita esa canción", "más de eso" o "cámbiame la última" funcionan de forma natural, sin depender de frases mágicas predefinidas.

```
Ejemplo de conversación:
Tú: "recomiéndame un disco de algún grupo similar a Extremoduro"
Bot: [llama a artistas_similares y filtrar_biblioteca, y responde con 2-3 discos
      concretos y por qué, mezclando biblioteca y descubrimiento]

Tú: "hazme una playlist con eso"
Bot: [busca las canciones y llama a crear_playlist - la playlist aparece de
      verdad en tu Navidrome]

Tú: "quita la última y pon algo más movido"
Bot: [vuelve a buscar y llama a crear_playlist otra vez con la lista ajustada]
```

## 🖥️ Modos de uso (`START_MODE`)

El backend puede arrancar en tres modos:

| Modo | Descripción | Requiere |
|------|-------------|----------|
| `telegram` | Solo bot de Telegram (por defecto) | `TELEGRAM_BOT_TOKEN` |
| `api` | Solo API REST — para conectar el frontend web u otra UI | — |
| `both` | Telegram + API REST simultáneamente | `TELEGRAM_BOT_TOKEN` |

### 🌐 Frontend web (Chainlit)

Cuando `START_MODE=api` o `both`, puedes desplegar también el frontend web:

- Chat en el navegador accesible en `http://localhost:8080`
- Historial de conversaciones persistente (SQLite)
- Mismas capacidades que el bot de Telegram
- Imagen Docker: `alvaromolrui/musicalo-frontend:main`

```yaml
# Fragmento docker-compose.yml
frontend:
  image: alvaromolrui/musicalo-frontend:main
  ports:
    - "8080:8080"
  environment:
    - BACKEND_URL=http://musicalo:8000
    - MUSICALO_API_KEY=${MUSICALO_API_KEY}
    - CHAINLIT_AUTH_SECRET=${CHAINLIT_AUTH_SECRET}   # openssl rand -hex 32
    - CHAINLIT_DEFAULT_USER=${CHAINLIT_DEFAULT_USER:-musicalo}
  volumes:
    - chainlit_data:/app/data   # historial SQLite persistente
```

> Ver `docker-compose.yml.example` para la configuración completa.

## 🏗️ Arquitectura

### Bot de Telegram
- **💬 Lenguaje Natural**: Escribe directamente sin comandos (ej: "recomiéndame un disco de Pink Floyd")
- **🎯 Comandos tradicionales**: `/recommend`, `/library`, `/stats`, `/search` (también funcionan)
- **🔘 Botones interactivos**: Me gusta, no me gusta, más recomendaciones
- **📊 Respuestas contextuales**: La IA usa tus datos reales de escucha
- **🎵 Recomendaciones variadas**: Diferentes sugerencias cada vez
- **🔄 Modo Polling**: Conexión simple y directa con Telegram

### Backend (FastAPI + Telegram Bot API)
- **API REST** en `POST /chat/` — consume el frontend web y cualquier cliente externo
- **Servicios integrados**:
  - `MusicAgentService`: el agente conversacional - bucle de *function calling* sobre Gemini (SDK `google-genai`) con las herramientas descritas más arriba. Es el motor detrás de la conversación en lenguaje natural y de la mayoría de comandos
  - `NavidromeService`: Conexión con tu servidor Navidrome
  - `KoitoService` / `ListenBrainzService`: Datos de escucha (Koito auto-hospedado tiene prioridad si está configurado; si no, ListenBrainz)
  - `MusicBrainzService`: Metadatos detallados, relaciones entre artistas, lanzamientos y búsqueda inversa por género/país/época
  - `SetlistfmService`: Playlists a partir de conciertos reales (setlist.fm)
  - `MusicRecommendationService`: motor de recomendaciones "avanzado" (perfil, filtrado híbrido) usado por comandos específicos como `/hybrid` y `/discover`
  - `ReleaseWatcher` + `NotificationService`: tarea de fondo que comprueba lanzamientos nuevos de tu biblioteca y avisa por ntfy - independiente de `START_MODE`, arranca tanto en modo `api` como `telegram`/`both`
  - `TelegramService`: Manejo de interacciones del bot en modo polling

### Frontend web (Chainlit)
- Interfaz de chat en el navegador
- Historial persistente en SQLite (volumen Docker `chainlit_data`)
- Autenticación sin formulario vía `@cl.header_auth_callback`; compatible con reverse proxy (Traefik + Authelia) para multiusuario

**Stack completamente open-source:**
- ✅ **Koito** (auto-hospedado) o **ListenBrainz** para datos de escucha - Koito además te da control total de tus datos al vivir en tu propia infraestructura
- ✅ **MusicBrainz** para metadatos precisos, descubrimiento por relaciones entre artistas y búsquedas avanzadas
- ✅ Ambos servicios son gratuitos, open-source y sin límites estrictos de API
- ✅ Cache persistente para minimizar llamadas a las APIs
- ✅ Sistema de búsqueda incremental con "busca más" para explorar toda tu biblioteca

## 🚀 Instalación

### Prerrequisitos
- **Docker y Docker Compose** instalados en tu sistema
- Servidor **Navidrome** funcionando
- Instancia de **Koito** auto-hospedada, o cuenta de **ListenBrainz** (open-source, gratuita) - uno de los dos
- **API key de Google Gemini** (gratuita)
- **Token de bot de Telegram**

### 🐳 Instalación con Docker Hub

La forma más sencilla de instalar Musicalo es usando la imagen oficial pre-construida de Docker Hub:

```bash
# 1. Crear directorio para el proyecto
mkdir musicalo
cd musicalo

# 2. Descargar archivo de configuración de ejemplo
wget https://raw.githubusercontent.com/alvaromolrui/musicalo/main/env.example
mv env.example .env

# 3. Editar el archivo .env con tus credenciales
nano .env  # O usa tu editor favorito

# 4. Descargar docker-compose.yml
wget https://raw.githubusercontent.com/alvaromolrui/musicalo/main/docker-compose.yml

# 5. Iniciar el bot (descargará automáticamente la imagen de Docker Hub)
docker-compose up -d
```

**La imagen se descargará automáticamente de Docker Hub** ([alvaromolrui/musicalo](https://hub.docker.com/r/alvaromolrui/musicalo)) en tu primer inicio.

**Comandos útiles:**
```bash
docker-compose logs -f      # Ver logs en tiempo real
docker-compose restart      # Reiniciar el bot
docker-compose down         # Detener el bot
docker-compose pull         # Actualizar a la última versión
docker-compose up -d        # Aplicar actualización
```

## ⚙️ Configuración

Copia el archivo `env.example` a `.env` y configura tus credenciales:

```bash
cp env.example .env
nano .env
```

El archivo `.env` está completamente documentado con comentarios explicativos para cada variable.

**Variables principales del backend:**
- `START_MODE`: `telegram` (default) / `api` / `both`
- `NAVIDROME_URL`, `NAVIDROME_USERNAME`, `NAVIDROME_PASSWORD`: Credenciales de Navidrome
- `KOITO_URL`, `KOITO_API_KEY`: Para datos de escucha vía Koito auto-hospedado (tiene prioridad si está seteado)
- `LISTENBRAINZ_USERNAME`, `LISTENBRAINZ_TOKEN`: Para datos de escucha vía ListenBrainz (REQUERIDO uno de los dos, Koito o ListenBrainz)
- `ENABLE_MUSICBRAINZ`: Habilitar metadatos y descubrimiento avanzado (RECOMENDADO)
- `SETLISTFM_API_KEY`: API key gratuita de setlist.fm (https://api.setlist.fm/) para crear playlists a partir de setlists de conciertos
- `NTFY_URL`, `NTFY_TOPIC`, `NTFY_TOKEN`: Aviso de lanzamientos nuevos por ntfy (OPCIONAL)
- `TELEGRAM_NOTIFY_CHAT_ID`: Aviso de lanzamientos nuevos por Telegram, reutilizando `TELEGRAM_BOT_TOKEN` (OPCIONAL - por defecto usa el primer ID de `TELEGRAM_ALLOWED_USER_IDS`)
- `RELEASES_CHECK_INTERVAL_HOURS`, `RELEASES_LOOKBACK_DAYS`: Frecuencia y ventana de la comprobación de lanzamientos (default 24h / 30 días)
- `GEMINI_API_KEY`: API key de Google Gemini (REQUERIDO)
- `TELEGRAM_BOT_TOKEN`: Token de tu bot de Telegram (solo si `START_MODE=telegram` o `both`)
- `TELEGRAM_ALLOWED_USER_IDS`: IDs permitidos para bot privado (RECOMENDADO)
- `MUSICALO_API_KEY`: Clave de acceso a la API REST (vacía = sin auth)

**Variables del frontend web** (solo si usas el servicio `frontend`):
- `CHAINLIT_AUTH_SECRET`: JWT secret requerido por Chainlit — genera con `openssl rand -hex 32`
- `CHAINLIT_DEFAULT_USER`: Usuario cuando no hay reverse proxy (default: `musicalo`)
- `CHAINLIT_DB_PATH`: Ruta al SQLite de historial (default: `/app/data/chainlit.db`)
- `BACKEND_URL`: URL del backend desde el contenedor frontend (default: `http://musicalo:8000`)

**Stack completamente open-source:** (Koito o ListenBrainz) + MusicBrainz + Navidrome = Sin dependencias de servicios comerciales.

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

#### Koito (recomendado si quieres auto-hospedar tus escuchas)
1. Despliega tu propia instancia de [Koito](https://koito.io/) (compatible con la API de scrobbling de ListenBrainz)
2. Apunta tu scrobbler favorito (Navidrome, Plex, etc.) al endpoint compatible con ListenBrainz de tu Koito, en vez de a listenbrainz.org
3. Genera una API key desde tu perfil de Koito (Settings → API Keys)
4. Configura `KOITO_URL` (la URL base de tu instancia) y `KOITO_API_KEY` en tu `.env`

**¿Por qué usar Koito?**
- ✅ Totalmente auto-hospedado: tus datos de escucha no salen de tu infraestructura
- ✅ Compatible con la API de ListenBrainz para scrobbling, así que cualquier cliente que ya sepa hablar con ListenBrainz funciona igual
- ✅ Import de historial desde ListenBrainz, Last.fm, Maloja y Spotify si vienes de otro servicio
- ⚠️ Al ser de un solo usuario no tiene recomendaciones colaborativas (no hay otros usuarios con los que comparar) - Musicalo usa MusicBrainz/IA como alternativa en ese caso

#### ListenBrainz (alternativa si no quieres auto-hospedar)
1. Ve a [ListenBrainz](https://listenbrainz.org/)
2. Regístrate con tu cuenta de MusicBrainz (o crea una nueva)
3. Opcional: Obtén un token de API en Settings → User Token
4. Conecta tu scrobbler favorito (Maloja, Navidrome, Plex, etc.)

**¿Por qué usar ListenBrainz?**
- ✅ Totalmente open-source y gratuito, sin nada que auto-hospedar
- ✅ Sin límites de API
- ✅ Recomendaciones colaborativas basadas en usuarios similares
- ✅ Compatible con múltiples plataformas de scrobbling

#### MusicBrainz (Recomendado)
MusicBrainz es completamente **gratuito y open source**. No requiere API key, solo información de contacto:

1. **No necesitas registrarte** para usar MusicBrainz
2. Configura en tu archivo `.env`:
   - `ENABLE_MUSICBRAINZ=true` (para habilitar)
   - `APP_NAME=MusicaloBot` (nombre de tu aplicación)
   - `CONTACT_EMAIL=tu_email@example.com` (requerido por las políticas de MusicBrainz)
3. Configuración opcional:
   - `MUSICBRAINZ_BATCH_SIZE=20` (artistas a verificar por búsqueda, 15-30 recomendado)
   - `MUSICBRAINZ_MAX_TOTAL=100` (límite máximo total de artistas)

**¿Por qué usar MusicBrainz?**
- ✅ Búsquedas ultra-específicas: "indie español de los 2000", "rock progresivo de los 70s"
- ✅ Metadatos precisos de género, país y época de cada artista
- ✅ Cache persistente (evita consultas repetidas)
- ✅ Búsqueda incremental con "busca más"
- ✅ Totalmente gratuito y sin límites estrictos

#### ntfy (opcional, para el aviso de lanzamientos nuevos)
1. Elige un nombre de topic único y difícil de adivinar (cualquiera que lo sepa puede suscribirse) - no hace falta crear cuenta
2. Instala la app de [ntfy](https://ntfy.sh/) (Android/iOS/web) y suscríbete a ese topic
3. Configura en tu `.env`:
   - `NTFY_TOPIC=tu-topic-elegido`
   - `NTFY_URL=https://ntfy.sh` (o la URL de tu propia instancia auto-hospedada)
   - `NTFY_TOKEN` solo si tu instancia requiere autenticación
4. Sin `NTFY_TOPIC` configurado, esta comprobación queda inactiva sin más - no es necesaria para el resto de la app

Alternativa/complemento: si ya tienes `TELEGRAM_BOT_TOKEN` configurado (aunque corras en `START_MODE=api` sin el bot interactivo), basta con eso - el aviso se manda directo por la Bot API al primer ID de `TELEGRAM_ALLOWED_USER_IDS`. Se puede tener ntfy y Telegram a la vez; se manda por los dos.

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
docker-compose restart
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

### 💬 Lenguaje Natural

¡Ahora puedes hablar directamente con el bot sin comandos!

**Ejemplos:**
```
"recomiéndame un disco de algún grupo similar a Pink Floyd"
"¿cuál fue mi última canción?"
"dame 3 artistas parecidos a Queen"
"¿qué he escuchado hoy de rock?"
"busca música de Queen en mi biblioteca"
"¿qué estoy escuchando?" (reproducción actual en tiempo real)
"¿qué es el jazz?" (preguntas generales sobre música)
```

La IA entiende tu intención y responde usando tus datos reales de Koito/ListenBrainz y MusicBrainz.

### 🗣️ Comandos con Lenguaje Natural

Casi todos los comandos pueden usarse con lenguaje natural sin necesidad de recordar la sintaxis exacta:

| Comando | Ejemplos de Lenguaje Natural |
|---------|------------------------------|
| `/recommend` | "Recomiéndame rock progresivo"<br>"Similar a Pink Floyd"<br>"De mi biblioteca que no escucho" |
| `/playlist` | "Haz playlist de Pink Floyd y Queen"<br>"Crea playlist de jazz suave" |
| `/search` | "Busca Queen en mi biblioteca"<br>"Buscar bohemian rhapsody" |
| `/library` | "Muéstrame mi biblioteca"<br>"Qué tengo en mi biblioteca" |
| `/stats` | "Mis estadísticas de este mes"<br>"Qué he escuchado esta semana" |
| `/releases` | "Qué hay nuevo de mis artistas"<br>"Lanzamientos recientes" |
| `/nowplaying` | "Qué estoy escuchando ahora"<br>"Qué está sonando" |

**⚠️ Excepciones:** Solo `/start`, `/help` y `/share` requieren usar el comando explícitamente.

### 🎯 Comandos Tradicionales (también funcionan)

- **`/recommend`** - Recomendaciones musicales • Ej: /recommend rock
- **`/playlist`** - Crear playlist M3U • Ej: /playlist jazz suave
- **`/nowplaying`** - Ver qué se está reproduciendo ahora • Muestra todos los reproductores activos
- **`/library`** - Explorar biblioteca
- **`/stats`** - Estadísticas de escucha • Ej: /stats week
- **`/search`** - Buscar música en la biblioteca • Ej: /search queen
- **`/releases`** - Consultar nuevos lanzamientos de artistas de la biblioteca • Ej: /releases week
- **`/share`** - Crear enlace para compartir música • Ej: /share The dark side of the moon
- **`/start`** - Iniciar el bot
- **`/help`** - Mostrar ayuda completa

### Lista de comandos

```
recommend - Recomendaciones musicales • Ej: /recommend rock
playlist - Crear playlist M3U • Ej: /playlist jazz suave
nowplaying - Ver qué se está reproduciendo ahora • Muestra todos los reproductores activos
library - Explorar biblioteca
stats - Estadísticas de escucha • Ej: /stats week
search - Buscar música en la biblioteca • Ej: /search queen
releases - Consultar nuevos lanzamientos de artistas de la biblioteca • Ej: /releases week
share - Crear enlace para compartir música • Ej: /share The dark side of the moon
start - Iniciar el bot
help - Mostrar ayuda completa
```

### Ejemplos con Comandos

```
/recommend                    # Recomendaciones generales
/recommend album rock         # Álbumes de rock
/recommend similar Queen      # Música similar a Queen
/library                      # Ver biblioteca
/stats                        # Ver estadísticas
/search queen                 # Buscar Queen
```

### 🔘 Interacciones

- **Botones inline**: ❤️ Me gusta, 👎 No me gusta, 🔄 Más recomendaciones
- **Teclado personalizado**: Botones rápidos para comandos comunes
- **Respuestas conversacionales**: La IA responde de forma natural

## 🤖 Comandos del Bot

> 🛠️ **La mayoría de comandos de música** pasan por el mismo agente con herramientas descrito arriba - el bot decide qué consultar y responde con datos reales, no con una plantilla fija por comando.

### Comandos Básicos
- **`/start`** - Iniciar bot y mostrar bienvenida
- **`/help`** - Ayuda detallada con ejemplos

### Comandos de Música
- **`/recommend`** - Recomendaciones personalizadas con IA
- **`/stats [periodo]`** - Análisis de tus estadísticas de escucha
- **`/playlist <descripción>`** - Crear playlist personalizada (el agente elige las canciones y la crea de verdad en Navidrome)
- **`/library`** - Resumen de tu biblioteca
- **`/releases [periodo]`** - Lanzamientos recientes de tus artistas
- **`/search <término>`** - Buscar en tu biblioteca
- **`/nowplaying`** - Ver reproducción actual
- **`/share <nombre>`** - Compartir música con enlace público

### Interacciones
- **Botones de reacción**: ❤️ Me gusta, 👎 No me gusta
- **Navegación**: 🔄 Más recomendaciones, 📚 Ver biblioteca
- **Acciones**: 🎵 Reproducir en Navidrome

## 🧠 Algoritmo de Recomendaciones

El sistema combina varios enfoques:

1. **Consultas dirigidas por el propio agente**: en vez de precalcular un "contexto" fijo en cada mensaje, el agente pide justo lo que necesita en cada caso (top artistas, escuchas recientes, filtrado por género...) llamando a sus herramientas
2. **Análisis de perfil**: Patrones de escucha, géneros favoritos, diversidad
3. **IA generativa**: Google Gemini para sugerencias contextuales
4. **Similitud musical**: Artistas y géneros relacionados (historial + MusicBrainz)
5. **Filtrado colaborativo**: Basado en usuarios con gustos similares (solo disponible con ListenBrainz - Koito, al ser de un solo usuario, no tiene otros usuarios con quien comparar, así que usa MusicBrainz/IA en su lugar)

## 🎨 Tecnologías

### Backend
- **FastAPI**: API REST + python-telegram-bot 20.7
- **Google Gemini** (SDK `google-genai`): function calling para el agente conversacional
- **httpx**: Cliente HTTP asíncrono para APIs
- **Pydantic**: Validación de datos

### Bot
- **Modo Polling**: Conexión persistente con Telegram
- **Inline Keyboards**: Botones interactivos
- **Reply Keyboards**: Teclados personalizados
- **Callback Handlers**: Manejo de interacciones
- **Async/Await**: Operaciones asíncronas para mejor rendimiento

### Frontend web
- **Chainlit 2.11.1**: Framework de chat web
- **SQLAlchemy + aiosqlite**: Historial persistente en SQLite
- **httpx**: Comunicación con la API REST del backend

## 📊 Características de la IA

- **🛠️ Agente con herramientas**: consulta biblioteca/historial/similares bajo demanda en vez de precalcular un contexto fijo, y encadena varias herramientas si una consulta lo requiere
- **💬 Memoria de conversación real**: recuerda lo hablado en el mismo turno de Gemini, no como texto resumido reinyectado
- **Análisis de género**: Identificación automática de preferencias
- **Patrones temporales**: Horarios de escucha preferidos
- **Diversidad musical**: Medición de amplitud de gustos
- **Descubrimiento**: Sugerencias para expandir horizontes
- **Explicabilidad**: Razones claras para cada recomendación
- **Búsqueda inversa con MusicBrainz**: Identifica artistas de tu biblioteca que cumplen criterios específicos (género, país, época)

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [Navidrome](https://github.com/navidrome/navidrome) por el excelente servidor de música
- [Koito](https://koito.io/) por el scrobbler auto-hospedado y compatible con ListenBrainz
- [ListenBrainz](https://listenbrainz.org/) por la API de scrobbling open source
- [MusicBrainz](https://musicbrainz.org/) por la base de datos de metadatos musicales open source
- [Google Gemini](https://ai.google.dev/) por las capacidades de IA
- La comunidad de desarrolladores de música open source

## 🐳 Gestión con Docker

### Comandos Docker Compose

```bash
# Iniciar bot
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Detener bot
docker-compose down

# Actualizar a última versión
docker-compose pull
docker-compose up -d

# Reiniciar bot
docker-compose restart
```

---

**Musicalo** - Descubre nueva música con el poder de la IA y la simplicidad de Telegram 🎵🤖
