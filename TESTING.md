# 🧪 Guía de Pruebas - Musicalo Agente Musical

## Rama: `feature/music-agent-improvements`

Esta guía te ayudará a probar las nuevas funcionalidades implementadas.

---

## 📋 Preparación

### 1. Cambiar a la rama
```bash
git checkout feature/music-agent-improvements
```

### 2. Verificar configuración
Asegúrate de que tu archivo `.env` tenga configurado:
```env
# Obligatorio
GEMINI_API_KEY=tu_clave_de_gemini
TELEGRAM_BOT_TOKEN=tu_token_de_telegram

# Recomendado (al menos uno)
LASTFM_API_KEY=tu_clave_lastfm
LASTFM_USERNAME=tu_usuario_lastfm

# O alternativamente
LISTENBRAINZ_USERNAME=tu_usuario_listenbrainz

# Biblioteca
NAVIDROME_URL=http://tu-instancia-navidrome:4533
NAVIDROME_USERNAME=admin
NAVIDROME_PASSWORD=password
```

### 3. Reiniciar el bot
```bash
# Si usas Docker
docker-compose down
docker-compose up -d --build

# Si ejecutas directamente
python backend/bot.py
```

---

## ✅ Tests Funcionales

### Test 1: Comando /playlist (básico)

**Comando:**
```
/playlist
```

**Resultado esperado:**
```
🎵 Crear Playlist

Uso: /playlist <descripción>

Ejemplos:
• /playlist rock progresivo de los 70s
• /playlist música energética para correr
• /playlist jazz suave
• /playlist similar a Pink Floyd
• /playlist 10 canciones de metal melódico
```

---

### Test 2: Crear playlist simple

**Comando:**
```
/playlist rock de los 80s
```

**Resultado esperado:**
1. Mensaje: "🎵 Creando playlist: _rock de los 80s_..."
2. El bot genera una playlist
3. Recibes un archivo `.m3u` descargable
4. El mensaje incluye:
   - Nombre de la playlist
   - Descripción
   - Lista de las primeras 10 canciones
   - Enlaces a Last.fm (si están disponibles)

**Verificación del archivo M3U:**
- Descarga el archivo
- Ábrelo con un editor de texto
- Debe empezar con `#EXTM3U`
- Debe tener entradas `#EXTINF` con información de canciones
- Debe tener URLs a tu servidor Navidrome

---

### Test 3: Crear playlist compleja

**Comando:**
```
/playlist rock progresivo de los 70s con sintetizadores
```

**Resultado esperado:**
- Playlist más específica y curada
- Canciones que coincidan con los criterios múltiples
- ~15 canciones en total

---

### Test 4: Crear playlist por actividad

**Comando:**
```
/playlist música energética para hacer ejercicio
```

**Resultado esperado:**
- Canciones con tempo rápido y energía alta
- Basadas en tus gustos personales

---

### Test 5: Comando /info (básico)

**Comando:**
```
/info
```

**Resultado esperado:**
```
ℹ️ Información Musical

Uso: /info <artista/álbum/canción>

Ejemplos:
• /info Pink Floyd
• /info Dark Side of the Moon
• /info Queen Bohemian Rhapsody
```

---

### Test 6: Información de artista

**Comando:**
```
/info Pink Floyd
```
*(Usa un artista que tengas en tu biblioteca)*

**Resultado esperado:**
1. Mensaje: "🔍 Buscando información sobre: _Pink Floyd_..."
2. Respuesta detallada con:
   - Información del artista
   - Álbumes en tu biblioteca (si los tienes)
   - Estadísticas de escucha (si usas Last.fm)
   - Enlaces a Last.fm
   - Artistas similares (posiblemente)

---

### Test 7: Información de álbum

**Comando:**
```
/info The Dark Side of the Moon
```

**Resultado esperado:**
- Información sobre el álbum
- Si está en tu biblioteca, detalles locales
- Enlaces relacionados

---

### Test 8: Consulta compleja al agente

**Comando:**
```
/info ¿Qué álbumes de Queen tengo en mi biblioteca?
```

**Resultado esperado:**
- Lista de álbumes de Queen que tienes
- Información detallada de cada uno
- Enlaces a Last.fm

---

### Test 9: Integración con comandos existentes

**Verificar que los comandos anteriores sigan funcionando:**

```
/start     ✓ Debe mostrar mensaje actualizado con nuevos comandos
/help      ✓ Debe incluir /playlist e /info
/recommend ✓ Debe funcionar igual que antes
/stats     ✓ Sin cambios
/search    ✓ Sin cambios
/ask       ✓ Sin cambios
```

---

## 🔍 Verificaciones Técnicas

### 1. Verificar logs del bot

```bash
# Docker
docker-compose logs -f backend

# Directo
# Ver la salida del terminal donde corre el bot
```

**Buscar mensajes como:**
```
✅ Agente musical: Last.fm habilitado
✅ Usando Last.fm para datos de escucha
🎵 Generando playlist con: rock de los 80s
🤖 Agente musical procesando: ...
✅ Playlist guardada en: /tmp/...
```

### 2. Verificar estructura del archivo M3U

Descarga una playlist generada y verifica:

```m3u
#EXTM3U
#PLAYLIST:Musicalo - rock de los 80s
#EXTENC:UTF-8
#DESCRIPTION:rock de los 80s
#EXTINF:243,Artista - Canción
http://tu-navidrome:4533/rest/stream.view?id=...&u=admin
```

### 3. Verificar imports

Abre una consola Python y verifica:

```python
from backend.services.playlist_service import PlaylistService
from backend.services.music_agent_service import MusicAgentService

# No debe dar errores de import
```

---

## 🐛 Casos de Error Esperados

### Error 1: Sin servicio de scrobbling

**Comando:** `/playlist rock`

**Sin Last.fm ni ListenBrainz configurado:**
```
⚠️ Necesitas configurar Last.fm o ListenBrainz para crear playlists.
```

**Solución:** Configurar al menos uno en `.env`

---

### Error 2: Sin datos del usuario

**Si no tienes historial de escucha:**
```
😔 No pude generar playlist con esos criterios.
```

**Solución:** 
- Asegúrate de tener scrobbles en Last.fm
- O usa el comando `/recommend` primero para verificar conexión

---

### Error 3: Gemini API no configurada

```
❌ Error creando playlist: [error de API]
```

**Solución:** Verifica `GEMINI_API_KEY` en `.env`

---

## 📊 Checklist de Pruebas

Marca cada prueba completada:

**Funcionalidad Básica:**
- [ ] `/playlist` muestra ayuda
- [ ] `/info` muestra ayuda
- [ ] `/playlist <algo>` genera archivo M3U
- [ ] `/info <algo>` muestra información

**Generación de Playlists:**
- [ ] Playlist simple (género)
- [ ] Playlist compleja (múltiples criterios)
- [ ] Playlist por actividad
- [ ] Archivo M3U se puede descargar
- [ ] Archivo M3U tiene formato correcto

**Agente Musical:**
- [ ] Consulta de artista funciona
- [ ] Consulta de álbum funciona
- [ ] Muestra datos de biblioteca local
- [ ] Muestra datos de Last.fm
- [ ] Incluye enlaces relevantes

**Integración:**
- [ ] Comandos anteriores funcionan
- [ ] `/start` actualizado
- [ ] `/help` actualizado
- [ ] Sin errores en logs
- [ ] Sin errores de linter

**Calidad de Respuestas:**
- [ ] Las playlists son relevantes
- [ ] La información es precisa
- [ ] Los enlaces funcionan
- [ ] Las respuestas están bien formateadas

---

## 🎯 Pruebas Avanzadas

### Test de Playlist Larga
```
/playlist 20 canciones de jazz suave
```
Verifica que genere ~20 canciones.

### Test de Consulta Compleja
```
/info Dame una comparación entre Pink Floyd y Radiohead
```
Verifica que el agente responda de forma inteligente.

### Test de Artista No en Biblioteca
```
/info Taylor Swift
```
*(Si no la tienes en tu biblioteca)*
Verifica que use solo datos de Last.fm.

### Test de Playlist Similar
```
/playlist similar a The Beatles pero más moderno
```
Verifica que entienda el concepto y genere apropiadamente.

---

## 📈 Métricas de Éxito

Una implementación exitosa debe cumplir:

✅ **Funcionalidad:**
- Todos los comandos nuevos funcionan
- Generación de playlists exitosa en >90% de casos
- Agente responde coherentemente

✅ **Calidad:**
- Las playlists son relevantes a la descripción
- La información es precisa
- Los enlaces funcionan

✅ **Rendimiento:**
- Generación de playlist < 10 segundos
- Respuesta del agente < 5 segundos
- Sin errores de timeout

✅ **Usabilidad:**
- Mensajes de ayuda claros
- Errores informativos
- Formato agradable

---

## 🚀 Siguientes Pasos

Si todas las pruebas pasan:

1. **Documentar cualquier issue encontrado**
2. **Hacer ajustes necesarios**
3. **Preparar merge a main:**
   ```bash
   git checkout main
   git merge feature/music-agent-improvements
   ```
4. **Actualizar README.md principal**
5. **Actualizar CHANGELOG.md**
6. **Desplegar en producción**

---

## 📝 Reporte de Pruebas

Usa este template para reportar:

```
## Prueba: [Nombre]
Fecha: [DD/MM/YYYY]
Tester: [Tu nombre]

### Resultado: ✅ / ❌

**Comando ejecutado:**
```
[comando]
```

**Salida esperada:**
[descripción]

**Salida real:**
[descripción]

**Notas:**
[cualquier observación]

**Screenshot:**
[opcional]
```

---

## 💡 Tips de Depuración

Si algo no funciona:

1. **Verifica logs:** `docker-compose logs -f backend`
2. **Verifica imports:** Asegúrate de que los nuevos archivos se crearon
3. **Verifica .env:** Todas las claves API configuradas
4. **Reinicia el bot:** `docker-compose restart backend`
5. **Verifica conexión:** Prueba `/stats` primero

---

¡Buena suerte con las pruebas! 🎵🤖

