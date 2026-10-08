#!/usr/bin/env python3
"""
Pruebas del agente con Gemini y Navidrome/Koito SIMULADOS: sin red ni claves.

Cubren el bucle de tool-calling de MusicAgentService (paralelismo, guardarraíles,
memoria entre turnos, estado por petición) y el normalizador de HTML para
Telegram. Pásalas antes de cada commit que toque el agente:

    python tests/check_agent_loop.py

Necesitan las dependencias del backend (requirements.txt) y nada más. Cualquier
llamada no simulada a Navidrome o Koito se bloquea antes de salir a la red: la
tool recibe el error "llamada de red no simulada" (las tools capturan sus
excepciones, así que eso no hace fallar la prueba por sí solo; si una prueba
nueva falla raro, busca ese texto). Sale con código 1 si falla alguna. Detalle
en tests/README.md.
"""
import asyncio
import os
import sys
import time

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")

# Entorno aislado ANTES de importar nada del backend: los servicios leen la config al instanciarse
os.environ["GEMINI_API_KEY"] = "dummy"
os.environ["NAVIDROME_URL"] = "http://navidrome.invalid"
os.environ["KOITO_URL"] = "http://koito.invalid"
os.environ["ENABLE_MUSICBRAINZ"] = "false"
os.environ.pop("SETLISTFM_API_KEY", None)
os.environ.pop("REDIS_URL", None)
sys.path.insert(0, BACKEND)

from google.genai import types  # noqa: E402
import services.music_agent_service as mas  # noqa: E402
from services.text_format import normalize_html  # noqa: E402


# ----------------------------------------------------------------------------
# Gemini simulado: cada prueba define un "guion" (contents, config, n) -> respuesta
# ----------------------------------------------------------------------------

def call(name, **args):
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def resp(*parts):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))])


def text(t):
    return resp(types.Part(text=t))


class FakeModels:
    def __init__(self, script):
        self.script = script
        self.configs = []
        self.n = 0

    async def generate_content(self, model, contents, config):
        self.configs.append(config)
        self.n += 1
        return self.script(contents, config, self.n)


def make_agent(script):
    """MusicAgentService con Gemini simulado y Navidrome/Koito sin red."""
    agent = mas.MusicAgentService()
    fake = FakeModels(script)
    agent.client = type("C", (), {"aio": type("A", (), {"models": fake})()})()

    async def no_network(endpoint, *a, **k):
        raise AssertionError(f"llamada de red no simulada: {endpoint}")
    agent.navidrome._make_request = no_network
    agent.history_service._make_request = no_network

    created = []

    async def create_playlist(name, ids):
        await asyncio.sleep(0.05)
        created.append(name)
        return f"pl-{name}"

    async def slow(*a, **k):
        await asyncio.sleep(0.3)
        return []

    async def get_playlists():
        return [{"id": "pl-old", "name": "Correr", "song_count": 2}]

    async def update(pid, ids):
        return True

    async def rename(pid, name):
        created.append(f"rename:{pid}:{name}")

    async def share(ids, description=None, expires=None):
        return {"id": "s1", "url": "https://navidrome.invalid/share/s1"}

    agent.navidrome.create_playlist = create_playlist
    agent.navidrome.update_playlist_songs = update
    agent.navidrome.rename_playlist = rename
    agent.navidrome.create_share = share
    agent.navidrome.get_genres = slow
    agent.navidrome.get_playlists = get_playlists
    agent.history_service.get_top_artists = slow
    return agent, fake, created


def results_of(contents):
    """Resultados de tools que el bucle devolvió al modelo en el último turno."""
    return [p.function_response.response["result"] for p in contents[-1].parts if p.function_response]


# ----------------------------------------------------------------------------
# Bucle de tool-calling
# ----------------------------------------------------------------------------

async def t_parallel_reads():
    def script(contents, config, n):
        return resp(call("listar_generos"), call("top_artistas")) if n == 1 else text("ok")
    agent, fake, _ = make_agent(script)
    t0 = time.perf_counter()
    r = await agent.query("hola", user_id=1)
    dt = time.perf_counter() - t0
    assert r["success"] and r["answer"] == "ok", r
    assert dt < 0.5, f"no se ejecutaron en paralelo: {dt:.2f}s"
    return f"2 lecturas de 0.3s en {dt:.2f}s"


async def t_write_guard_and_state():
    seen = {}
    def script(contents, config, n):
        if n == 1:
            return resp(call("crear_playlist", nombre="A", ids_canciones=["1"]),
                        call("crear_playlist", nombre="B", ids_canciones=["2"]))
        seen["results"] = results_of(contents)
        return text("hecho")
    agent, fake, created = make_agent(script)
    r = await agent.query("haz una playlist", user_id=2)
    assert created == ["A"], created
    assert seen["results"][0].get("success") and "Ya hay una playlist activa" in seen["results"][1]["error"], seen
    assert r["playlist_created"] and r["playlist_created"]["id"] == "pl-A", r
    return "segunda crear_playlist bloqueada; playlist_created llega a query()"


async def t_exhaustion_final_answer():
    def script(contents, config, n):
        mode = config.tool_config.function_calling_config.mode if config.tool_config else None
        if mode == types.FunctionCallingConfigMode.NONE:
            return text("resumen con lo que tengo")
        return resp(call("listar_generos"))
    original = mas.MAX_TOOL_TURNS
    mas.MAX_TOOL_TURNS = 3
    try:
        agent, fake, _ = make_agent(script)
        r = await agent.query("algo largo", user_id=3)
    finally:
        mas.MAX_TOOL_TURNS = original
    assert r["answer"] == "resumen con lo que tengo", r
    assert fake.n == 4, fake.n
    return "tras agotar rondas responde sin tools en vez de error genérico"


async def t_concurrent_users():
    def script(contents, config, n):
        last_user = contents[-1]
        if last_user.parts[0].text:  # primer turno de la consulta
            return resp(call("crear_playlist", nombre=last_user.parts[0].text, ids_canciones=["x"]))
        return text("listo")
    agent, fake, created = make_agent(script)
    r1, r2 = await asyncio.gather(agent.query("U1", user_id=10), agent.query("U2", user_id=11))
    assert r1["playlist_created"]["name"] == "U1" and r2["playlist_created"]["name"] == "U2", (r1, r2)
    s1 = agent.conversation_manager.get_session(10).last_playlist
    s2 = agent.conversation_manager.get_session(11).last_playlist
    assert s1["name"] == "U1" and s2["name"] == "U2", (s1, s2)
    assert sorted(created) == ["U1", "U2"]
    return "dos usuarios a la vez: cada uno su playlist y su sesión"


async def t_bad_args():
    seen = {}
    def script(contents, config, n):
        if n == 1:
            return resp(call("listar_generos", inventado=True))
        seen["r"] = results_of(contents)[0]
        return text("corregido")
    agent, fake, _ = make_agent(script)
    r = await agent.query("x", user_id=4)
    assert r["success"] and "Argumentos no válidos" in seen["r"]["error"], seen
    return "argumento inventado vuelve al modelo como error, no rompe la consulta"


async def t_existing_playlist_becomes_active():
    def script(contents, config, n):
        if n == 1:
            return resp(call("actualizar_playlist", ids_canciones=["9"], playlist_id="pl-old"))
        return text("actualizada")
    agent, fake, _ = make_agent(script)
    await agent.query("edita mi playlist de correr", user_id=5)
    assert agent.conversation_manager.get_session(5).last_playlist == {"id": "pl-old", "name": "Correr"}
    return "editar una playlist existente la deja como activa"


async def t_rename_active_playlist():
    def script(contents, config, n):
        if n == 1:
            return resp(call("crear_playlist", nombre="Vieja", ids_canciones=["1"]))
        if n == 3:
            return resp(call("renombrar_playlist", nuevo_nombre="Nueva", playlist_id="pl-Vieja"))
        return text("ok")
    agent, fake, created = make_agent(script)
    await agent.query("hazme una playlist", user_id=7)
    await agent.query("renómbrala a Nueva", user_id=7)
    assert created == ["Vieja", "rename:pl-Vieja:Nueva"], created
    assert agent.conversation_manager.get_session(7).last_playlist == {"id": "pl-Vieja", "name": "Nueva"}
    return "renombra la activa (id explícito, sin ir a Navidrome a buscarla) y actualiza la sesión"


async def t_no_forbidden_params():
    def script(contents, config, n):
        return text("ok")
    agent, fake, _ = make_agent(script)
    await agent.query("x", user_id=6)
    cfg = fake.configs[0]
    for f in ("temperature", "top_p", "top_k", "max_output_tokens"):
        assert getattr(cfg, f) is None, f
    assert cfg.thinking_config is None or cfg.thinking_config.thinking_budget is None
    return f"sin temperature/top_p/top_k/thinking_budget (thinking_config={cfg.thinking_config})"


# ----------------------------------------------------------------------------
# Memoria entre turnos
# ----------------------------------------------------------------------------

async def t_memory_keeps_tool_results():
    seen = {}
    async def search(q, limit=20):
        from models.schemas import Track
        return {"tracks": [Track(id="t-99", title="Sometimes", artist="MBV", album="Loveless", path="/music/x.flac")],
                "albums": [], "artists": []}
    def script(contents, config, n):
        if n == 1:
            return resp(call("buscar_biblioteca", consulta="Sometimes"))
        if n == 2:
            return text("La tengo, es de Loveless.")
        seen["contents"] = list(contents)
        return text("El id era t-99.")
    agent, fake, _ = make_agent(script)
    agent.navidrome.search = search
    await agent.query("¿tengo Sometimes?", user_id=20)
    await agent.query("¿qué id tenía?", user_id=20)
    hist = seen["contents"]
    fr = [p.function_response.response["result"] for c in hist for p in (c.parts or []) if p.function_response]
    assert fr and fr[0]["tracks"][0]["id"] == "t-99", hist
    assert "path" not in fr[0]["tracks"][0] and "cover_url" not in fr[0]["tracks"][0], fr[0]
    roles = [c.role for c in hist]
    assert roles == ["user", "model", "user", "model", "user"], roles
    return "el 2º turno ve la llamada y el resultado del 1º (compactado, sin path/nulos)"


async def t_memory_old_turns_text_only():
    def script(contents, config, n):
        if contents[-1].parts[0].text == "T6":
            script.hist = list(contents)  # copia: la lista sigue creciendo dentro del bucle
        return resp(call("listar_generos")) if contents[-1].parts[0].text else text("ok")
    agent, fake, _ = make_agent(script)
    for i in range(1, 7):
        await agent.query(f"T{i}", user_id=21)
    session = agent.conversation_manager.get_session(21)
    assert len(session.agent_turns) == mas.MEMORY_TURNS, len(session.agent_turns)
    hist = script.hist
    n_fc = sum(1 for c in hist for p in (c.parts or []) if p.function_call)
    assert hist[0].parts[0].text == "T1", hist[0].parts[0].text  # T1..T5 en memoria al preguntar T6
    assert n_fc == mas.TOOL_MEMORY_TURNS, n_fc  # solo los últimos con detalle de tools
    return f"{mas.MEMORY_TURNS} turnos en memoria, solo los {mas.TOOL_MEMORY_TURNS} últimos con detalle de tools"


# ----------------------------------------------------------------------------
# Guardarraíl contra playlists inventadas
# ----------------------------------------------------------------------------

async def t_claim_without_write_gets_nudged():
    seen = {}
    def script(contents, config, n):
        if n == 1:
            return text("¡Listo! He quitado la canción de la playlist.")
        if n == 2:
            seen["nudge"] = contents[-1].parts[0].text
            return resp(call("actualizar_playlist", ids_canciones=["1"], playlist_id="pl-old"))
        return text("Hecho, he quitado la canción de la playlist Correr.")
    agent, fake, _ = make_agent(script)
    r = await agent.query("quita la última de mi playlist de correr", user_id=30)
    assert "Comprobación automática" in seen["nudge"], seen
    assert "⚠️" not in r["answer"], r["answer"]
    assert r["data_used"]["tools_used"][0]["tool"] == "actualizar_playlist"
    return "afirmó sin tool -> se le devolvió -> llamó a actualizar_playlist, sin aviso al usuario"


async def t_claim_persists_adds_warning():
    def script(contents, config, n):
        return text("He renombrado la playlist a Calma.")
    agent, fake, _ = make_agent(script)
    r = await agent.query("renombra mi playlist a Calma", user_id=31)
    assert fake.n == 2, fake.n  # una sola corrección, no un bucle
    assert "no he podido confirmar ese cambio" in r["answer"], r["answer"]
    return "si insiste sin tool, el usuario recibe el aviso (y solo 1 reintento)"


async def t_real_write_no_nudge():
    def script(contents, config, n):
        if n == 1:
            return resp(call("crear_playlist", nombre="Calma", ids_canciones=["1"]))
        return text("He creado la playlist Calma con 1 canción.")
    agent, fake, _ = make_agent(script)
    r = await agent.query("hazme una playlist", user_id=32)
    assert fake.n == 2 and "⚠️" not in r["answer"], (fake.n, r["answer"])
    return "con escritura real no hay reintento ni aviso"


async def t_claim_detection():
    for t in ("Ayer creé la playlist Calma, ¿quieres verla?", "He añadido a mi lista mental a Radiohead",
              "Tienes 3 playlists: Correr, Calma y Fiesta."):
        assert not mas._claims_playlist_change(t), t
    for t in ("He creado la playlist Calma.", "Tu playlist ya está actualizada", "Ya he quitado esa de la playlist"):
        assert mas._claims_playlist_change(t), t
    return "pasado simple y frases sin cambio no disparan; 'he creado/quitado' sí"


# ----------------------------------------------------------------------------
# Normalizador de HTML para Telegram (services/text_format.py)
# ----------------------------------------------------------------------------

async def t_normalize_html():
    cases = {
        "Tengo estas:\n\n*   <b>In Utero</b> (1993)\n\n*   Lithium\n\nY ya.":
            "Tengo estas:\n\n• <b>In Utero</b> (1993)\n• Lithium\n\nY ya.",
        "Esto es **muy** bueno y *raro*, 3 * 4 = 12":
            "Esto es <b>muy</b> bueno y <i>raro</i>, 3 * 4 = 12",
        "Simon & Garfunkel son < que Queen &amp; ya":
            "Simon &amp; Garfunkel son &lt; que Queen &amp; ya",
        '<a href="https://x.com/?a=1&b=2">enlace</a>':
            '<a href="https://x.com/?a=1&amp;b=2">enlace</a>',
        "<ul><li>uno</li><li>dos</li></ul><p>párrafo</p>fin<br>línea":
            "• uno\n• dos\n\npárrafo\nfin\nlínea",
        "<b>abierta y </i> huérfana <i>cursiva <b>mal</i> anidada</b>":
            "<b>abierta y  huérfana <i>cursiva mal</i> anidada</b>",
        "Mira [Loveless](https://es.wikipedia.org/wiki/Loveless) y `codigo`":
            'Mira <a href="https://es.wikipedia.org/wiki/Loveless">Loveless</a> y <code>codigo</code>',
        "## Recomendaciones\nTexto": "<b>Recomendaciones</b>\nTexto",
        "Hola, tienes 3 discos de Radiohead.": "Hola, tienes 3 discos de Radiohead.",
    }
    for src, expected in cases.items():
        got = normalize_html(src)
        assert got == expected, f"{src!r}\n  esperado {expected!r}\n  obtenido {got!r}"
        assert normalize_html(got) == got, f"no idempotente: {got!r}"
    return f"{len(cases)} casos (Markdown, escapado, etiquetas raras/desbalanceadas, idempotencia)"


async def main():
    tests = [
        t_parallel_reads, t_write_guard_and_state, t_exhaustion_final_answer, t_concurrent_users,
        t_bad_args, t_existing_playlist_becomes_active, t_rename_active_playlist, t_no_forbidden_params,
        t_memory_keeps_tool_results, t_memory_old_turns_text_only,
        t_claim_without_write_gets_nudged, t_claim_persists_adds_warning, t_real_write_no_nudge, t_claim_detection,
        t_normalize_html,
    ]
    failed = 0
    for t in tests:
        try:
            print(f"PASS {t.__name__}: {await t()}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
