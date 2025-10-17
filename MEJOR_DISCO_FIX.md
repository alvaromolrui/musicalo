# Fix: Consulta "Mejor disco de [artista]"

## Problema Identificado

Cuando el usuario preguntaba "¿Cuál es el mejor disco de El Mató?", el sistema respondía que no tenía ningún disco de ese artista en su biblioteca, a pesar de que sí los tenía. Solo cuando preguntaba explícitamente "¿Qué discos tengo de El Mató?" el sistema mostraba correctamente los 8 álbumes disponibles.

### Causa Raíz

El sistema solo activaba la búsqueda en biblioteca cuando detectaba palabras clave específicas como:
- "tengo", "biblioteca", "colección"
- "álbum", "disco"

Pero NO se activaba con frases como:
- "mejor disco de"
- "mejor álbum de"
- "recomiéndame un disco de"

Esto causaba que el sistema solo consultara Last.fm y asumiera que el usuario no tenía música de ese artista.

## Cambios Implementados

### 1. Detección Mejorada de Búsquedas en Biblioteca

**Archivo:** `backend/services/music_agent_service.py`
**Líneas:** 203-210

Agregadas nuevas palabras clave para activar búsqueda en biblioteca:
- `"mejor disco de"`
- `"mejor álbum de"`
- `"disco de"`
- `"álbum de"`
- `"discografía"`
- `"música de"`
- `"canciones de"`
- `"temas de"`

### 2. Extracción Mejorada de Términos de Búsqueda

**Archivo:** `backend/services/music_agent_service.py`
**Líneas:** 650-665

Mejorada la función `_extract_search_term()` para reconocer patrones como:
- "mejor disco de [artista]"
- "mejor álbum de [artista]"
- "disco de [artista]"
- "álbum de [artista]"

Ahora extrae correctamente el nombre del artista de consultas más complejas.

### 3. Consulta Automática a Last.fm para Recomendaciones

**Archivo:** `backend/services/music_agent_service.py`
**Líneas:** 291-304

Agregada búsqueda automática en Last.fm cuando se pregunta por el "mejor disco" de un artista:
```python
if self.lastfm and needs_library_search and search_term and any(word in query_lower for word in ["mejor", "recomend"]):
    top_albums = await self.lastfm.get_artist_top_albums(search_term, limit=10)
    if top_albums:
        data["lastfm_artist_info"] = {
            "artist": search_term,
            "top_albums": top_albums
        }
```

### 4. Formateo de Información de Last.fm

**Archivo:** `backend/services/music_agent_service.py`
**Líneas:** 435-458

Agregado formateo de los top álbumes de Last.fm con:
- Nombre del álbum
- Número de escuchas globales
- URL de Last.fm
- Instrucciones para el AI sobre cómo combinar biblioteca + popularidad

### 5. Reglas Mejoradas para el AI

**Archivo:** `backend/services/music_agent_service.py`
**Líneas:** 110-120

Actualizadas las reglas críticas del prompt del AI:
```
1. SIEMPRE consulta PRIMERO la biblioteca (📚) para ver qué tiene el usuario
2. LUEGO complementa con Last.fm (🌍) para recomendaciones y descubrimientos
3. Si preguntan "mejor disco/álbum de X":
   a) Verifica QUÉ TIENE en biblioteca de ese artista
   b) Combina con recomendaciones de Last.fm
   c) Responde: "En tu biblioteca tienes X, Y, Z. Según Last.fm, el mejor es..."
```

## Comportamiento Esperado Después del Fix

### Antes (❌)
```
Usuario: "¿Cuál es el mejor disco de El Mató?"
Bot: "En tu biblioteca no tienes ningún disco de ellos, pero en Last.fm su mejor álbum es La Dinastía Scorpio"
```

### Después (✅)
```
Usuario: "¿Cuál es el mejor disco de El Mató?"
Bot: "¡Veo que tienes varios discos de El Mató a un Policía Motorizado en tu biblioteca! 📀

En tu colección:
📀 La Dinastía Scorpio (2014) - 15 canciones
📀 La Dinastía Scorpio (2013) - 12 canciones
📀 Súper Terror (2023) - 10 canciones
📀 La Sintesis O'Konor (2022) - 10 canciones
[... y más]

Según Last.fm y la opinión general, su mejor álbum es **La Dinastía Scorpio** (que ya tienes 🎉). Es considerado su obra maestra con melodías pegadizas y letras introspectivas."
```

## Flujo de Datos Mejorado

```
Usuario: "¿Cuál es el mejor disco de [artista]?"
    ↓
1. Detectar intención (activar búsqueda en biblioteca)
    ↓
2. Extraer término: "[artista]"
    ↓
3. Buscar en Navidrome: albums, artists, tracks del artista
    ↓
4. Buscar en Last.fm: top albums del artista (popularidad global)
    ↓
5. Combinar ambas fuentes en contexto para el AI
    ↓
6. AI genera respuesta integrando:
   - Qué tiene el usuario en biblioteca
   - Qué es más popular según Last.fm
   - Recomendación personalizada
```

## Testing

Para probar el fix:

1. **Caso 1: Usuario tiene música del artista**
   ```
   Usuario: "¿Cuál es el mejor disco de El Mató?"
   Esperado: Muestra los discos que tiene + recomendación de Last.fm
   ```

2. **Caso 2: Usuario NO tiene música del artista**
   ```
   Usuario: "¿Cuál es el mejor disco de Radiohead?"
   Esperado: Indica que no tiene + recomienda basado en Last.fm
   ```

3. **Caso 3: Consulta sobre qué tiene (sin cambios)**
   ```
   Usuario: "¿Qué discos tengo de El Mató?"
   Esperado: Lista solo lo que tiene en biblioteca (sin Last.fm)
   ```

## Beneficios

1. **Respuestas más completas**: El sistema siempre verifica ambas fuentes
2. **Mejor experiencia de usuario**: No dice "no tienes nada" cuando sí tiene
3. **Recomendaciones inteligentes**: Combina posesión personal + popularidad global
4. **Coherencia**: Mismo comportamiento para preguntas similares

## Cambios Adicionales (Fix v2)

### Problema: El filtro seguía descartando resultados

Después del primer fix, el sistema seguía diciendo "En tu biblioteca no encuentro nada" porque:
- El término extraído era "el mató"
- Navidrome devolvía "El Mató a un Policía Motorizado"
- El filtro de similitud (60%) lo descartaba porque "el mató" vs "El Mató a un Policía Motorizado" tenía baja similitud

### Solución: Filtro mejorado con búsqueda por contenido

**Archivo:** `backend/services/music_agent_service.py`

#### Cambio 1: Filtro de álbumes más permisivo (líneas 621-638)
```python
# ANTES: Solo usaba similitud de 60%
if artist_similarity >= SIMILARITY_THRESHOLD or search_lower in album.artist.lower():

# DESPUÉS: Verifica si el término está CONTENIDO en el nombre
if (search_lower in artist_lower or 
    artist_lower.startswith(search_lower) or
    artist_similarity >= SIMILARITY_THRESHOLD or 
    search_lower in album.name.lower()):
```

Ahora mantiene resultados si:
1. El término de búsqueda está **contenido** en el nombre del artista
2. El nombre del artista **comienza** con el término
3. La similitud es ≥ 60%
4. El término está en el nombre del álbum

#### Cambio 2: Filtro de artistas mejorado (líneas 640-652)
Similar mejora para artistas: busca por contenido además de similitud.

#### Cambio 3: Filtro de canciones mejorado (líneas 654-665)
Similar mejora para canciones.

#### Cambio 4: Extracción de términos más robusta (líneas 708-728)
```python
# MEJORADO: Captura mejor nombres sin mayúsculas
de_patterns = [
    # Patrón específico para "mejor disco/álbum de X"
    r'(?:mejor\s+)?(?:disco|álbum|album)\s+de\s+(.+?)(?:\?|$)',
    # Patrón general "de X"
    r'\bde\s+([a-zA-Záéíóúñ][a-zA-Záéíóúñ\s]+?)(?:\s+tengo|\s+teengo|\s+en|\?|$)'
]
```

Ahora:
- Captura todo después de "disco de" hasta el "?"
- Soporta caracteres con acentos (áéíóúñ)
- Más permisivo con nombres en minúsculas

## Notas Adicionales

- La palabra "mejor" ahora también activa la búsqueda de música nueva (`needs_new_music`)
- El filtrado ahora usa **búsqueda por contenido** además de similitud
- "el mató" encuentra "El Mató a un Policía Motorizado" ✅
- "pink" encuentra "Pink Floyd" ✅
- "radio" encuentra "Radiohead" ✅
- El sistema sigue priorizando la biblioteca sobre fuentes externas
- Las conversaciones mantienen el contexto entre mensajes

