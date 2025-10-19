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

- **models/schemas.py**:
  - Mantenidos `LastFMTrack` y `LastFMArtist` por compatibilidad
  - Agregada documentación explicando que ahora se usan con ListenBrainz/MusicBrainz

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

- **docker-compose.yml**:
  - Cambiado a build local (para desarrollo)
  - Eliminadas variables de entorno de Last.fm

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
9 commits totales
8 archivos modificados
1 archivo eliminado
~1100 líneas agregadas
~800 líneas eliminadas
```

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

1. **Recomendaciones por género**:
   ```
   /recommend electrónica
   → Debería dar Daft Punk, Aphex Twin, etc. (NO hip-hop)
   ```

2. **Búsqueda de similares**:
   ```
   similar a Oasis
   → Debería dar Blur, The Verve, etc. (NO miembros de Oasis)
   ```

3. **Búsqueda de similares para artistas nicho**:
   ```
   similar a Mujeres
   → Debería encontrar artistas con tags similares si existen
   ```

4. **Recomendaciones generales**:
   ```
   /recommend
   → NO debería repetir el mismo artista 3 veces
   → Razones deberían estar completas (no cortadas)
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

- **`LastFMTrack` y `LastFMArtist`**: Mantenidos por compatibilidad, pero ahora se usan con datos de ListenBrainz/MusicBrainz
- **Campo `source`**: Ahora puede ser "ListenBrainz", "MusicBrainz", "ListenBrainz+MusicBrainz", "AI (Gemini)", "Navidrome"

## 🔗 Referencias

- [ListenBrainz API](https://listenbrainz.readthedocs.io/)
- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)
- [Documentación del Proyecto](README.md)

---

**Fecha de migración**: 19 de Octubre, 2025  
**Versión**: 3.1.0 (post-migración)  
**Status**: ✅ Completa y funcional

