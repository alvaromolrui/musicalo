# Glosario

Términos y nombres propios de Musicalo que aparecen sin definir en el código, el README o los commits — para que una sesión nueva no tenga que reconstruir el significado leyendo varios ficheros a la vez. Convenciones de *forma* (nombrado, estilo de commits) van en [convenciones.md](convenciones.md), no aquí.

## Servicios externos que integra Musicalo

| Término | Significado |
|---|---|
| **Navidrome** | Servidor de música autoalojado (compatible Subsonic) que aloja la biblioteca real del usuario. Musicalo lo consulta y también **crea/actualiza playlists reales** en él — no es solo lectura. Cliente: [backend/services/navidrome_service.py](backend/services/navidrome_service.py). |
| **Koito** | Scrobbler de historial de escucha, auto-hospedado, compatible con la API de ListenBrainz. Tiene **prioridad** sobre ListenBrainz si `KOITO_URL` está configurado — ver `MusicAssistant.__init__` en [backend/core/music_assistant.py](backend/core/music_assistant.py). Al ser de un solo usuario no tiene recomendaciones colaborativas (no hay otros usuarios con quien comparar). |
| **ListenBrainz** | Alternativa a Koito para historial de escucha, servicio compartido open-source (no auto-hospedado). Se usa solo si `KOITO_URL` no está configurado. Tiene recomendaciones colaborativas (sí hay otros usuarios). |
| **MusicBrainz** | Base de datos de metadatos musicales open-source (géneros, relaciones entre artistas, lanzamientos). Sin API key, solo requiere `CONTACT_EMAIL`/`APP_NAME` por sus políticas de uso. Cliente: `MusicBrainzService`, accesible desde el agente como `self.agent.musicbrainz`. |
| **setlist.fm** | Servicio de setlists de conciertos reales. Musicalo lo usa para crear una playlist en Navidrome a partir de un concierto (por enlace o por artista/ciudad/fecha) emparejando canción a canción contra la biblioteca. Cliente: `SetlistfmService` ([backend/services/setlistfm_service.py](backend/services/setlistfm_service.py)). |
| **ntfy** | Servicio de notificaciones push (auto-hospedable o `ntfy.sh`) usado para avisar de lanzamientos nuevos. Opcional — sin `NTFY_TOPIC` esa vía queda inactiva sin afectar al resto de la app. |
| **Gemini** | Modelo de IA de Google (SDK `google-genai`) que ejecuta el bucle de *function calling* del agente conversacional. No confundir con el SDK anterior `google-generativeai` (ver más abajo). |

## Conceptos propios del código

| Término | Significado |
|---|---|
| **`MusicAssistant`** | Orquestador central agnóstico de UI ([backend/core/music_assistant.py](backend/core/music_assistant.py)). No importa nada de Telegram ni de ningún framework web — cualquier adaptador de interfaz (bot, API) lo consume igual. |
| **`MusicAgentService` / "el agente"** | El motor de *function calling* sobre Gemini que decide qué herramientas llamar y redacta la respuesta con su propia voz — es el "un único agente conversacional" que menciona el README, no un componente aparte del backend. Ver [arquitectura.md](arquitectura.md). |
| **Tool / herramienta** | Cada función que el agente puede invocar (`buscar_biblioteca`, `crear_playlist`, `ver_playlist_actual`...). Tabla completa en el [README](README.md#-un-agente-con-herramientas-no-un-árbol-de-decisiones). |
| **`ConversationSession` / "sesión"** | Estado de una conversación (historial de turnos, playlist activa, últimas recomendaciones) guardado en memoria del proceso backend, indexado por `user_id`. No confundir con el historial de Chainlit (persistente en SQLite) — son dos cosas distintas, ver [arquitectura.md](arquitectura.md#dónde-vive-el-estado--y-el-punto-de-duplicación-a-tener-en-cuenta). |
| **`last_playlist` / "playlist activa"** | Referencia (`{id, name}`) a la última playlist creada en la conversación actual, guardada en `ConversationSession`. Permite que un refinamiento posterior (`actualizar_playlist`) modifique esa playlist en vez de crear una duplicada. |
| **`resolve_uid()`** | Función centralizada ([backend/api/user_id.py](backend/api/user_id.py)) que convierte el identificador de usuario (string, típicamente `thread_id` de Chainlit) al entero que usa `ConversationManager` — vía `md5`, estable entre reinicios del contenedor (a diferencia del `hash()` de Python que sustituyó, salteado por proceso). |
| **`START_MODE`** | Variable de entorno que decide qué arranca el proceso backend: `telegram` (default), `api`, o `both`. Ver [start-bot.py](start-bot.py). |
| **`AssistantResponse`** | Tipo de retorno común de los métodos de `MusicAssistant` — cada adaptador de UI (bot, API) lo traduce a su formato nativo. |

## Herramientas propias / scripts

| Término | Significado |
|---|---|
| **`start-bot.py`** | Punto de entrada real del contenedor — no `backend/bot.py` directamente. Lee `START_MODE` y decide si arranca el bot, la API, o ambas en el mismo *event loop*. |
| **`docker-entrypoint.sh`** | Script de arranque del contenedor Docker (previo a `start-bot.py`) — revisar aquí antes de asumir cómo arranca el proceso en producción. |

## Cómo añadir un término

Cuando documentes algo y uses un nombre propio, sigla o concepto interno que no se explica por sí solo, añade la fila aquí en la misma sesión en la que aparece — no lo dejes para más adelante.
