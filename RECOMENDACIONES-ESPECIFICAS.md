# 🎨 Recomendaciones Específicas - Guía de Uso

## Visión General

Musicalo ahora soporta **peticiones ultra-específicas** para recomendaciones de música. Puedes describir exactamente lo que estás buscando con todos los detalles que quieras, y la IA entenderá y generará recomendaciones precisas basadas en tus criterios.

## ¿Qué ha cambiado?

### Antes (Limitado)
- ✅ "Recomiéndame rock"
- ✅ "Discos similares a Pink Floyd"
- ❌ "Rock progresivo de los 70s con sintetizadores atmosféricos"

### Ahora (Ilimitado)
- ✅ "Recomiéndame rock"
- ✅ "Discos similares a Pink Floyd"
- ✅ **"Rock progresivo de los 70s con sintetizadores atmosféricos"**
- ✅ **"Música energética con buenos solos de guitarra para hacer ejercicio"**
- ✅ **"Jazz suave instrumental perfecto para estudiar"**

## Ejemplos de Uso

### 🎸 Por Características Musicales

```
"Rock progresivo de los 70s con sintetizadores"
→ Pink Floyd, Yes, Genesis, King Crimson, ELP

"Metal melódico con voces limpias"
→ Nightwish, Sonata Arctica, Kamelot

"Música energética con buenos solos de guitarra"
→ Led Zeppelin, Deep Purple, Van Halen

"Jazz suave instrumental para estudiar"
→ Bill Evans, Keith Jarrett, Brad Mehldau
```

### 🎭 Por Mood/Ambiente

```
"Álbumes conceptuales melancólicos"
→ Radiohead - OK Computer, Pink Floyd - The Wall

"Música atmosférica y envolvente"
→ Sigur Rós, Explosions in the Sky

"Rock alegre y optimista"
→ The Beatles, The Beach Boys

"Música relajante para dormir"
→ Brian Eno, Max Richter
```

### 📅 Por Época

```
"Rock clásico de los 70s"
→ Led Zeppelin, Queen, The Who

"Punk de los 80s"
→ The Clash, Dead Kennedys, Bad Religion

"Rock alternativo español de los 90s"
→ Héroes del Silencio, Extremoduro, Platero y Tú

"Indie moderno de la última década"
→ Tame Impala, Arctic Monkeys, The Strokes
```

### 🎯 Por Uso/Contexto

```
"Música perfecta para hacer ejercicio"
→ Música energética, ritmos rápidos

"Jazz tranquilo para una cena romántica"
→ Jazz suave, instrumentales

"Rock para un viaje largo en carretera"
→ Rock clásico, rock progresivo

"Música de fondo para trabajar concentrado"
→ Ambient, post-rock, electrónica suave
```

### 🎵 Combinando Múltiples Criterios

```
"Rock progresivo español con influencias de jazz"
→ Búsqueda muy específica con múltiples características

"Metal sinfónico con orquestaciones épicas y voces operísticas"
→ Nightwish, Epica, Therion

"Rock alternativo melancólico con letras poéticas en español"
→ Zoé, Caifanes, Soda Stereo

"Electrónica experimental de los 90s con influencias de ambient"
→ Aphex Twin, Autechre, Boards of Canada
```

## Cómo Funciona Técnicamente

### 1. Detección Inteligente
El bot usa IA (Gemini) para analizar tu mensaje y detectar cuando estás siendo específico:

```python
# Petición simple → usa género básico
"rock" → genre_filter="rock"

# Petición específica → usa custom_prompt
"rock progresivo de los 70s con sintetizadores" 
→ custom_prompt="rock progresivo de los 70s con sintetizadores"
```

### 2. Generación de Recomendaciones
Cuando detecta un `custom_prompt`, la IA:

1. **Analiza** todos los criterios mencionados
2. **Considera** tu perfil musical (top artistas, escuchas recientes)
3. **Balancea** entre tus gustos y los criterios específicos
4. **Genera** recomendaciones que cumplen TODOS los criterios

### 3. Enriquecimiento de Datos
Las recomendaciones se enriquecen con:
- URLs de Last.fm para más información
- Álbumes específicos de los artistas
- Razones detalladas de por qué se recomienda cada uno

## Tipos de Peticiones Soportadas

### ✅ Peticiones que Funcionan Mejor

1. **Con adjetivos descriptivos**
   - "melancólico", "energético", "suave", "épico"

2. **Con instrumentos específicos**
   - "con sintetizadores", "buenos solos de guitarra", "piano"

3. **Con referencias temporales**
   - "de los 70s", "moderno", "clásico"

4. **Con contexto de uso**
   - "para estudiar", "para ejercicio", "para dormir"

5. **Con características vocales**
   - "con voces limpias", "voces operísticas", "instrumental"

### ⚠️ Limitaciones Actuales

- La calidad depende del conocimiento musical de Gemini AI
- No puede buscar en tu biblioteca de Navidrome con criterios específicos (solo en Last.fm)
- Las recomendaciones son generales, no personalizadas a tu biblioteca local

## Ejemplos Prácticos de Conversación

### Ejemplo 1: Petición Específica
```
Usuario: "Recomiéndame rock progresivo de los 70s con sintetizadores"

Bot: 🎨 Analizando tu petición: 'rock progresivo de los 70s con sintetizadores'...

Bot: 🎨 Recomendaciones para: rock progresivo de los 70s con sintetizadores

1. 🎤 Pink Floyd - The Dark Side of the Moon
   📀 The Dark Side of the Moon
   💡 Álbum conceptual de rock progresivo de 1973 con sintetizadores 
       atmosféricos (según: rock progresivo de los 70s con sintetizadores...)
   🔗 Fuente: AI (Gemini)
   🌐 Ver en Last.fm
   🎯 95% match

2. 🎤 Yes - Close to the Edge
   ...
```

### Ejemplo 2: Petición con Contexto
```
Usuario: "Música suave y relajante para estudiar"

Bot: 🎨 Analizando tu petición: 'música suave y relajante para estudiar'...

Bot: 🎨 Recomendaciones para: música suave y relajante para estudiar

1. 🎤 Bill Evans - Sunday at the Village Vanguard
   💡 Jazz instrumental suave perfecto para concentración
   ...
```

### Ejemplo 3: Múltiples Criterios
```
Usuario: "Metal melódico europeo con voces femeninas"

Bot: 🎨 Analizando tu petición: 'metal melódico europeo con voces femeninas'...

Bot: 🎨 Recomendaciones para: metal melódico europeo con voces femeninas

1. 🎤 Nightwish - Oceanborn
   💡 Metal sinfónico finlandés con voces operísticas de Tarja Turunen
   ...
```

## Mejores Prácticas

### ✅ Hacer
- Sé específico con lo que buscas
- Menciona múltiples características
- Usa adjetivos descriptivos
- Incluye contexto de uso si es relevante

### ❌ Evitar
- Peticiones demasiado ambiguas ("música buena")
- Contradicciones ("rock suave pero muy agresivo")
- Pedir artistas muy oscuros o locales (la IA podría no conocerlos)

## Comandos Relacionados

- `/recommend` - Modo básico de recomendaciones
- `/ask <pregunta>` - Para preguntas sobre música
- `/search <término>` - Buscar en tu biblioteca
- `/help` - Ver todos los comandos disponibles

## Retroalimentación

¿Tienes sugerencias para mejorar las recomendaciones específicas? ¡Háznoslo saber!

---

**Versión del documento:** 1.0  
**Última actualización:** Octubre 2025  
**Feature:** Custom Prompt Recommendations

