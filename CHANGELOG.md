# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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

