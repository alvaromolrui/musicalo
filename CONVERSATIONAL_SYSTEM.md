# Sistema Conversacional Natural - Musicalo Bot

## 🎯 Resumen de Cambios

Se ha implementado un sistema completo de conversación natural que permite al usuario interactuar con el bot **sin necesidad de recordar comandos específicos**. El bot ahora entiende lenguaje natural y mantiene contexto entre mensajes.

### 🆕 Actualización v2.1 - Simplificación Radical (2025-01-16)

**Problema Resuelto:** El sistema detectaba incorrectamente intenciones (ej: "últimos 3 artistas" iba a `stats` en lugar de responder la pregunta específica).

**Solución:** Simplificar `IntentDetector` de 9 intenciones a solo 5:
- **De 9 intenciones → 5 intenciones**
- **Filosofía nueva:** Solo detectar intenciones MUY obvias (palabras clave)
- **Default:** 95% de casos van a `conversacion` (el agente es inteligente)
- **Resultado:** El bot responde correctamente a preguntas específicas sin mostrar dashboard completo

**Intenciones v2.1:**
1. `playlist` - Solo si dice "haz/crea playlist"
2. `buscar` - Solo si dice "busca/buscar"
3. `recomendar` - Solo si dice "similar a [artista]"
4. `referencia` - Solo si dice "más de eso" sin artista
5. `conversacion` - **TODO LO DEMÁS** ← Este es el poder del sistema

---

## 📦 Nuevos Componentes

### 1. **ConversationManager** (`backend/services/conversation_manager.py`)

**Propósito:** Gestionar el contexto conversacional de cada usuario.

**Características:**
- Sesiones por usuario con timeout de 2 horas
- Memoria de últimos 10 mensajes (usuario + asistente)
- Guarda últimas 10 recomendaciones para referencias
- Tracking de última acción realizada
- Limpieza automática de sesiones expiradas

**API Principal:**
```python
# Obtener/crear sesión de usuario
session = conversation_manager.get_session(user_id)

# Agregar mensaje al historial
session.add_message("user", "ponme rock progresivo")
session.add_message("assistant", "Te recomiendo...")

# Guardar recomendaciones
session.set_last_recommendations(recommendations)

# Obtener contexto formateado para IA
context = session.get_context_for_ai()

# Limpiar sesión
conversation_manager.clear_session(user_id)
```

---

### 2. **IntentDetector** (`backend/services/intent_detector.py`)

**Propósito:** Detectar la intención del usuario usando Gemini LLM.

**Intenciones Soportadas (SOLO 5 - Simplificado v2.1):**
- `playlist` - SOLO cuando pide explícitamente "haz/crea playlist"
- `buscar` - SOLO cuando usa palabra "busca/buscar"
- `recomendar` - SOLO cuando dice "similar a [artista]"
- `referencia` - SOLO cuando dice "más de eso" sin mencionar artista
- `conversacion` - **TODO LO DEMÁS** (95% de casos, por defecto)

**Filosofía:** El `IntentDetector` es ultra-conservador y solo detecta intenciones MUY obvias. El agente conversacional es lo suficientemente inteligente para manejar cualquier consulta, por lo que todo lo que no sea obvio va a `conversacion` por defecto.

**Ejemplo de Uso:**
```python
intent_detector = IntentDetector()

intent_data = await intent_detector.detect_intent(
    "recomiéndame rock progresivo de los 70s",
    session_context="Usuario escuchó Pink Floyd recientemente",
    user_stats={'top_artists': ['Pink Floyd', 'Queen']}
)

# Resultado:
# {
#   "intent": "recomendar",
#   "params": {
#     "description": "rock progresivo de los 70s",
#     "genres": ["rock progresivo"],
#     "time_period": "70s"
#   },
#   "confidence": 0.9
# }
```

---

### 3. **SystemPrompts** (`backend/services/system_prompts.py`)

**Propósito:** Centralizar y estandarizar todos los prompts del sistema.

**Prompts Disponibles:**
- `get_music_assistant_prompt()` - Prompt principal del asistente
- `get_recommendation_prompt()` - Prompt para recomendaciones
- `get_playlist_prompt()` - Prompt para crear playlists
- `get_info_query_prompt()` - Prompt para consultas de información
- `get_error_message()` - Mensajes de error amigables

**Características:**
- Contexto temporal automático (hora del día, día de la semana)
- Personalidad del asistente definida claramente
- Integración de estadísticas del usuario
- Tono conversacional y natural

---

## 🔄 Componentes Modificados

### 4. **MusicAgentService** (Refactorizado)

**Cambios Principales:**
- Nuevo parámetro `user_id` en método `query()`
- Integración con `ConversationManager`
- Uso de `SystemPrompts` para personalización
- Mantiene historial de conversación automáticamente

**Antes:**
```python
result = await agent.query("¿Qué álbumes tengo de Pink Floyd?")
```

**Después:**
```python
result = await agent.query(
    "¿Qué álbumes tengo de Pink Floyd?",
    user_id=123456,  # ID del usuario de Telegram
    context={"type": "conversational"}
)
```

---

### 5. **TelegramService** (Simplificado)

**Cambios Principales:**
- `handle_message()` reducido de 300+ líneas a ~150 líneas
- Eliminado `_detect_intent_with_regex()` (complejo sistema de regex)
- Uso de `IntentDetector` para clasificación
- Guardado automático de recomendaciones en sesión
- Soporte para referencias contextuales

**Flujo Nuevo:**
```
Usuario envía mensaje
    ↓
IntentDetector analiza con Gemini
    ↓
Se detecta intención + parámetros
    ↓
Se ejecuta acción correspondiente
    ↓
Se guarda en historial conversacional
```

---

## 🎨 Ejemplos de Uso

### Ejemplo 1: Conversación Natural Simple
```
Usuario: "recomiéndame un disco"
Bot: [Detecta: conversacion (no es obvio que sea 'recomendar')]
     [Agente procesa] "📀 Te recomiendo 'OK Computer' de Radiohead..."

Usuario: "ponme otro"
Bot: [Detecta: referencia, usa última recomendación]
     "🎵 Similar a Radiohead, te va a gustar 'The Bends'..."
```

### Ejemplo 2: Consulta con Contexto (FIX v2.1)
```
Usuario: "¿cuáles son los últimos 3 artistas que escuché?"
Bot: [Detecta: conversacion (pregunta específica)]
     [Agente responde específicamente]
     "Los últimos 3 artistas que has escuchado son:
      1. Childish Gambino
      2. Bestia Bebé
      3. Extremoduro"
```

### Ejemplo 3: Petición Específica
```
Usuario: "rock progresivo de los 70s con sintetizadores"
Bot: [Detecta: conversacion (no usa 'similar a')]
     [Agente procesa criterios]
     "🎸 Perfecto, te recomiendo:
      • Yes - Close to the Edge
      • Emerson, Lake & Palmer - Tarkus..."
```

### Ejemplo 4: Palabra Clave Específica
```
Usuario: "busca Pink Floyd"
Bot: [Detecta: buscar (palabra clave "busca")]
     "🔍 Encontré 3 álbumes de Pink Floyd en tu biblioteca..."

Usuario: "similar a Pink Floyd"
Bot: [Detecta: recomendar (palabra clave "similar a")]
     "🎸 Te recomiendo artistas similares:
      • King Crimson, Yes, Genesis..."
```

---

## 🧪 Cómo Probar

### 1. Prueba Básica de Conversación
```bash
# Iniciar el bot
python backend/bot.py

# En Telegram, enviar:
"recomiéndame música rock"
# Debería recomendar rock

"ponme algo parecido"
# Debería usar la última recomendación como contexto
```

### 2. Prueba de Memoria Conversacional
```bash
# En Telegram:
"busca Queen"
"dame información de eso"
# Debería entender que "eso" se refiere a Queen
```

### 3. Prueba de Intenciones Múltiples
```bash
# Intentar diferentes tipos de peticiones:
"recomiéndame un disco de Pink Floyd"        # info (busca en biblioteca)
"similar a Pink Floyd"                        # recomendar con similar_to
"haz playlist con Pink Floyd y Queen"         # playlist
"qué he escuchado esta semana"                # stats
"¿qué es el jazz?"                            # pregunta_general
"busca Radiohead"                             # buscar
```

---

## 📊 Métricas de Mejora

### Antes (v1.0)
- ~800 líneas de código complejo en `telegram_service.py`
- Sistema de regex frágil y difícil de mantener
- Sin memoria entre mensajes
- Usuario debe adaptarse a comandos específicos

### v2.0 (Sistema Conversacional)
- ~500 líneas de código más limpio
- Detección de intenciones con LLM (9 intenciones)
- Memoria conversacional completa
- Usuario habla naturalmente
- +3 nuevos módulos especializados

### v2.1 (Simplificación) - ACTUAL
- ~450 líneas de código ultra-limpio
- Solo 5 intenciones (ultra-conservador)
- 95% de casos van a conversación por defecto
- Agente conversacional hace el trabajo pesado
- **Fix:** Preguntas específicas responden correctamente

---

## 🔧 Configuración

No se requiere configuración adicional. El sistema usa las mismas variables de entorno:

```env
GEMINI_API_KEY=tu_api_key
LASTFM_API_KEY=tu_lastfm_key
LASTFM_USERNAME=tu_usuario
NAVIDROME_URL=http://tu_servidor:4533
NAVIDROME_USERNAME=tu_usuario
NAVIDROME_PASSWORD=tu_password
```

---

## 🚀 Próximas Mejoras Posibles

1. **Persistencia de Sesiones:**
   - Guardar sesiones en Redis/DB para supervivencia entre reinicios

2. **Análisis de Sentimiento:**
   - Detectar mood del usuario en tiempo real
   - Adaptar recomendaciones según estado emocional

3. **Aprendizaje de Preferencias:**
   - Machine learning sobre feedback (likes/dislikes)
   - Personalización automática del sistema de recomendaciones

4. **Multi-idioma:**
   - Soporte para inglés, español, y otros idiomas
   - Detección automática de idioma del usuario

5. **Voice Support:**
   - Integración con mensajes de voz de Telegram
   - Transcripción automática y procesamiento

---

## 📚 Arquitectura

```
┌─────────────────────────────────────────────────┐
│              TelegramService                     │
│  (Punto de entrada, maneja updates)             │
└─────────────┬───────────────────────────────────┘
              │
              ├──> ConversationManager
              │    (Gestiona sesiones y contexto)
              │
              ├──> IntentDetector
              │    (Clasifica intención con Gemini)
              │
              ├──> MusicAgentService
              │    (Consultas conversacionales)
              │    │
              │    ├──> LastFMService
              │    ├──> NavidromeService
              │    └──> ListenBrainzService
              │
              └──> SystemPrompts
                   (Prompts centralizados)
```

---

## 🐛 Troubleshooting

### Problema: Bot no recuerda conversaciones anteriores
**Solución:** Verificar que el `user_id` se está pasando correctamente en todas las llamadas a `agent.query()`.

### Problema: Detección de intenciones incorrecta
**Solución:** Revisar logs para ver qué intención se detectó. Puede ser necesario ajustar prompts en `IntentDetector`.

### Problema: Sesiones no expiran
**Solución:** Llamar periódicamente a `conversation_manager.clear_old_sessions()` en un job programado.

---

## 📝 Notas de Desarrollo

- Todas las sesiones están en memoria. Para producción con múltiples instancias, considerar Redis.
- El timeout de sesión es configurable en `ConversationManager.__init__()`.
- Los prompts en `SystemPrompts` pueden ajustarse según necesidades específicas.
- `IntentDetector` usa Gemini 2.0 Flash para velocidad y costo-efectividad.

---

## ✅ Checklist de Testing

- [ ] Conversación básica funciona
- [ ] Referencias a mensajes anteriores funcionan ("más de eso")
- [ ] Todas las intenciones se detectan correctamente
- [ ] Sesiones expiran después de 2 horas
- [ ] Recomendaciones se guardan en sesión
- [ ] Comandos tradicionales siguen funcionando
- [ ] No hay memory leaks con sesiones
- [ ] Logs muestran detección de intenciones

---

**Implementado:** 2025-01-16  
**Versión:** 2.0.0 (Sistema Conversacional)  
**Branch:** `feature/music-agent-improvements`

