# Integración Combinada: ListenBrainz + Last.fm

## 📊 Resumen de la Estrategia

Este proyecto ahora utiliza **ambas APIs de forma complementaria**, aprovechando las fortalezas de cada una:

### **ListenBrainz** (Servicio de Historial)
Priorizado para todo lo relacionado con el historial personal del usuario:
- ✅ Historial de escuchas recientes
- ✅ Estadísticas del usuario
- ✅ Top artistas personales
- ✅ Top canciones personales
- ✅ Actividad de escucha por día

**Ventajas:**
- Sin límites de tasa de API
- Historial completo y detallado
- Mayor privacidad (open source)
- Datos más precisos del historial personal

### **Last.fm** (Servicio de Descubrimiento)
Utilizado para recomendaciones y metadatos globales:
- ✅ Artistas similares
- ✅ Canciones similares
- ✅ Top álbumes de artistas (popularidad global)
- ✅ Top canciones de artistas (popularidad global)
- ✅ Metadatos enriquecidos (imágenes, URLs)

**Ventajas:**
- Mejor algoritmo de similitud
- Base de datos más grande de relaciones entre artistas
- Información de popularidad global
- Metadatos más completos

## 🔧 Implementación Técnica

### Servicios Definidos

```python
# En MusicAgentService.__init__()

# HISTORIAL: Priorizar ListenBrainz (más datos, sin límites de API)
self.history_service = self.listenbrainz or self.lastfm
self.history_service_name = "ListenBrainz" if self.listenbrainz else "Last.fm"

# RECOMENDACIONES Y METADATOS: Solo Last.fm
self.discovery_service = self.lastfm
```

### Flujo de Datos

```
┌─────────────────────────────────────────────────┐
│           CONSULTA DEL USUARIO                  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │  ¿Qué tipo de consulta es?  │
    └─────────────┬───────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│  HISTORIAL   │      │  DESCUBRIMIENTO  │
├──────────────┤      ├──────────────────┤
│ ListenBrainz │      │    Last.fm       │
│  (preferido) │      │   (exclusivo)    │
│      o       │      │                  │
│   Last.fm    │      └──────────────────┘
└──────────────┘
      │                       │
      └───────────┬───────────┘
                  ▼
        ┌──────────────────┐
        │  RESPUESTA AL    │
        │     USUARIO      │
        └──────────────────┘
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Consulta de Historial
**Pregunta:** "¿Qué he escuchado últimamente?"

```python
# Usa history_service (ListenBrainz si está disponible)
recent_tracks = await self.history_service.get_recent_tracks(limit=20)
```

**Fuente de datos:** ListenBrainz → más completo, sin límites

---

### Ejemplo 2: Búsqueda de Similares
**Pregunta:** "¿Qué artistas son parecidos a Radiohead?"

```python
# Usa discovery_service (siempre Last.fm)
similar = await self.discovery_service.get_similar_artists("Radiohead", limit=5)
```

**Fuente de datos:** Last.fm → mejor algoritmo de similitud

---

### Ejemplo 3: Descubrimiento Híbrido
**Pregunta:** "Recomiéndame algo nuevo"

```python
# 1. Obtener gustos del usuario (ListenBrainz)
top_artists = await self.history_service.get_top_artists(limit=5)

# 2. Buscar artistas similares (Last.fm)
for artist in top_artists:
    similar = await self.discovery_service.get_similar_artists(artist.name)
    top_albums = await self.discovery_service.get_artist_top_albums(artist.name)
```

**Fuente de datos:** Combinación de ambas APIs

---

### Ejemplo 4: "Mejor Disco de un Artista"
**Pregunta:** "¿Cuál es el mejor disco de Pink Floyd?"

```python
# 1. Buscar en biblioteca local (Navidrome)
library_results = await self.navidrome.search("Pink Floyd")

# 2. Obtener popularidad global (Last.fm)
top_albums = await self.discovery_service.get_artist_top_albums("Pink Floyd")

# 3. Combinar ambas fuentes en la respuesta
```

**Fuente de datos:** Navidrome + Last.fm

## ⚙️ Configuración

### Variables de Entorno Necesarias

```env
# Para historial completo (RECOMENDADO)
LISTENBRAINZ_USERNAME=tu_usuario_listenbrainz
LISTENBRAINZ_TOKEN=tu_token_opcional

# Para recomendaciones y descubrimiento (RECOMENDADO)
LASTFM_API_KEY=tu_api_key_lastfm
LASTFM_USERNAME=tu_usuario_lastfm
```

### Escenarios de Configuración

| ListenBrainz | Last.fm | Resultado |
|--------------|---------|-----------|
| ✅ | ✅ | **Óptimo:** Historial de LB + Descubrimiento de LFM |
| ✅ | ❌ | Historial de LB, sin recomendaciones |
| ❌ | ✅ | Historial y descubrimiento de LFM |
| ❌ | ❌ | Solo biblioteca local (sin scrobbling) |

## 🎯 Beneficios de esta Arquitectura

1. **Mejor rendimiento**: ListenBrainz no tiene límites de API
2. **Datos completos**: Todo el historial disponible sin restricciones
3. **Mejores recomendaciones**: Algoritmos de Last.fm más maduros
4. **Redundancia**: Si uno falla, el otro responde
5. **Complementariedad**: Cada API hace lo que mejor sabe
6. **Flexibilidad**: Funciona con una o ambas APIs

## 🔄 Migración desde el Sistema Anterior

### Antes (sistema único)
```python
# Usaba solo un servicio
self.music_service = self.lastfm or self.listenbrainz
```

### Ahora (sistema híbrido)
```python
# Separa responsabilidades
self.history_service = self.listenbrainz or self.lastfm
self.discovery_service = self.lastfm
```

## 📊 Comparativa de Endpoints

| Funcionalidad | ListenBrainz | Last.fm | Uso Recomendado |
|---------------|--------------|---------|-----------------|
| Escuchas recientes | ✅ (ilimitado) | ✅ (limitado) | **ListenBrainz** |
| Top artistas | ✅ (calculado) | ✅ (nativo) | **ListenBrainz** |
| Top canciones | ✅ (calculado) | ✅ (nativo) | **ListenBrainz** |
| Estadísticas usuario | ✅ | ✅ | **ListenBrainz** |
| Artistas similares | ❌ | ✅ | **Last.fm** |
| Canciones similares | ❌ | ✅ | **Last.fm** |
| Top álbumes artista | ❌ | ✅ | **Last.fm** |
| Top tracks artista | ❌ | ✅ | **Last.fm** |
| Metadatos (imágenes) | ⚠️ (limitado) | ✅ | **Last.fm** |

## 🚀 Próximas Mejoras Posibles

- [ ] Cache de resultados de Last.fm para reducir llamadas
- [ ] Endpoint de ListenBrainz para recomendaciones propias
- [ ] Sincronización bidireccional entre ambos servicios
- [ ] Métricas de uso de cada API
- [ ] Fallback automático si un servicio falla

## 📚 Referencias

- [ListenBrainz API Documentation](https://listenbrainz.readthedocs.io/en/latest/dev/api/)
- [Last.fm API Documentation](https://www.last.fm/api)
- [MusicBrainz Database](https://musicbrainz.org/)

---

**Fecha de implementación:** 2025-10-17  
**Versión:** 1.0

