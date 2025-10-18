# 🎵 Feature: Comando /releases

## Descripción

Nueva funcionalidad que permite ver los lanzamientos recientes (álbumes y EPs) de los artistas que tienes en tu biblioteca de Navidrome.

## ¿Cómo funciona?

El comando utiliza una estrategia eficiente de búsqueda:

1. **Búsqueda global en MusicBrainz**: Obtiene TODOS los lanzamientos recientes del período especificado (ej: último mes) con una sola consulta optimizada usando la API de búsqueda de MusicBrainz
2. **Obtención de artistas locales**: Lee todos los artistas de tu biblioteca Navidrome
3. **Matching inteligente**: Compara los releases con tus artistas usando normalización de texto (maneja "The Beatles" vs "Beatles", acentos, mayúsculas, etc.)

### Ventajas de este enfoque

- ⚡ **Rápido**: 1-3 requests a MusicBrainz vs 500+ si consultáramos artista por artista
- 🎯 **Eficiente**: ~3-5 segundos vs 8+ minutos del enfoque tradicional
- 🔄 **Sin rate limiting**: Solo hace unas pocas llamadas a la API
- 📊 **Completo**: Verifica hasta 500 releases globales contra tu biblioteca

## Uso

### Comandos disponibles

```bash
/releases              # Lanzamientos del último mes (30 días)
/releases 7            # Lanzamientos de la última semana
/releases 60           # Lanzamientos de los últimos 60 días
/releases 90           # Lanzamientos de los últimos 3 meses
```

### Ejemplo de respuesta

```
🎵 Lanzamientos recientes (30 días)

✅ Encontrados 5 lanzamientos de artistas en tu biblioteca
📊 Total verificado: 287 releases globales

🎤 King Gizzard & The Lizard Wizard
   📀 Flight b741 (Album)
      📅 2024-08-09
      🔗 Ver en MusicBrainz

🎤 Fontaines D.C.
   📀 Romance (Album)
      📅 2024-08-23
      🔗 Ver en MusicBrainz

🎤 The Smile
   💿 Wall of Eyes (EP)
      📅 2024-01-26
      🔗 Ver en MusicBrainz

💡 Usa /releases <días> para cambiar el rango (ej: /releases 7 para última semana)
```

## Requisitos

- **MusicBrainz habilitado**: Debe estar configurado `ENABLE_MUSICBRAINZ=true` en tu `.env`
- **Navidrome funcionando**: Para obtener los artistas de tu biblioteca
- **Conexión a internet**: Para consultar la API de MusicBrainz

## Archivos modificados

### Nuevos métodos en `MusicBrainzService`

1. **`get_all_recent_releases(days)`**: Obtiene todos los releases del período usando búsqueda Lucene
   - Query: `firstreleasedate:[YYYY-MM-DD TO YYYY-MM-DD] AND status:official AND (type:album OR type:ep)`
   - Paginación automática (hasta 500 releases)
   - Rate limiting incorporado (1 req/seg)

2. **`match_releases_with_library(releases, artists)`**: Compara releases con artistas
   - Normalización de texto (elimina acentos, "The", mayúsculas, etc.)
   - Matching eficiente usando sets de Python
   - Devuelve solo los releases que coinciden

### Nuevo comando en `TelegramService`

- **`releases_command()`**: Handler del comando `/releases`
  - Parsea argumentos (número de días)
  - Coordina la búsqueda y matching
  - Formatea la respuesta agrupada por artista
  - Maneja errores y casos límite

### Registro del comando

- Añadido en `bot.py` como `CommandHandler("releases", ...)`
- Documentado en mensajes de `/help` y `/start`

## Detalles técnicos

### Normalización de nombres

La función de matching normaliza nombres de artistas para manejar variaciones:

```python
"The Beatles" → "beatles"
"Café Tacvba" → "cafe tacvba"
"MGMT" → "mgmt"
"Pink Floyd" → "pink floyd"
```

### Límites y restricciones

- **Máximo de días**: 1-365 días
- **Releases mostrados**: Primeros 20 (para no saturar el mensaje)
- **Releases verificados**: Hasta 500 por consulta (límite de seguridad)
- **Rate limit**: 1 request/segundo a MusicBrainz

### Query de MusicBrainz

La query Lucene utilizada es:

```
firstreleasedate:[2024-09-18 TO 2024-10-18] 
AND status:official 
AND (type:album OR type:ep)
```

Esto filtra:
- **firstreleasedate**: Por rango de fechas
- **status:official**: Solo lanzamientos oficiales (no bootlegs)
- **type**: Solo álbumes y EPs (no singles, compilaciones, etc.)

## Mejoras futuras posibles

1. **Cache de 24h**: Cachear resultados para evitar consultas repetidas
2. **Notificaciones**: Sistema de notificaciones automáticas de nuevos releases
3. **Filtros adicionales**: Por país, género, tipo de release
4. **Integración con Last.fm**: Complementar con datos de popularidad
5. **Descarga automática**: Integración con sistemas de descarga

## Testing

Para probar la funcionalidad:

```bash
# En tu bot de Telegram
/releases          # Ver lanzamientos del mes
/releases 7        # Ver lanzamientos de la semana
/releases 90       # Ver lanzamientos del trimestre
```

Verifica que:
- ✅ Se muestren releases de artistas en tu biblioteca
- ✅ No se muestren artistas que no tienes
- ✅ Las fechas estén dentro del rango solicitado
- ✅ Los enlaces a MusicBrainz funcionen
- ✅ El matching maneje variaciones de nombres

## Comparación con enfoque tradicional

| Métrica | Enfoque anterior | Nuevo enfoque |
|---------|------------------|---------------|
| **Requests a API** | 500+ (uno por artista) | 1-3 (búsqueda global) |
| **Tiempo total** | 8+ minutos | 3-5 segundos |
| **Rate limiting** | Problemático | Sin problemas |
| **Escalabilidad** | Mala | Excelente |
| **Precisión** | Alta | Alta |

## Créditos

- **MusicBrainz**: Base de datos de música open source
- **Lucene Query Syntax**: Para búsquedas avanzadas
- **Python asyncio**: Para operaciones asíncronas eficientes

