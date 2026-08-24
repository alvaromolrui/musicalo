# Índice de decisiones

Registro histórico del **por qué** de cada decisión de diseño importante de Musicalo — contexto, opciones consideradas y consecuencias. No es documentación del estado actual (eso vive en [arquitectura.md](../arquitectura.md)) ni una bitácora de sesión: una entrada de aquí se cierra cuando el cambio está aplicado y se conserva tal cual, no se sigue editando como si fuera viva.

Estas primeras entradas se han reconstruido a partir de commits grandes de refactor ya aplicados (no había carpeta `decisiones/` antes de esta sesión) — el detalle completo de cada una sigue viviendo en el commit citado, no se duplica aquí.

| Tema | Estado | Resumen |
|---|---|---|
| Agente único con function calling sustituye al clasificador de intents | ✅ Aplicado ([`cdeab96`](https://github.com/alvaromolrui/musicalo/commit/cdeab96)) | Sustituido el pipeline de intent-detection + prompts por categoría + plantillas Python por un único agente conversacional (Gemini, SDK `google-genai`) con *tool-calling*: el modelo decide qué herramientas llamar y redacta la respuesta él mismo. Eliminadas ~950 líneas de heurística de extracción de canciones para playlists. Ver [arquitectura.md](../arquitectura.md#componentes). |
| Koito como fuente de historial de escucha, con prioridad sobre ListenBrainz | ✅ Aplicado (mismo commit `cdeab96`) | Nuevo `KoitoService`, misma interfaz pública que `ListenBrainzService`. Elegido en runtime: si `KOITO_URL` está configurado tiene prioridad; si no, se usa `LISTENBRAINZ_USERNAME`. Motivo (ver README): Koito es auto-hospedado (control total de los datos), a costa de no tener recomendaciones colaborativas al ser de un solo usuario — MusicBrainz/IA cubre ese hueco. |
| `actualizar_playlist` en vez de duplicar al refinar una playlist | ✅ Aplicado ([`53040ab`](https://github.com/alvaromolrui/musicalo/commit/53040ab), reforzado en [`6d23e17`](https://github.com/alvaromolrui/musicalo/commit/6d23e17)) | La sesión de conversación guarda la playlist activa (`last_playlist`); un refinamiento posterior debe llamar a `actualizar_playlist` sobre ella en vez de crear una nueva. Ver fila correspondiente en [errores-conocidos.md](../errores-conocidos.md). |
| Playlists desde setlist.fm | ✅ Aplicado ([`c71af6b`](https://github.com/alvaromolrui/musicalo/commit/c71af6b)) | Nuevo `SetlistfmService`: pegar un enlace de setlist.fm o pedirlo en lenguaje natural (artista/ciudad/fecha) busca las canciones del concierto real en la biblioteca con *fuzzy matching* y crea la playlist en Navidrome. |
| Migración pendiente de `google-generativeai` a `google-genai` | 🟡 Parcial — deuda técnica aceptada | El agente (`music_agent_service.py`) ya usa el SDK nuevo `google-genai`; `ai_service.py`, `enhanced_intent_detector.py` e `intent_detector.py` siguen en el SDK antiguo (`google-generativeai`, EOL 30-nov-2025). Migrarlos se documenta como "un pase aparte" en [requirements.txt](../requirements.txt) — no hay fecha objetivo fijada. |

## Plantilla para una decisión nueva

1. Si el cambio es grande o tiene varias fases, crea `decisiones/<tema-en-kebab-case>/` con su propio documento; si es una decisión puntual y ya está aplicada, una fila en la tabla de arriba con enlace al commit puede bastar — no fuerces una carpeta para todo.
2. Documento principal (si lo hay) con esta forma mínima:
   - **Contexto**: qué problema o disparador motivó la decisión (fecha explícita, `AAAA-MM-DD`).
   - **Opciones consideradas**: qué alternativas se evaluaron y por qué se descartaron las no elegidas.
   - **Decisión**: qué se eligió.
   - **Consecuencias**: qué cambia en [arquitectura.md](../arquitectura.md)/[glosario.md](../glosario.md) como resultado.
3. Al completarse: añade o actualiza la fila en la tabla de arriba, y actualiza [arquitectura.md](../arquitectura.md) si el estado actual del sistema cambió — no sigas editando la entrada de aquí como si fuera documentación viva.
