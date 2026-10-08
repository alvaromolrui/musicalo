# Pruebas del agente

Dos scripts, sin pytest ni CI (no hay pipeline de tests en el repo, ver [flujo-de-trabajo.md](../flujo-de-trabajo.md#ciclo-real-de-publicación)). Se llaman `check_*` y no `test_*` a propósito: son scripts que se ejecutan directamente, no tests que `pytest` vaya a descubrir.

| Script | Qué prueba | Dónde corre | Coste |
|---|---|---|---|
| [check_agent_loop.py](check_agent_loop.py) | El bucle de `MusicAgentService` con Gemini y Navidrome/Koito **simulados**: paralelismo, guardarraíl de playlist duplicada, agotar rondas, consultas concurrentes, argumentos inventados, renombrar, parámetros prohibidos por Google, memoria entre turnos, guardarraíl de playlists inventadas y el normalizador de HTML para Telegram | En local, con las dependencias de `requirements.txt` | Ninguno: sin red ni claves, unos segundos |
| [check_agent_live.py](check_agent_live.py) | Conversaciones reales (formato, memoria, crear y refinar playlist, renombrar, cultura musical, estadísticas, petición abierta) con Gemini, Navidrome y Koito **de verdad** y las escrituras simuladas | Dentro del contenedor `musicalo` | ~10 llamadas reales a Gemini, 1 minuto aprox. |

## Cuándo pasarlas

- `check_agent_loop.py`: antes de cada commit que toque `music_agent_service.py`, `conversation_manager.py`, `text_format.py`, `gemini_client.py` o las tools. Si añades una tool o un guardarraíl, añade su caso aquí.
- `check_agent_live.py`: antes de desplegar un cambio de comportamiento del agente (prompt, tools, memoria) y, si cambias `GEMINI_MODEL`, con el modelo nuevo. Las respuestas hay que mirarlas a ojo: el script solo comprueba que no hay errores ni HTML inválido, no si la recomendación es buena.

## Cómo ejecutarlas

### Simuladas (local)

```bash
pip install -r requirements.txt   # una vez, mejor en un venv
python tests/check_agent_loop.py
```

Imprime `PASS`/`FAIL` por caso y sale con código 1 si falla alguno. Fuerza su propio entorno (claves falsas, URLs `.invalid`), así que no importa lo que tengas en `.env`.

### Reales (en el servidor)

Se pasan por stdin al contenedor, que ya tiene las dependencias y las variables de entorno: las claves no salen del servidor. Desde el host donde corre el contenedor (`docker-server`), con el repo clonado:

```bash
docker exec -i -e PYTHONIOENCODING=utf-8 musicalo python - < tests/check_agent_live.py
```

Eso prueba el código **desplegado** (`/app/backend`). Para probar un cambio **antes** de desplegarlo, copia el backend nuevo a una carpeta temporal del contenedor y apunta `MUSICALO_BACKEND` a ella:

```bash
tar --exclude=__pycache__ -cf - backend | docker exec -i musicalo sh -c "rm -rf /tmp/musicalo-next && mkdir -p /tmp/musicalo-next && tar -xf - -C /tmp/musicalo-next"
docker exec -i -e PYTHONIOENCODING=utf-8 -e MUSICALO_BACKEND=/tmp/musicalo-next/backend musicalo python - < tests/check_agent_live.py
docker exec musicalo rm -rf /tmp/musicalo-next
```

`ONLY=playlist,memoria` (otro `-e`) limita los escenarios. El script corre en su propio proceso: no comparte sesiones con el servidor en marcha ni deja nada en Navidrome. Crear, editar y renombrar playlists y compartir se simulan en memoria; las lecturas (biblioteca, playlists, historial) sí son reales.

## Script antiguo

[test_playlist_creation.py](../test_playlist_creation.py), en la raíz, es de antes del agente actual: **no arranca** (`ModuleNotFoundError: No module named 'models'`, por cómo importa el backend) y, si arrancara, **crearía tres playlists reales** en Navidrome. Lo sustituyen los dos scripts de esta carpeta.
