# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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

