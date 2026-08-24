# Musicalo — contexto para Claude Code

Musicalo es un asistente musical con IA que combina un bot de Telegram y una interfaz web (Chainlit), sobre un backend FastAPI en Python. Un único agente conversacional (Gemini con *function calling*) decide qué consultar — biblioteca en Navidrome, historial de escucha en Koito/ListenBrainz, metadatos en MusicBrainz — y redacta la respuesta con su propia voz, sin plantillas fijas. Detalle funcional completo en el [README](README.md).

## Estructura del repo

Más allá del código, el repo mantiene seis tipos de conocimiento en documentos propios — consúltalos antes de asumir que algo no está ya resuelto en otro sitio:

- **Arquitectura** — [arquitectura.md](arquitectura.md): componentes reales del backend/frontend, cómo se comunican, dónde vive el estado (incluye el punto de duplicación entre la memoria del agente y el historial de Chainlit) y la topología de despliegue.
- **Convenciones** — [convenciones.md](convenciones.md): formato de commits (`Fix:`/`Feat:`/`Docs:`), versionado, estilo de código, y el aviso de que el `CHANGELOG.md` está desactualizado.
- **Decisiones** — [decisiones/README.md](decisiones/README.md): índice del *por qué* de los cambios de diseño importantes (agente único con function calling, Koito como fuente de escucha...), no el estado actual.
- **Glosario** — [glosario.md](glosario.md): servicios externos (Navidrome, Koito, MusicBrainz, setlist.fm...) y conceptos propios del código (`MusicAssistant`, sesión, playlist activa...).
- **Flujo de trabajo** — [flujo-de-trabajo.md](flujo-de-trabajo.md): qué fichero tocar según lo que encuentres en sesión, y el ciclo real de publicación (commits a `main` → build condicional de imágenes Docker → tag `vX.Y.Z` para release).
- **Errores conocidos** — [errores-conocidos.md](errores-conocidos.md): bugs reales ya diagnosticados y corregidos en producción, para no reabrir la investigación desde cero.
