#!/usr/bin/env python3
"""
Prueba REAL del agente: Gemini, Navidrome y Koito de verdad, con las ESCRITURAS simuladas.

Lanza conversaciones de ejemplo (formato, memoria entre turnos, crear y refinar una
playlist, renombrar, cultura musical sin tools, estadísticas, petición abierta) y
para cada respuesta muestra tiempo, tools usadas, escrituras (simuladas) y si el
HTML es válido para Telegram. Crear/editar/renombrar playlists y compartir NUNCA
llegan a Navidrome: se guardan en memoria del propio script. Las lecturas sí son
reales, y cada consulta consume llamadas reales a Gemini.

Se ejecuta DENTRO del contenedor `musicalo`, que ya tiene las dependencias y las
variables de entorno (las claves no salen del servidor). Por stdin, desde el host
donde corre el contenedor:

    docker exec -i -e PYTHONIOENCODING=utf-8 musicalo python - < tests/check_agent_live.py

Opciones (variables de entorno, con -e en el docker exec):
- MUSICALO_BACKEND: backend a probar (default /app/backend, el desplegado). Para
  probar ANTES de desplegar, copia el backend nuevo al contenedor y apunta aquí,
  ver tests/README.md.
- ONLY: escenarios separados por comas (p.ej. ONLY=playlist,memoria).

Corre en su propio proceso: no comparte sesiones ni memoria con el servidor en
marcha. Sale con código 1 si alguna respuesta tiene HTML inválido o falla.
"""
import asyncio
import os
import re
import sys
import time

BACKEND = os.getenv("MUSICALO_BACKEND", "/app/backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

import logging  # noqa: E402
logging.basicConfig(level=logging.WARNING, format="LOG %(levelname)s %(name)s: %(message)s")

from core.music_assistant import MusicAssistant  # noqa: E402
from models.schemas import Track  # noqa: E402

ALLOWED_TAG = re.compile(r"</?(b|i|code)>|<a href=\"[^\"<>]+\">|</a>")

SCENARIOS = [
    ("formato", ["¿Qué discos he añadido últimamente a la biblioteca? Dime los 5 más recientes."]),
    ("memoria", ["¿Qué canciones tengo de Vetusta Morla? Dime solo 5.",
                 "¿De qué disco es la tercera que me has dicho y de qué año es?"]),
    ("playlist", ["Hazme una playlist de 6 canciones tranquilas para leer, de lo que tengo.",
                  "Quita la segunda y pon en su lugar otra canción que encaje."]),
    ("renombrar", ["Hazme una playlist de 4 canciones de Vetusta Morla.",
                   "Ahora renómbrala a 'Morla esencial'."]),
    ("conocimiento", ["¿Por qué se considera tan importante el Loveless de My Bloody Valentine? En pocas líneas."]),
    ("estadisticas", ["¿Cuánto he escuchado este año y qué artista ha dominado?"]),
    ("abierta", ["Estoy un poco de bajón, ¿qué disco de los que tengo me pondrías ahora?"]),
]


def telegram_html_problem(text: str) -> str:
    """'' si el texto es HTML válido para Telegram (parse_mode=HTML); si no, el motivo."""
    stack = []
    for m in re.finditer(r"<[^>]*>", text):
        tag = m.group(0)
        if not ALLOWED_TAG.fullmatch(tag):
            return f"etiqueta no permitida {tag!r}"
        name = re.match(r"</?(\w+)", tag).group(1)
        if tag.startswith("</"):
            if not stack or stack.pop() != name:
                return f"cierre desbalanceado {tag!r}"
        else:
            stack.append(name)
    if stack:
        return f"sin cerrar {stack}"
    if re.search(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)", text):
        return "& sin escapar"
    if re.search(r"(?m)^\s*[*-]\s|\*\*", text):
        return "Markdown sin convertir"
    return ""


def simulate_writes(nav, fake_playlists, writes):
    """Sustituye en un NavidromeService todo lo que escribe por una versión en memoria."""
    async def create_playlist(name, song_ids):
        pid = f"fake-{len(fake_playlists) + 1}"
        fake_playlists[pid] = {"name": name, "ids": list(song_ids)}
        writes.append(("crear", name, len(song_ids)))
        return pid

    async def update_playlist_songs(pid, song_ids):
        if pid not in fake_playlists:  # una playlist real del usuario: no se toca
            writes.append(("actualizar-real-bloqueada", pid, len(song_ids)))
            fake_playlists[pid] = {"name": "(real, simulada)", "ids": []}
        fake_playlists[pid]["ids"] = list(song_ids)
        writes.append(("actualizar", fake_playlists[pid]["name"], len(song_ids)))
        return True

    async def rename_playlist(pid, name):
        if pid not in fake_playlists:
            writes.append(("renombrar-real-bloqueada", pid, name))
            return
        writes.append(("renombrar", fake_playlists[pid]["name"], name))
        fake_playlists[pid]["name"] = name

    real_get_playlist_tracks = nav.get_playlist_tracks

    async def get_playlist_tracks(pid):
        if pid not in fake_playlists:
            return await real_get_playlist_tracks(pid)  # lectura real de una playlist del usuario
        tracks = []
        for sid in fake_playlists[pid]["ids"]:
            song = (await nav._make_request("getSong", {"id": sid})).get("song", {})
            tracks.append(Track(id=sid, title=song.get("title", ""), artist=song.get("artist", ""),
                                album=song.get("album", ""), year=song.get("year"), genre=song.get("genre")))
        return tracks

    async def create_share(ids, description=None, expires=None):
        writes.append(("compartir", len(ids)))
        return {"id": "fake-share", "url": "https://navidrome.invalid/share/fake", "description": description}

    nav.create_playlist = create_playlist
    nav.update_playlist_songs = update_playlist_songs
    nav.rename_playlist = rename_playlist
    nav.get_playlist_tracks = get_playlist_tracks
    nav.create_share = create_share


async def main():
    print(f"Backend probado: {BACKEND}")
    assistant = MusicAssistant()
    agent = assistant.agent

    fake_playlists, writes = {}, []
    # Las dos instancias de NavidromeService: la del agente y la de MusicAssistant
    # (setlist.fm, compartir por comando...). Ninguna debe escribir de verdad.
    simulate_writes(agent.navidrome, fake_playlists, writes)
    simulate_writes(assistant.navidrome, fake_playlists, writes)

    real_query = agent.query
    last = {}

    async def query(q, user_id, context=None):
        r = await real_query(q, user_id=user_id, context=context)
        last["r"] = r
        return r
    agent.query = query

    only = [x for x in os.getenv("ONLY", "").split(",") if x]
    problems = []
    for uid, (name, turns) in enumerate(SCENARIOS, start=900):
        if only and name not in only:
            continue
        print(f"\n=================== {name} ===================")
        for q in turns:
            writes.clear()
            last.clear()
            t = time.time()
            try:
                resp = await assistant.chat(uid, q)
            except Exception as e:
                problems.append(f"{name}: excepción {type(e).__name__}: {e}")
                print(f"\n> {q}\n  EXCEPCIÓN {type(e).__name__}: {e}")
                continue
            dt = time.time() - t
            r = last.get("r", {})
            tools = [x["tool"] for x in r.get("data_used", {}).get("tools_used", [])]
            problem = telegram_html_problem(resp.text)
            if problem:
                problems.append(f"{name}: HTML {problem}")
            if not resp.success:
                problems.append(f"{name}: respuesta de error")
            print(f"\n> {q}")
            print(f"  [{dt:.1f}s] tools={tools} escrituras={writes} html={'OK' if not problem else 'MAL: ' + problem}")
            print("  " + resp.text.replace("\n", "\n  ")[:900])

    await agent.close()
    print("\n=================== resumen ===================")
    print("\n".join(problems) if problems else "Sin problemas de formato ni errores. Revisa a ojo la calidad de las respuestas.")
    sys.exit(1 if problems else 0)


asyncio.run(main())
