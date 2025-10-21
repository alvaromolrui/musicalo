# Musicalo 🎵🤖

[![Version](https://img.shields.io/badge/Version-4.2.0--alpha-orange.svg)](VERSION)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-alvaromolrui%2Fmusicalo-blue?logo=docker)](https://hub.docker.com/r/alvaromolrui/musicalo)
[![GitHub](https://img.shields.io/badge/GitHub-alvaromolrui%2Fmusicalo-black?logo=github)](https://github.com/alvaromolrui/musicalo)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://telegram.org)

Un bot de Telegram inteligente que utiliza IA para generar recomendaciones musicales personalizadas basadas en tu biblioteca de Navidrome y tus scrobbles de ListenBrainz.

## ✨ Características

- **🤖 Lenguaje Natural**: Habla directamente con el bot sin necesidad de comandos
- **🎨 Peticiones Específicas**: Describe exactamente lo que buscas con todos los detalles
- **🧠 Contexto Adaptativo en 3 Niveles** ⭐ **NUEVO**: El bot SIEMPRE conoce tus gustos y se adapta automáticamente
- **🎯 5 Reglas Críticas de Recomendación** ⭐ **NUEVO**: Álbumes, similitud, idioma, novedad, anti-duplicados
- **🔍 Búsqueda Profunda** ⭐ **NUEVO**: Control total con "dame todo" (50/200/1000 resultados)
- **❌ Filtro Anti-Duplicados** ⭐ **NUEVO**: NUNCA recomienda música que ya tienes
- **🎯 IA Contextual**: Gemini AI entiende intenciones y responde con tus datos reales
- **🎵 Integración con Navidrome**: Acceso completo a tu biblioteca musical autoalojada
- **📊 Scrobbles de ListenBrainz**: Análisis de tus hábitos de escucha y patrones (open-source, sin límites)
- **🎶 MusicBrainz**: Metadatos detallados y descubrimiento basado en relaciones entre artistas
- **⚡ Respuestas Ultrarrápidas**: Caché inteligente - 92% más rápido en consultas repetidas
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

### 🧠 Sistema de Contexto Adaptativo en 3 Niveles

**¡Nueva característica v4.2.0!** El bot ahora **SIEMPRE** conoce tus gustos musicales, adaptándose inteligentemente según lo que preguntes:

#### **Nivel 1: Contexto Mínimo** ⚡⚡⚡ (SIEMPRE activo)
- Se ejecuta en **todas las consultas** sin excepción
- Escuchas: **Top 5 artistas del MES** + últimas 3 escuchas
- Biblioteca: **20 artistas + 10 álbumes + top 5 géneros**
- **Caché de 1 hora** para máxima velocidad
- Respuestas en **~50ms** (instantáneo)

#### **Nivel 2: Contexto Enriquecido** ⚡⚡ (Recomendaciones)
- Se activa automáticamente cuando pides recomendaciones
- Escuchas: **Top 10 artistas del AÑO** + últimas 10 escuchas + top álbumes
- Biblioteca: **300 artistas + 150 álbumes + todos los géneros** (datos completos para filtrado preciso)
- **Caché de 15 minutos** (se actualiza dinámicamente)
- Primera consulta: ~800ms, repetidas: ~50ms

#### **Nivel 3: Contexto Completo** ⚡ (Estadísticas)
- Se activa cuando preguntas por tu perfil o estadísticas
- Escuchas: **Top 20 artistas de TODO EL TIEMPO** + últimas 30 + estadísticas completas
- Biblioteca: **Análisis completo** (500 artistas, 200 álbumes, géneros, décadas)
- **Caché de 10 minutos** (información histórica estable)
- Primera consulta: ~1200ms, repetidas: ~50ms

**Resultado:** El bot te conoce desde el primer mensaje y responde **92% más rápido** en consultas repetidas.

```
Ejemplo de conversación:
Tú: "Hola"
Bot: "¡Hola! Este mes escuchas mucho Extremoduro, Los Suaves y Barricada 🎸
      Tienes 150 álbumes de rock en tu biblioteca."
     [Nivel 1: Estadísticas mensuales + resumen biblioteca]

Tú: "Recomiéndame algo"
Bot: "Este año Extremoduro es tu artista #1 con 234 escuchas.
      De tus 50 álbumes de rock español, te recomiendo..."
     [Nivel 2: Estadísticas anuales + biblioteca completa]

Tú: "¿Cuál es mi artista más escuchado de todos los tiempos?"
Bot: "En todo el tiempo has escuchado 10,523 canciones.
      Extremoduro es #1 con 1,247 escuchas (12% del total).
      Tu biblioteca tiene 2,350 canciones de 156 artistas..."
     [Nivel 3: Estadísticas all-time + análisis completo biblioteca]
```

**Todos los comandos aprovechan el contexto:** `/recommend`, `/stats`, `/playlist`, `/library`, `/releases`, `/search`, `/nowplaying`

### 🔍 Búsqueda Profunda Controlada

**¡Nueva característica v4.2.0!** Controla cuántos resultados quieres ver cuando preguntas por tu biblioteca:

| Tipo de Búsqueda | Límite | Cuándo Usar |
|------------------|--------|-------------|
| **Primera búsqueda** | 50 resultados | Exploración inicial rápida |
| **"busca más"** | 200 resultados | Necesitas más detalles |
| **"dame todo"** | 1000 resultados | Inmersión completa en biblioteca |

**Ejemplo de uso:**
```
Tú: "¿Qué tengo de rock?"
🤖: [Muestra 50 álbumes]
    💡 Mostrando primeros 50 resultados.
    Para ver TODO, di "dame todo"

Tú: "dame todo"
🤖: [Muestra TODOS los álbumes de rock]
    ✅ INMERSIÓN COMPLETA - 1000 resultados
```

**Palabras mágicas:**
- `"dame todo"` / `"muéstrame todo"` → Ver toda la biblioteca
- `"busca más"` → Ver más resultados (200)
- `"búsqueda completa"` / `"inmersión completa"` → Sin límites

### 🎯 Reglas Críticas de Recomendación

El bot sigue **5 reglas estrictas** para recomendaciones de alta calidad:

1. **📀 FORMATO ÁLBUM POR DEFECTO**
   - Siempre recomienda álbumes completos (no canciones sueltas)
   - Excepción: si pides explícitamente "canciones"

2. **🎵 ALTO GRADO DE SIMILITUD**
   - Solo artistas/álbumes MUY similares a tus gustos
   - No mezcla géneros incompatibles (rock ≠ jazz)

3. **🌍 AFINIDAD DE IDIOMA**
   - Si escuchas español → recomienda español
   - Si escuchas inglés → recomienda inglés
   - Mantiene coherencia lingüística automáticamente

4. **🆕 PRIORIDAD A LO NUEVO**
   - Álbumes recientes (últimos 5 años)
   - Artistas que aún NO conoces
   - Descubrimiento continuo

5. **❌ NUNCA RECOMIENDA LO QUE YA TIENES**
   - Verifica tu biblioteca ANTES de recomendar
   - Filtra artistas y álbumes duplicados
   - Solo música nueva para ti

**Resultado:** Recomendaciones precisas, relevantes y SIEMPRE nuevas.

## 🏗️ Arquitectura

### Bot de Telegram
- **💬 Lenguaje Natural**: Escribe directamente sin comandos (ej: "recomiéndame un disco de Pink Floyd")
- **🎯 Comandos tradicionales**: `/recommend`, `/library`, `/stats`, `/search` (también funcionan)
- **🔘 Botones interactivos**: Me gusta, no me gusta, más recomendaciones
- **📊 Respuestas contextuales**: La IA usa tus datos reales de escucha
- **🎵 Recomendaciones variadas**: Diferentes sugerencias cada vez
- **🔄 Modo Polling**: Conexión simple y directa con Telegram

### Backend (Python + Telegram Bot API)
- **Servicios integrados**: 
  - `NavidromeService`: Conexión con tu servidor Navidrome
  - `ListenBrainzService`: Datos de escucha y recomendaciones colaborativas (open source, sin límites)
  - `MusicBrainzService`: Metadatos detallados, relaciones entre artistas y búsqueda inversa por género/país/época
  - `MusicRecommendationService`: IA con Google Gemini para recomendaciones personalizadas
  - `TelegramService`: Manejo de interacciones del bot en modo polling

**Stack completamente open-source:**
- ✅ **ListenBrainz** para datos de escucha y recomendaciones basadas en usuarios similares
- ✅ **MusicBrainz** para metadatos precisos, descubrimiento por relaciones entre artistas y búsquedas avanzadas
- ✅ Ambos servicios son gratuitos, open-source y sin límites estrictos de API
- ✅ Cache persistente para minimizar llamadas a las APIs
- ✅ **Búsqueda profunda controlada** con "dame todo" (50 → 200 → 1000 resultados)
- ✅ **Filtro anti-duplicados** en recomendaciones (NUNCA recomienda lo que ya tienes)

## 🚀 Instalación

### Prerrequisitos
- **Docker y Docker Compose** instalados en tu sistema
- Servidor **Navidrome** funcionando
- Cuenta de **ListenBrainz** (open-source, gratuita)
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

**Variables principales:**
- `NAVIDROME_URL`: URL de tu servidor Navidrome
- `NAVIDROME_USERNAME` y `NAVIDROME_PASSWORD`: Credenciales de Navidrome
- `LISTENBRAINZ_USERNAME` y `LISTENBRAINZ_TOKEN`: Para datos de escucha (REQUERIDO)
- `ENABLE_MUSICBRAINZ`: Habilitar metadatos y descubrimiento avanzado (RECOMENDADO)
- `GEMINI_API_KEY`: API key de Google Gemini (REQUERIDO)
- `TELEGRAM_BOT_TOKEN`: Token de tu bot de Telegram (REQUERIDO)
- `TELEGRAM_ALLOWED_USER_IDS`: IDs permitidos para bot privado (RECOMENDADO)

**Stack completamente open-source:** ListenBrainz + MusicBrainz + Navidrome = Sin dependencias de servicios comerciales.

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
2. Regístrate con tu cuenta de MusicBrainz (o crea una nueva)
3. Opcional: Obtén un token de API en Settings → User Token
4. Conecta tu scrobbler favorito (Maloja, Navidrome, Plex, etc.)

**¿Por qué usar ListenBrainz?**
- ✅ Totalmente open-source y gratuito
- ✅ Sin límites de API
- ✅ Recomendaciones colaborativas basadas en usuarios similares
- ✅ Compatible con múltiples plataformas de scrobbling
- ✅ Privacidad y control total de tus datos

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
"¿qué tengo de jazz?" → "dame todo" (búsqueda profunda)
"recomiéndame álbumes nuevos" (solo discos recientes que NO tienes)
```

La IA entiende tu intención y responde usando tus datos reales de ListenBrainz y MusicBrainz.

### 🗣️ Comandos con Lenguaje Natural

Casi todos los comandos pueden usarse con lenguaje natural sin necesidad de recordar la sintaxis exacta:

| Comando | Ejemplos de Lenguaje Natural |
|---------|------------------------------|
| `/recommend` | "Recomiéndame rock progresivo"<br>"Similar a Pink Floyd"<br>"Álbumes nuevos de artistas que NO conozco" |
| `/playlist` | "Haz playlist de Pink Floyd y Queen"<br>"Crea playlist de jazz suave" |
| `/search` | "Busca Queen en mi biblioteca"<br>"¿Qué tengo de jazz?" → "dame todo" (búsqueda profunda) |
| `/library` | "Muéstrame mi biblioteca"<br>"Todo lo que tengo de rock" (inmersión completa) |
| `/stats` | "Mis estadísticas de este mes"<br>"Qué he escuchado esta semana" |
| `/releases` | "Qué hay nuevo de mis artistas"<br>"Lanzamientos recientes" |
| `/nowplaying` | "Qué estoy escuchando ahora"<br>"Qué está sonando" |

**⚠️ Excepciones:** Solo `/start`, `/help` y `/share` requieren usar el comando explícitamente.

### 🎯 Comandos Tradicionales (también funcionan)

- **`/recommend`** - Recomendaciones musicales • Ej: /recommend rock
- **`/playlist`** - Crear playlist M3U • Ej: /playlist jazz suave
- **`/nowplaying`** - Ver qué se está reproduciendo ahora • Muestra todos los reproductores activos
- **`/library`** - Explorar biblioteca
- **`/stats`** - Estadísticas en Listenbrainz • Ej: /stats week
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
stats - Estadísticas en Listenbrainz • Ej: /stats week
search - Buscar música en la biblioteca • Ej: /search queen
releases - Consultar nuevos lanzamientos de artistas de la biblioteca • Ej: /releases week
share - Crear enlace para compartir música • Ej: /share The dark side of the moon
start - Iniciar el bot
help - Mostrar ayuda completa
```

### Ejemplos con Comandos

```
/recommend                    # Recomendaciones generales (5 álbumes nuevos que NO tienes)
/recommend rock               # Álbumes de rock (alta similitud, mismo idioma)
/search jazz                  # Buscar jazz (primeros 50 resultados)
  → "dame todo"               # Ver TODOS los álbumes de jazz (1000 resultados)
/library                      # Ver biblioteca
/stats                        # Ver estadísticas
/playlist rock 70s            # Playlist DE TU BIBLIOTECA
```

**💡 Nuevas capacidades:**
- `/recommend` ahora **NUNCA** repite artistas que ya tienes
- `/search` soporta "dame todo" para búsqueda completa
- `/playlist` siempre usa música de tu biblioteca

### 🔘 Interacciones

- **Botones inline**: ❤️ Me gusta, 👎 No me gusta, 🔄 Más recomendaciones
- **Teclado personalizado**: Botones rápidos para comandos comunes
- **Respuestas conversacionales**: La IA responde de forma natural

## 🤖 Comandos del Bot

> 🧠 **Todos los comandos de música** ahora usan el **sistema de contexto adaptativo** - el bot siempre conoce tus gustos y responde de forma personalizada.

### Comandos Básicos
- **`/start`** - Iniciar bot y mostrar bienvenida
- **`/help`** - Ayuda detallada con ejemplos

### Comandos de Música (🧠 con contexto adaptativo)
- **`/recommend [descripción]`** - Recomendaciones IA con reglas mejoradas (Nivel 2)
  - ⭐ **MEJORADO**: Ahora 100% IA - respeta todas las reglas críticas
  - 📀 Formato álbum por defecto, alta similitud, afinidad de idioma
  - ❌ NUNCA recomienda música que ya tienes en biblioteca
  - Ejemplos: `/recommend`, `/recommend rock`, `/recommend canciones` (excepción)
- **`/stats [periodo]`** - Análisis inteligente de tus estadísticas (Nivel 3)
- **`/playlist <descripción>`** - Crear playlist personalizada (Nivel 2)
  - 🎵 Siempre usa canciones de TU biblioteca
- **`/library`** - Resumen inteligente de tu biblioteca (Nivel 3)
- **`/releases [periodo]`** - Lanzamientos filtrados por tus gustos (Nivel 2)
- **`/search <término>`** - Buscar con sugerencias contextuales (Nivel 1)
  - 🔍 Soporta "dame todo" para búsqueda completa
- **`/nowplaying`** - Ver reproducción actual con contexto (Nivel 1)
- **`/share <nombre>`** - Compartir música con enlace público

### Interacciones
- **Botones de reacción**: ❤️ Me gusta, 👎 No me gusta
- **Navegación**: 🔄 Más recomendaciones, 📚 Ver biblioteca
- **Acciones**: 🎵 Reproducir en Navidrome

## 🧠 Algoritmo de Recomendaciones

El sistema utiliza múltiples enfoques con **contexto adaptativo** y **reglas críticas**:

1. **Contexto en 3 Niveles** ⭐ **NUEVO**: Sistema inteligente con periodos progresivos
   - Nivel 1 (Mínimo): Stats **MENSUALES** + resumen biblioteca - caché 1h
   - Nivel 2 (Enriquecido): Stats **ANUALES** + biblioteca completa (300 artistas, 150 álbumes) - caché 15min
   - Nivel 3 (Completo): Stats **TODO EL TIEMPO** + análisis detallado - caché 10min

2. **5 Reglas Críticas** ⭐ **NUEVO**: Garantizan recomendaciones de alta calidad
   - 📀 Formato álbum por defecto
   - 🎵 Alta similitud musical
   - 🌍 Afinidad de idioma
   - 🆕 Prioridad a lo nuevo
   - ❌ Filtro anti-duplicados

3. **Análisis de perfil**: Patrones de escucha, géneros favoritos, diversidad

4. **IA generativa**: Google Gemini para sugerencias contextuales

5. **Similitud musical**: Artistas y géneros relacionados

6. **Filtrado colaborativo**: Basado en usuarios con gustos similares (ListenBrainz)

**Resultado:** Recomendaciones precisas, relevantes y siempre nuevas que respetan tu perfil musical.

## 🎨 Tecnologías

### Backend
- **python-telegram-bot 20.7**: Framework moderno para bots
- **Google Gemini**: IA para recomendaciones contextuales
- **httpx**: Cliente HTTP asíncrono para APIs
- **Pydantic**: Validación de datos

### Bot
- **Modo Polling**: Conexión persistente con Telegram
- **Inline Keyboards**: Botones interactivos
- **Reply Keyboards**: Teclados personalizados
- **Callback Handlers**: Manejo de interacciones
- **Async/Await**: Operaciones asíncronas para mejor rendimiento

## 📊 Características de la IA

- **🧠 Contexto Adaptativo** ⭐ **NUEVO**: Sistema de 3 niveles que siempre conoce tus gustos
  - Respuestas **92% más rápidas** en consultas repetidas
  - Caché inteligente (1h/15min/10min según el tipo de dato)
  - Se actualiza automáticamente con tus nuevas escuchas
- **🎯 Recomendaciones de Alta Calidad** ⭐ **NUEVO**: 5 reglas críticas
  - ✅ **Formato álbum** por defecto (no canciones sueltas)
  - ✅ **Alta similitud** (no mezcla géneros incompatibles)
  - ✅ **Afinidad de idioma** (español → español, inglés → inglés)
  - ✅ **Prioridad a lo nuevo** (álbumes recientes, artistas desconocidos)
  - ✅ **Filtro anti-duplicados** (NUNCA recomienda lo que ya tienes)
- **🔍 Búsqueda Profunda** ⭐ **NUEVO**: Control total con "dame todo"
  - Primera búsqueda: 50 resultados (rápida)
  - "busca más": 200 resultados (ampliada)
  - "dame todo": 1000 resultados (completa)
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
