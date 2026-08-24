# Convenciones

Reglas de forma que ya se venían aplicando de facto en el código y los commits de Musicalo — puestas en un solo sitio para no tener que inferirlas leyendo el historial cada vez. Términos y nombres propios (qué es Koito, qué hace `resolve_uid()`...) van en [glosario.md](glosario.md), no aquí.

## Commits

Patrón real, consistente en los últimos ~15 commits del repo (ver `git log`):

- **Prefijo capitalizado + dos puntos**, en español: `Fix:`, `Feat:`, `Docs:`, `chore:`. El texto tras el prefijo describe el efecto observable, no el mecanismo ("Fix: conversaciones distintas de Chainlit compartian la misma memoria", no "Fix: cambiar user_id.py").
- **Cuerpo del commit para bugs no trivial**: empieza con "Encontrado en producción: ..." describiendo el síntoma real visto, sigue con la causa raíz, y termina con una lista `- fichero.py: qué cambió y por qué` fichero a fichero. Si el fix no resuelve el problema del todo, dilo explícitamente en una nota aparte en vez de dar a entender que quedó cerrado (ver el commit `195e6c4` como ejemplo: "Nota: no resuelve del todo el caso de...").
- Sin acentos ni `ñ` en el *subject* de algunos commits históricos (probablemente por el terminal usado), pero el cuerpo sí los usa con normalidad — no es una regla deliberada, no hace falta seguirla en commits nuevos.
- `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` al final de cualquier commit generado con Claude Code — ya está en las instrucciones del harness, no hace falta repetirlo de memoria pero sí respetarlo.
- Un commit por hallazgo/cambio coherente — no agrupar un fix de bug con una feature no relacionada en el mismo commit (patrón visible en todo el historial: cada commit toca un problema).

## Versionado

- [VERSION](VERSION) — fichero de una línea con la versión actual (`4.2.1` a fecha de escribir esto), sin prefijo `v`. Lo lee [.github/workflows/docker-publish.yml](.github/workflows/docker-publish.yml) para decidir si un tag `vX.Y.Z` también debe mover el tag Docker `latest` (solo si coincide con el contenido de `VERSION`).
- Tags de git con prefijo `v` (`v4.2.1`) disparan build de ambas imágenes Docker (backend y frontend) sin importar qué cambió; un push a `main` sin tag solo reconstruye la imagen cuya carpeta (`backend/`/`Dockerfile`/... o `frontend/`) cambió realmente — ver el job `changes` del workflow.
- **Aviso**: [CHANGELOG.md](CHANGELOG.md) no está sincronizado con el código real — su última entrada es de enero 2025 y no refleja el cambio a un único agente con function calling (`cdeab96` y posteriores) ni ninguno de los fixes recientes de "Fix:". No lo uses como fuente de verdad del estado actual del proyecto — para eso está [arquitectura.md](arquitectura.md) y el propio `git log`. Si retomas el CHANGELOG, seguiría su formato existente ([Keep a Changelog](https://keepachangelog.com/es/1.0.0/) + [SemVer](https://semver.org/lang/es/)).

## Estilo de código

- Español para nombres de tools del agente (`buscar_biblioteca`, `crear_playlist`) y para todo el texto orientado al usuario (mensajes del bot, `system_prompts.py`); inglés para nombres de clases/módulos/variables internas (`MusicAssistant`, `ConversationSession`) — mezcla deliberada, no la fuerces a ser 100% una cosa o la otra.
- Docstrings explicando el *porqué* además del *qué* cuando el código no es obvio por sí solo (ver cabeceras de [conversation_manager.py](backend/services/conversation_manager.py) o [music_assistant.py](backend/core/music_assistant.py)) — sigue ese nivel de detalle en código nuevo, no un docstring de una línea genérico.
- Sin linter/formatter configurado todavía en el repo (no hay `.flake8`, `pyproject.toml` con `[tool.ruff]`/`[tool.black]`, ni `.editorconfig`) — si introduces uno, documéntalo aquí y enlázalo en vez de duplicarlo.

## Ramas

El historial de `main` no muestra uso de Pull Requests para el trabajo normal (commits directos a `main`) — hay dos ramas remotas de feature sin mergear (`feature/new-agent-approach`, `feature/v4.2.0-improvements`) de las que no hay evidencia de que sigan activas; no asumas que representan trabajo en curso sin comprobarlo primero (`git log <rama> -5`).

## Notación en este set de documentos

Este repo no usaba todavía marcadores de estado tipo `[CONFIRMADO]`/`[PROPUESTA]`/`[ABIERTO]` antes de esta estructura de documentación. Si abres una decisión con partes pendientes de validar en [decisiones/](decisiones/README.md), puedes adoptarlos con ese mismo significado (dato verificado vs. recomendación pendiente vs. bloqueado por falta de info) — defínelo aquí si empiezas a usarlos de verdad, para que no quede como una convención fantasma.
