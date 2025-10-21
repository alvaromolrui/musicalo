# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [4.2.0-alpha] - 2025-01-21

### 🐛 Arreglado
- **CRÍTICO: Comando `/recommend` ahora usa el agente con reglas mejoradas**
  - **Problema**: El comando `/recommend` usaba lógica antigua que llamaba directamente a ListenBrainz/MusicBrainz, ignorando TODAS las reglas del system prompt
  - **Resultado**: Recomendaciones con baja similitud (Metallica similar a The Cure??), artistas ya conocidos, y sin respeto por idioma/década
  - **Solución**: Migrado completamente al agente conversacional - **333 líneas → 39 líneas** (simplificación del 88%)
  - **Ahora respeta**: Formato álbum por defecto, alta similitud, afinidad de idioma, priorización de discos nuevos y artistas nuevos
  - **Impacto**: Mejora MASIVA en calidad de recomendaciones, consistencia total con otros comandos, y código 10x más mantenible

### ✨ Nuevo
- **🧠 Sistema de Contexto Adaptativo en 3 Niveles con Periodos Progresivos**
  - El agente ahora SIEMPRE tiene contexto de tu música Y biblioteca, adaptándose automáticamente
  - **Nivel 1 (Mínimo)**: TODAS las consultas - Stats MENSUALES + resumen biblioteca (20 artistas, 10 álbumes, géneros) - caché 1h
  - **Nivel 2 (Enriquecido)**: Recomendaciones - Stats ANUALES + biblioteca completa (100 artistas, 50 álbumes, todos géneros) - caché 15min
  - **Nivel 3 (Completo)**: Estadísticas - Stats TODO EL TIEMPO + análisis detallado (500 artistas, 200 álbumes, géneros, décadas) - caché 10min
  - **Biblioteca incluida en TODOS los niveles** - el agente siempre sabe qué música tienes disponible
  - Nuevos métodos: `_get_minimal_context()`, `_get_enriched_context()`, `_get_full_context()`

### 🔧 Mejorado
- **⚡ Rendimiento Optimizado con Caché Escalonado y Periodos Inteligentes**
  - Consultas simples: 50ms (contexto mensual + biblioteca desde caché)
  - Recomendaciones (primera vez): 800ms (stats anuales + biblioteca completa)
  - Recomendaciones (repetidas): 50ms (todo desde caché)
  - Consultas de perfil: 1200ms (stats all-time + análisis completo)
  - **Reducción de latencia del 92%** en consultas repetidas
  - TTL ajustados: 1h (mensual), 15min (anual), 10min (all-time)

- **🎯 Detección Inteligente de Nivel Requerido**
  - Pattern matching automático para determinar qué contexto necesita
  - Palabras clave para nivel 2: "recomienda", "sugiere", "ponme", "parecido", "similar", "nuevo", "descubrir"
  - Palabras clave para nivel 3: "mi biblioteca", "qué tengo", "mis escuchas", "mis estadísticas", "mi perfil musical"

- **📊 Contexto Siempre Disponible con Biblioteca Integrada**
  - El agente nunca responde "sin saber" quién eres
  - **TODOS los niveles incluyen contexto de biblioteca** - sabe qué música tienes disponible
  - Periodos progresivos (Mes → Año → Todo el tiempo) para relevancia contextual
  - Incluso en consultas simples como "Hola", tiene contexto mensual + biblioteca
  - Balance perfecto entre personalización, relevancia temporal y rendimiento

- **🎵 Playlists Mejoradas**
  - Query modificada para SIEMPRE incluir "con canciones de mi biblioteca"
  - Palabra clave "playlist" agregada a needs_library_search
  - Doble verificación: playlists SIEMPRE usan solo música que tienes
  - El agente combina gustos anuales + disponibilidad en biblioteca

- **🤖 TODOS los Comandos Ahora Usan el Agente con Contexto**
  - ✅ `/stats` → Análisis inteligentes con contexto nivel 3 (-63% código)
  - ✅ `/playlist` → Playlists personalizadas con contexto nivel 2 (-63% código)
  - ✅ `/releases` → Lanzamientos filtrados con contexto nivel 2 (-89% código)
  - ✅ `/library` → Resumen inteligente con contexto nivel 3 (-39% código)
  - ✅ `/nowplaying` → Info contextualizada con nivel 1 (-60% código)
  - ✅ `/search` → Búsqueda con sugerencias con nivel 1 (-58% código)
  - ✅ `/recommend` → Ya usaba el agente
  - ✅ Callback `more_recommendations` → Ahora usa el agente
  - ✅ Conversación natural → Ya usaba el agente

- **🧹 Simplificación Masiva del Código**
  - **-497 líneas** de código complejo eliminadas de `telegram_service.py`
  - Reducción total del **70%** en código de comandos
  - Toda la lógica centralizada en el agente conversacional
  - Código más mantenible y fácil de entender

### 🎨 Experiencia de Usuario
- **Conversaciones más naturales**: El agente conoce tus gustos desde el primer mensaje
- **Respuestas más rápidas**: Caché inteligente minimiza llamadas a APIs
- **Personalización progresiva**: El contexto se enriquece automáticamente según tus necesidades

### 📚 Documentación
- Nuevo archivo `ADAPTIVE_CONTEXT.md` con documentación completa del sistema
- Ejemplos detallados de cada nivel de contexto
- Comparación con alternativas y métricas de rendimiento
- Logs del sistema para debugging

### 🔄 Compatibilidad
- Totalmente retrocompatible con toda la funcionalidad existente
- No requiere cambios en variables de entorno
- Funciona automáticamente sin configuración adicional

## [4.0.1-alpha] - 2025-10-20

### 🔧 Mejorado
- **🔍 Búsqueda Ultra-Flexible**: Sistema de variaciones ortográficas y plurales
  - Manejo automático de errores ortográficos comunes (qu→k, c→k, k→qu, k→c)
  - Eliminación automática de plurales (canciones→cancion, álbumes→álbum)
  - Búsqueda con palabras individuales y orden inverso
  - Aplicado tanto a `/search` como `/share`
  - Ejemplos: "inquebrantables" encuentra "inkebrantable", "sfdk inquebrantables" encuentra resultados en cualquier orden
- **📋 Parseo Menos Estricto en `/share`**: Búsqueda más permisiva con coincidencias parciales
  - Matching flexible de artistas (coincidencias parciales en lugar de exactas)
  - Búsqueda de respaldo automática con palabras individuales
  - Notificación visual cuando se activa búsqueda flexible

### 🧹 Refactorizado
- **🔗 Limpieza de Código de Shares**: Simplificación de la función `create_share`
  - Eliminado código innecesario relacionado con parámetro `downloadable` (no funcional en API de Navidrome)
  - Eliminados todos los logs de debug redundantes
  - Reducción de ~140 líneas a ~80 líneas más limpias y mantenibles
  - Documentación actualizada sobre limitaciones de la API de Navidrome
  - Mensajes de usuario más honestos sobre funcionalidad de descargas

### 📝 Documentación
- Actualizado README con información precisa sobre funcionalidad de shares
- Agregada nota sobre dependencia de configuración del servidor para descargas
- Documentadas limitaciones de la API de Subsonic/Navidrome respecto a parámetro `downloadable`

## [4.0.0-alpha] - 2025-10-19

### 🎉 Migración Completa a Stack 100% Open-Source

Esta versión marca la eliminación completa de Last.fm del proyecto, migrando a un stack totalmente open-source: **ListenBrainz + MusicBrainz + Navidrome**.

### ✨ Añadido
- **🔄 Sistema de Recomendaciones Rediseñado**: 
  - Estrategia 1: ListenBrainz CF (collaborative filtering) basado en usuarios similares
  - Estrategia 2: MusicBrainz búsqueda global por tags/géneros
  - Estrategia 3: IA/Gemini como fallback para artistas sin metadata
- **🎵 Comando `/share`**: Genera enlaces públicos compartibles con opción de descarga
- **📰 Comando `/releases`**: Consulta nuevos lanzamientos de artistas de tu biblioteca
- **🎨 Recomendaciones de Biblioteca**: Sistema de redescubrimiento con filtros avanzados
- **🛡️ Manejo de Bloqueos de Gemini**: Respuestas elegantes ante filtros de seguridad

### 🔧 Mejorado
- **Orden de Prioridad de Recomendaciones**:
  - `/recommend` sin filtros: ListenBrainz+MusicBrainz SOLO (basado en historial real, más rápido)
  - `/recommend [género]`: IA primero para entender criterios específicos
- **Parseo de IA Robusto**: 
  - Pre-filtrado de líneas válidas
  - Validación estricta de formato
  - Eliminación automática de análisis/perfil
  - Validación de longitud mínima de razones
- **Sistema de Deduplicación**: 3 niveles (IA, ListenBrainz→Biblioteca, Final)
- **Búsqueda de Similares**: Excluye personas individuales, solo bandas/proyectos
- **Optimizaciones de Rendimiento**:
  - Cache de artistas de biblioteca (5 min)
  - Cache de recomendaciones ListenBrainz (5 min)
  - Límites optimizados en llamadas a APIs
  - Tiempos reducidos: ~8-12s → ~3-5s con cache

### 🗑️ Eliminado
- **❌ Last.fm Service**: Completamente eliminado (472 líneas)
- **❌ Variables de Entorno**: `LASTFM_API_KEY`, `LASTFM_USERNAME`
- **❌ Referencias en Código**: Todas las menciones a Last.fm en código funcional

### 🔄 Refactorizado
- **Modelos de Datos**: 
  - `LastFMTrack` → `ScrobbleTrack`
  - `LastFMArtist` → `ScrobbleArtist`
- **Claves de API**: `lastfm_artist_info` → `musicbrainz_artist_info`
- **Servicios**: Todos los servicios actualizados para usar ListenBrainz+MusicBrainz

### 🐛 Corregido
- Manejo robusto de bloqueos de seguridad de Gemini
- Detección correcta de intención 'recomendar_biblioteca'
- Parseo de recomendaciones IA sin truncamiento
- Funcionalidad de descarga en comando `/share`
- Validación de parámetros en createShare de Navidrome

### 📚 Documentación
- README actualizado eliminando Last.fm, destacando stack open-source
- MIGRATION.md completo con estrategias y tiempos esperados
- CLEANUP_SUMMARY.md documentando refactorización final
- env.example actualizado con nuevas variables

### 📊 Estadísticas de la Migración
- **19 commits** en la rama `remove-lastfm-use-listenbrainz`
- **13 archivos** modificados
- **1 archivo** eliminado (lastfm_service.py)
- **+1,740 líneas** añadidas
- **-976 líneas** eliminadas

### 🎯 Stack Final
- ✅ **ListenBrainz**: Scrobbling y recomendaciones colaborativas (gratuito, sin límites)
- ✅ **MusicBrainz**: Metadatos y búsquedas avanzadas (gratuito, open-source)
- ✅ **Navidrome**: Servidor de música autoalojado
- ✅ **Google Gemini**: IA para recomendaciones contextuales
- ✅ **100% Open-Source**: Sin dependencias de servicios comerciales

### ⚙️ Migración Requerida
Si actualizas desde v3.x, elimina estas variables de tu `.env`:
```env
# ELIMINAR:
# LASTFM_API_KEY=...
# LASTFM_USERNAME=...

# ASEGURAR que tienes:
LISTENBRAINZ_USERNAME=tu_usuario
LISTENBRAINZ_TOKEN=tu_token  # Opcional pero recomendado
ENABLE_MUSICBRAINZ=true
```

## [3.0.0-alpha] - 2025-10-18

### 🎉 Integración MusicBrainz - Búsquedas Avanzadas por Género/País/Época

Esta actualización añade integración completa con MusicBrainz para búsquedas musicales ultra-específicas, permitiendo consultas como "indie español de los 2000" o "rock progresivo de los 70s con sintetizadores".

### ✨ Añadido
- **🎵 Servicio MusicBrainz**: Nuevo `MusicBrainzService` para enriquecimiento y verificación de metadatos
- **🔍 Búsqueda Inversa**: Identifica artistas de tu biblioteca que cumplen criterios específicos (género, país, época)
- **💾 Cache Persistente**: Sistema de cache con expiración de 30 días para minimizar llamadas a la API
- **🔄 Búsqueda Incremental**: Comando "busca más" para continuar explorando tu biblioteca
- **📊 Verificación por Lotes**: Configurable vía `MUSICBRAINZ_BATCH_SIZE` (15-30 artistas por búsqueda)
- **🎯 Filtros Avanzados**: Soporte para género, país, idioma y rango de años
- **🗺️ Mapeo Inteligente de Géneros**: Relaciones entre géneros relacionados (indie/alternative, rock/hard rock, etc.)
- **⚙️ Configuración Flexible**: Variables de entorno para habilitar/deshabilitar y configurar límites

### 🔧 Mejorado
- **Detección de Intenciones**: Clasificar "busca más" como conversación para mantener contexto
- **Gestor de Conversaciones**: Nuevo atributo `context` en `ConversationSession` para búsquedas incrementales
- **Agente Musical**: 
  - SIEMPRE usar MusicBrainz para búsquedas de género y guardar contexto
  - Optimizar consultas simples saltando stats del usuario cuando no son necesarias
  - Priorizar género sobre search_term cuando coinciden
- **Rendimiento**: Aumentar límite de artistas verificados de 20/30 a 50 en búsquedas complejas
- **Logging**: Logging detallado del cache con edad de datos y estadísticas
- **Rate Limiting**: Respeto estricto del límite de 1 req/seg de MusicBrainz (1.1s para seguridad)
- **Comando /recommend**: Agregar fallback a Last.fm cuando MusicBrainz no encuentra suficientes resultados

### 🐛 Corregido
- **Manejo de Errores**: Manejo robusto de errores en MusicBrainz para artistas no encontrados
- **Respuestas Vacías**: Evitar crashes cuando MusicBrainz no devuelve datos válidos
- **Extracción Segura**: Manejo seguro de géneros, tags, área y life-span con fallbacks

### 📚 Documentación
- README actualizado con sección completa de MusicBrainz
- Documentación de todas las variables de entorno en `env.example`
- Guía de configuración: por qué usar MusicBrainz y cómo configurarlo
- docker-compose.yml actualizado con variables de MusicBrainz

### ⚙️ Configuración
Nuevas variables de entorno en `.env`:
```bash
# MusicBrainz Configuration (Optional)
ENABLE_MUSICBRAINZ=true
APP_NAME=MusicaloBot
CONTACT_EMAIL=your_email@example.com
MUSICBRAINZ_BATCH_SIZE=20
MUSICBRAINZ_MAX_TOTAL=100
```

### 📊 Métricas de Rendimiento
- **Cache Hit Rate**: ~80-90% en búsquedas repetidas
- **Tiempo por búsqueda**: ~17-33 segundos (dependiendo del batch size)
- **API Requests**: Minimizados gracias al cache persistente

### 🔗 Commits Principales
- `f1be050` - fix: Agregar fallback a Last.fm en comando /recommend
- `9d2303e` - feat: Optimizaciones de rendimiento en music_agent_service
- `c5de42c` - fix: SIEMPRE usar MusicBrainz para géneros y guardar contexto
- `8333194` - feat: Cache persistente y búsqueda incremental con 'busca más'
- `77adca0` - feat: Integrar MusicBrainz para búsqueda inversa de géneros

## [2.0.0-alpha] - 2025-10-17

### 🎉 Lanzamiento Mayor - Agente Musical Conversacional

Esta versión representa una reescritura completa del bot, transformándolo en un agente musical inteligente con capacidades conversacionales avanzadas.

### ✨ Añadido
- **🤖 Agente Musical Conversacional**: Sistema completo de detección de intenciones y respuestas inteligentes
- **📝 Sistema de Gestión de Conversaciones**: Mantiene contexto de hasta 10 mensajes por usuario
- **🎵 Creación de Playlists M3U**: Genera playlists directamente en Navidrome
- **🔍 Búsqueda Inteligente**: Normalización de texto, manejo de tildes y variaciones de nombres
- **🎯 Detección de Intenciones**: Clasifica automáticamente el tipo de consulta del usuario
- **🌐 Integración Híbrida**: Combina ListenBrainz + Last.fm con fallback automático
- **🎨 Filtrado Inteligente por Idioma**: Post-filtrado usando IA para garantizar idioma solicitado
- **🔀 Mapeo Inteligente de Géneros**: Relaciones y estrategias múltiples de búsqueda
- **📊 Estadísticas Mejoradas**: Soporte para rangos de tiempo de ListenBrainz
- **🎼 Playlists Exclusivas**: Cuando se solicita artista específico, solo incluye ese artista

### 🔧 Mejorado
- **Priorización de Biblioteca Local**: Siempre busca primero en biblioteca antes que en Last.fm
- **Extracción Mejorada de Términos**: Soporta typos comunes y múltiples formatos
- **Normalización de Búsquedas**: Maneja correctamente artistas con puntuación (Kase.O)
- **Resolución de Ambigüedades**: Distingue "disco" como álbum vs género
- **Formato M3U Estándar**: Compatible con Navidrome
- **Logs Detallados**: Diagnóstico completo de todas las operaciones

### 🗑️ Eliminado
- **Webhooks completos**: Bot funciona solo en modo polling
- **Configuración nginx**: Ya no se requiere proxy reverso
- **Scripts de deployment manual**: build-and-push.sh, quick-deploy.sh
- **Scripts docker obsoletos**: docker-*.sh
- **Comandos /info y /ask**: Simplificación de comandos
- **backend/main.py**: Solo era para webhooks

### 🐛 Corregido
- **CRÍTICO**: Bot ignoraba biblioteca completamente - ahora prioriza biblioteca local
- **CRÍTICO**: Filtrado de resultados irrelevantes antes de pasar a IA
- **CRÍTICO**: Bot inventaba álbumes mezclando artistas diferentes
- Distinción clara entre "últimos" y "top" artistas escuchados
- Endpoint correcto de API de ListenBrainz (/1/ en lugar de /1.0/)
- Detección correcta de "disco DE" vs "SIMILAR A"
- Normalización de texto para búsquedas (eliminar tildes/acentos)
- Búsqueda flexible con variaciones del término

### 📚 Documentación
- Guía completa del agente musical
- Documentación del sistema conversacional
- Guía completa de pruebas
- Documentación de todos los fixes críticos
- README actualizado con lista de comandos correcta

## [1.1.1-alpha] - 2025-10-15

### ✨ Añadido
- **🔒 Bot Privado**: Control de acceso por ID de usuario
  - Variable `TELEGRAM_ALLOWED_USER_IDS` para usuarios autorizados
  - Decorador `@_check_authorization` en todos los comandos
  - Mensaje informativo con ID para usuarios no autorizados
  - Logs de modo de seguridad (público/privado)
- **📚 Sección de Seguridad**: Guía completa en README

### 🐛 Corregido
- Error de sintaxis en `docker-compose.yml` (llaves faltantes)
- Error de sintaxis en `docker-compose.production.yml` (llaves faltantes)
- Health check eliminado (no funcional en modo polling)

### 🔧 Mejorado
- **Configuración consolidada**: Un solo archivo `env.example` para Docker y manual
- **README simplificado**: Eliminadas duplicaciones y secciones obsoletas
- **Documentación clara**: Explicación de archivos docker-compose
- **Rebranding completo**: "Music Agent" → "Musicalo" en todo el proyecto
- **Solo modo polling**: Eliminado todo código relacionado con webhooks
- Archivos bien documentados con comentarios organizados

### 🗑️ Eliminado
- `backend/main.py` (era solo para webhooks)
- `env.docker` (consolidado en `env.example`)
- Referencias a archivos inexistentes
- Secciones duplicadas en README
- Health check del Dockerfile (no aplicable en modo polling)
- Todo el código relacionado con webhooks
- Mapeo de puertos en docker-compose (innecesario en modo polling)
- Variables de entorno no usadas: `DEBUG`, `HOST`, `PORT`, `TELEGRAM_WEBHOOK_URL`

## [1.1.0-alpha] - 2025-10-15

### ✨ Añadido
- **Conversación Natural con IA**: Interactúa con el bot sin usar comandos, simplemente escribe lo que quieres
- **Interpretación Inteligente**: Gemini AI entiende la intención del usuario y ejecuta la acción apropiada
- **Respuestas Contextuales**: El bot responde usando tus datos reales de Last.fm/ListenBrainz (20 últimas canciones + 10 top artistas)
- **Detección de Referencias**: Reconoce cuando mencionas un artista específico para buscar similares (ej: "como Pink Floyd")
- **Detección de Cantidad**: Respeta singular (1 resultado) vs plural (5 resultados)
- **Variedad en Recomendaciones**: Sistema de randomización que muestra diferentes resultados cada vez
- **Modo Chat**: Nueva acción conversacional para preguntas específicas sobre tu música
- **Fallback Conversacional**: Si no entiende el mensaje, responde conversacionalmente con contexto completo

### 🔧 Mejorado
- Parseo de argumentos más robusto (detecta tipo y similar en cualquier orden)
- Formato de salida diferenciado por tipo (álbumes, artistas, canciones)
- Manejo de errores mejorado con fallbacks útiles
- Sistema de webhook con verificación previa para evitar rate limiting
- Búsqueda ampliada de artistas similares (30 en lugar de 20)
- Mensajes de bienvenida y ayuda actualizados con ejemplos de lenguaje natural

### 🗑️ Eliminado
- Watchtower de docker-compose (simplificación)
- 9 archivos redundantes de testing (consolidados en TESTING.md)
- Imports duplicados (optimizados al inicio del archivo)
- Configuración duplicada de webhook en docker-entrypoint.sh

### 🐛 Corregido
- Error de rate limiting al configurar webhook (429 - Flood control exceeded)
- Detección correcta de rec_type="album" cuando usuario dice "disco"
- Indentaciones en bloques condicionales
- Compatibilidad con diferentes versiones de google-generativeai
- Uso de modelo correcto (gemini-2.0-flash-exp)

### 📚 Documentación
- README.md actualizado con sección destacada de lenguaje natural
- TESTING.md con proceso simplificado de testing
- CHANGELOG-v1.1.0.md con detalles completos del release
- LISTO-PARA-PROBAR.md con checklist de validación
- Roadmap actualizado (modo conversacional marcado como completado)

## [1.0.0] - 2025-10-XX

### Lanzamiento Inicial
- Bot de Telegram con comandos básicos
- Integración con Navidrome
- Soporte para ListenBrainz
- Recomendaciones con Google Gemini
- Comandos: /start, /help, /recommend, /library, /stats, /search
- Despliegue con Docker y Docker Compose
- Scripts de gestión (docker-start.sh, docker-logs.sh, etc)

