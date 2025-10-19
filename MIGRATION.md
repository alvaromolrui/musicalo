# Migración de Last.fm a ListenBrainz + MusicBrainz

## 📋 Resumen

Esta rama (`remove-lastfm-use-listenbrainz`) migra completamente el proyecto de Last.fm a un stack 100% open-source usando **ListenBrainz** y **MusicBrainz**.

## 🎯 Motivación

- ✅ **Open-source completo**: Sin dependencias de servicios comerciales
- ✅ **Sin límites de API**: ListenBrainz no tiene restricciones estrictas
- ✅ **Mejor privacidad**: Control total de tus datos
- ✅ **Más funcionalidades**: MusicBrainz ofrece relaciones entre artistas y metadatos detallados
- ✅ **Sostenibilidad**: No depender de APIs que pueden cambiar o desaparecer

## 🔄 Cambios Principales

### 1. Servicios Eliminados

- ❌ `backend/services/lastfm_service.py` (472 líneas eliminadas)

### 2. Servicios Extendidos

#### **ListenBrainzService** - Nuevos métodos:
- `get_recommendations(count)` - Recomendaciones colaborativas personalizadas
- `get_similar_artists_from_recording(artist, limit, mb_service)` - Artistas similares con fallback a MusicBrainz
- `get_similar_tracks_from_recording(track, artist, limit)` - Canciones similares
- `get_lb_radio(mode, seed_artist, count)` - Radio personalizada
- `get_explore_playlists()` - Playlists de descubrimiento
- `get_similar_recordings(recording_mbid, count)` - Grabaciones similares por MBID
- `get_sitewide_stats(stat_type, range_type)` - Trending/popular global

#### **MusicBrainzService** - Nuevos métodos:
- `get_artist_relationships(artist, relation_types)` - Colaboraciones y relaciones
- `discover_similar_artists(artist, library_artists, limit)` - Similitud basada en metadatos
- `find_similar_by_tags(artist, limit)` - Búsqueda global por tags/géneros
- `get_artist_top_albums_enhanced(artist, limit)` - Álbumes con score
- `get_artist_top_tracks_enhanced(artist, limit)` - Tracks para recomendaciones

### 3. Archivos Actualizados

- **ai_service.py**: 
  - Eliminado import de `LastFMService`
  - Renombrado `_generate_lastfm_recommendations` → `_generate_listenbrainz_recommendations`
  - Todas las llamadas ahora usan ListenBrainz + MusicBrainz
  - Conversión automática de `genre_filter` a `custom_prompt`
  - Sistema de deduplicación en 3 niveles

- **telegram_service.py**:
  - Eliminado import de `LastFMService`
  - Eliminada lógica dual ListenBrainz/Last.fm
  - Enlaces dinámicos según servicio (MusicBrainz/ListenBrainz)
  - Mensajes de ayuda actualizados

- **music_agent_service.py**:
  - Eliminado import de `LastFMService`
  - Eliminada inicialización de `self.lastfm`
  - Eliminados todos los fallbacks a Last.fm
  - Actualizado para usar solo ListenBrainz
  - Actualizado `_get_artist_info` para usar MusicBrainz
  - ✅ Renombrado key `lastfm_artist_info` → `musicbrainz_artist_info`

- **models/schemas.py**:
  - ✅ Renombrados `LastFMTrack` → `ScrobbleTrack` y `LastFMArtist` → `ScrobbleArtist`
  - Documentación actualizada para reflejar origen en servicios de scrobbling (ListenBrainz)
  - Eliminadas todas las referencias a Last.fm en nombres de clases

- **system_prompts.py**:
  - Todas las capacidades actualizadas a ListenBrainz+MusicBrainz
  - Ejemplos actualizados sin menciones a Last.fm
  - Filosofía de recomendación actualizada

- **env.example**:
  - Eliminadas variables `LASTFM_API_KEY` y `LASTFM_USERNAME`
  - ListenBrainz marcado como REQUERIDO
  - MusicBrainz marcado como RECOMENDADO

- **README.md**:
  - Eliminadas secciones de Last.fm
  - Destacado stack 100% open-source
  - Actualizada descripción de servicios

- **docker-compose.yml** y **docker-entrypoint.sh**:
  - Cambiado a build local (para desarrollo)
  - Eliminadas variables de entorno de Last.fm
  - ✅ Eliminado logging de LASTFM_USERNAME en docker-entrypoint.sh

## 🎨 Mejoras Adicionales

### Sistema de Recomendaciones

1. **Eliminación de duplicados**: Sistema de 3 niveles
   - Entre recomendaciones de IA
   - Entre IA → ListenBrainz → Biblioteca
   - Filtrado final de seguridad

2. **Respeto al género solicitado**:
   - Conversión automática de `genre_filter` a `custom_prompt`
   - Prioridad absoluta de petición sobre perfil del usuario
   - Validación de razones (min 20 caracteres)

3. **Búsqueda de similares mejorada**:
   - **Estrategia 1**: ListenBrainz CF (collaborative filtering)
   - **Estrategia 2**: MusicBrainz búsqueda por tags/géneros similares
   - Filtrado de personas individuales (solo bandas/proyectos)
   - Logging detallado de cada estrategia

4. **Parseo mejorado**:
   - Validación de longitud de razones
   - Filtrado de líneas de análisis
   - Detección y skip de duplicados
   - Debug logging para troubleshooting

## 📊 Estadísticas

```
19 commits totales
13 archivos modificados  
1 archivo eliminado (lastfm_service.py)
+1,740 líneas agregadas
-976 líneas eliminadas
```

## ⚡ Optimizaciones de Rendimiento

### Cache Implementado

1. **Cache de artistas de biblioteca** (5 minutos)
   - Evita `get_artists(500)` en cada recomendación
   - **Mejora**: Primera llamada ~300ms, siguientes <1ms

2. **Cache de recomendaciones de ListenBrainz** (5 minutos)
   - Reutiliza CF recommendations entre peticiones
   - **Mejora**: ~200ms ahorrados por recomendación

### Límites Optimizados

| Parámetro | Antes | Ahora | Ahorro |
|-----------|-------|-------|--------|
| Artistas para analizar | 5 | 3 | ~40% |
| Similares por artista | 10 | 7 | ~30% |
| ListenBrainz CF count | 100 | 50 | ~50% |
| MusicBrainz búsquedas tags | 3 | 2 | ~33% |
| MusicBrainz resultados/tag | 20 | 15 | ~25% |
| IA max_output_tokens | 2048 | 800 | ~60% |
| Artistas en prompt IA | 50 | 30 | Menor |

### Tiempos Esperados

| Operación | Primera vez | Siguientes (cache) |
|-----------|-------------|-------------------|
| `/recommend` (sin filtros) | ~8-12s | **~3-5s** ✨ (NO usa IA) |
| `/recommend electrónica` | ~12-18s | **~5-8s** ✨ (usa IA) |
| `similar a X` (con tags) | ~5-7s | **~3-5s** ✨ |
| `similar a X` (sin tags, IA) | ~3-5s | **~3-5s** |
| Conversacional "algo nuevo" | ~10-15s | **~5-8s** ✨ (usa IA) |

### Configuración de IA Optimizada

```python
generation_config = {
    'temperature': 0.5-0.7,  # Más determinista
    'max_output_tokens': 300-800,  # Según uso
    'top_p': 0.8-0.9
}
```

## 🎯 Cambios Críticos del Sistema de Recomendaciones

### Orden de Prioridad Actualizado

**ANTES (malo)**:
1. Custom prompts (solo si el usuario especifica)
2. ListenBrainz CF (genérico, daba Metallica, The Temptations)
3. Biblioteca local

**AHORA (mejor)**:

Para `/recommend` sin filtros:
1. **ListenBrainz+MusicBrainz SOLO** (basado en historial real de escucha)
2. Artistas similares a los que escuchas activamente
3. Biblioteca local como último recurso
4. **NO usa IA** (más rápido, basado en datos reales)

Para `/recommend [género]` o peticiones específicas:
1. **IA primero** (entiende criterio específico)
2. ListenBrainz+MusicBrainz como complemento
3. Biblioteca local como último recurso

### Mejoras en Parseo de IA

- ✅ Pre-filtrado de líneas válidas antes de procesar
- ✅ Eliminación de numeración automática
- ✅ Validación estricta de formato ([ARTISTA] - [NOMBRE] | [RAZÓN])
- ✅ Skip de líneas de análisis/perfil
- ✅ Validación de longitud mínima de razones (20 chars)
- ✅ Logging detallado de líneas rechazadas

### Mejoras en Búsqueda de Similares

**Sistema de 3 estrategias** (en orden):

1. **ListenBrainz CF** (collaborative filtering)
   - Usa recomendaciones personalizadas basadas en usuarios similares
   - Agrupa por artista y ordena por score
   - Mejor para artistas populares con suficientes datos
   
2. **MusicBrainz Tags** (`find_similar_by_tags`)
   - Busca artistas globalmente con géneros/tags similares
   - Excluye personas individuales (solo bandas/proyectos)
   - Logging detallado de tags encontrados
   - Útil cuando ListenBrainz CF no tiene datos
   
3. **IA/Gemini** (conocimiento musical general) 🆕
   - Fallback cuando MusicBrainz no tiene tags/géneros
   - Usa conocimiento general de música de la IA
   - Genera artistas similares basándose en estilo/época/sonido
   - Crítico para artistas nicho sin metadata (ej: Mujeres, Albertucho, Sanguijuelas del Guadiana)
   - Siempre encuentra resultados si el artista es conocido

**Resultado**: 
- "similar a Mujeres" → Funciona aunque no tenga tags en MusicBrainz
- "similar a Oasis" → Da bandas (Blur, The Verve) no miembros (Liam Gallagher)
- "similar a cualquier artista" → Siempre encuentra algo gracias a las 3 estrategias

## 🚀 Instrucciones de Despliegue

### Para Desarrollo Local

```bash
# Cambiar a la rama
git checkout remove-lastfm-use-listenbrainz

# Reconstruir contenedor
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### Para Producción

```bash
# Mergear a main
git checkout main
git merge remove-lastfm-use-listenbrainz

# Push
git push origin main

# El CI/CD construirá automáticamente la nueva imagen
```

## ⚙️ Configuración Requerida

Actualiza tu archivo `.env`:

```env
# ELIMINAR estas líneas:
# LASTFM_API_KEY=...
# LASTFM_USERNAME=...

# ASEGURAR que tienes:
LISTENBRAINZ_USERNAME=tu_usuario
LISTENBRAINZ_TOKEN=tu_token  # Opcional pero recomendado
ENABLE_MUSICBRAINZ=true
```

## 🧪 Testing

Prueba estos casos después de desplegar:

1. **Recomendaciones generales** (basadas en historial):
   ```
   /recommend
   → Fuente: ListenBrainz+MusicBrainz (NO AI)
   → Artistas similares a los que escuchas (SFDK, Extremoduro, etc.)
   → Solo artistas que NO tienes en biblioteca
   → Más rápido (~8-12s primera vez, ~3-5s con cache)
   ```

2. **Recomendaciones por género** (usa IA):
   ```
   /recommend electrónica
   → Fuente: AI (Gemini) + ListenBrainz+MusicBrainz
   → Debería dar Daft Punk, Aphex Twin, etc. (NO hip-hop)
   → Razones completas sin fragmentos
   ```

3. **Búsqueda de similares con tags**:
   ```
   similar a Oasis
   → Estrategia 2: MusicBrainz tags (rock, britpop)
   → Debería dar Blur, The Verve, etc. (NO miembros de Oasis)
   ```

4. **Búsqueda de similares SIN tags** (artistas nicho):
   ```
   similar a Mujeres
   → Estrategia 3: IA fallback
   → Debería dar: Savages, The Courtneys, Parquet Courts, etc.
   ```

5. **Enlaces**:
   ```
   Verificar que digan "Ver en MusicBrainz" o "Ver en ListenBrainz"
   NO "Ver en Last.fm"
   ```

## 🐛 Problemas Conocidos y Soluciones

### Problema: "No encontré artistas similares a X"

**Causa**: ListenBrainz CF no tiene datos + MusicBrainz no tiene relaciones/tags

**Solución**: 
- Verificar que el artista existe en MusicBrainz
- Esperar a que ListenBrainz acumule más datos de ese artista
- Usar recomendaciones generales en su lugar

### Problema: Recomendaciones duplicadas

**Causa**: Múltiples fuentes pueden generar el mismo artista

**Solución**: Sistema de deduplicación implementado en 3 niveles

### Problema: Razones cortadas

**Causa**: La IA generaba análisis antes de las recomendaciones

**Solución**:
- Prompt mejorado pidiendo SOLO recomendaciones
- Filtrado de líneas que no son recomendaciones
- Validación de longitud mínima

## 📝 Notas de Compatibilidad

- **`ScrobbleTrack` y `ScrobbleArtist`**: Anteriormente `LastFMTrack` y `LastFMArtist`, ahora renombrados para reflejar su uso con servicios de scrobbling open-source (ListenBrainz)
- **Campo `source`**: Ahora puede ser "ListenBrainz", "MusicBrainz", "ListenBrainz+MusicBrainz", "AI (Gemini)", "Navidrome"
- **Keys en respuestas**: `musicbrainz_artist_info` (anteriormente `lastfm_artist_info`)

## 🔗 Referencias

- [ListenBrainz API](https://listenbrainz.readthedocs.io/)
- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)
- [Documentación del Proyecto](README.md)

---

**Fecha de migración**: 19 de Octubre, 2025  
**Versión**: 3.1.0 (post-migración)  
**Status**: ✅ Completa y funcional

### Limpieza Final - 19 de Octubre, 2025

✅ **Eliminadas todas las referencias a Last.fm del código:**
- Renombrados modelos `LastFMTrack` → `ScrobbleTrack` y `LastFMArtist` → `ScrobbleArtist`
- Renombrado key `lastfm_artist_info` → `musicbrainz_artist_info`
- Eliminado logging de `LASTFM_USERNAME` en docker-entrypoint.sh
- Actualizados todos los imports y referencias en los servicios
- **Stack 100% open-source**: ListenBrainz + MusicBrainz + Navidrome

El repositorio ya no contiene ninguna referencia a Last.fm en el código funcional (solo en documentación histórica como CHANGELOG.md y MIGRATION.md).

