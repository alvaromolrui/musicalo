"""
Musicalo Frontend — interfaz de chat web construida con Chainlit.

Conecta con la API REST de Musicalo (backend) vía HTTP.
Variables de entorno:
  BACKEND_URL           URL base del backend (default: http://localhost:8000)
  MUSICALO_API_KEY      Clave de API del backend (vacía = sin auth)
  CHAINLIT_DEFAULT_USER Usuario por defecto cuando no hay reverse proxy (default: musicalo)
  CHAINLIT_DB_PATH      Ruta al fichero SQLite de historial (default: /app/data/chainlit.db)
"""
import asyncio
import json
import os
import re
from typing import Optional

import aiosqlite
import httpx
import chainlit as cl
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("MUSICALO_API_KEY", "").strip()
_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
_TIMEOUT = 90  # segundos — las respuestas de IA pueden tardar

_DB_PATH = os.getenv("CHAINLIT_DB_PATH", "/app/data/chainlit.db")
_DEFAULT_USER = os.getenv("CHAINLIT_DEFAULT_USER", "musicalo")

# Velocidad del efecto streaming (segundos entre palabras)
_STREAM_DELAY = 0.018


class _DataLayer(SQLAlchemyDataLayer):
    """Data layer con correcciones para Chainlit 2.11.1 + SQLite.

    - get_thread_author: la columna userIdentifier queda NULL porque Chainlit
      no la incluye en el INSERT. Devolvemos el usuario por defecto en lugar
      de lanzar ValueError (que provoca HTTP 500).

    - get_thread: si falla la deserialización de pasos o cualquier otro
      error, devolvemos None para que Chainlit arranque un chat limpio en
      lugar de mostrar la pantalla negra.
    """

    async def get_thread_author(self, thread_id: str) -> str:
        try:
            author = await super().get_thread_author(thread_id)
            if author:
                return author
        except Exception:
            pass
        return _DEFAULT_USER

    async def get_thread(self, thread_id: str):
        try:
            return await super().get_thread(thread_id)
        except Exception as exc:
            print(f"[warn] get_thread {thread_id}: {exc}")
            return None


# Data layer persistente: guarda threads y mensajes en SQLite
cl_data._data_layer = _DataLayer(conninfo=f"sqlite+aiosqlite:///{_DB_PATH}")


# ---------------------------------------------------------------------------
# Auth: identifica al usuario sin mostrar formulario de login
# ---------------------------------------------------------------------------

@cl.header_auth_callback
async def header_auth_callback(headers: dict) -> Optional[cl.User]:
    """
    Identifica al usuario a partir de cabeceras HTTP, sin pantalla de login.

    Con un reverse proxy que soporte forward auth (Traefik, nginx + Authelia,
    Caddy, etc.) se puede proporcionar la cabecera X-Auth-User para que cada
    usuario tenga su propio historial separado.

    Sin proxy, todos los accesos se identifican con CHAINLIT_DEFAULT_USER
    y comparten el mismo historial.
    """
    username = (
        headers.get("x-auth-user")
        or headers.get("x-forwarded-user")
        or headers.get("remote-user")
        or os.getenv("CHAINLIT_DEFAULT_USER", "musicalo")
    )
    user = cl.User(identifier=username, metadata={})

    # Crear el usuario en el data layer si no existe todavía.
    data_layer = cl_data._data_layer
    if data_layer:
        existing = await data_layer.get_user(username)
        if not existing:
            await data_layer.create_user(user)

    return user


# ---------------------------------------------------------------------------
# Starters: mensajes sugeridos en chat nuevo
# ---------------------------------------------------------------------------

@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(
            label="Recomiéndame música",
            message="Recomiéndame artistas o álbumes que me puedan gustar basándote en mis gustos musicales",
        ),
        cl.Starter(
            label="¿Qué estoy escuchando?",
            message="¿Qué está sonando ahora mismo en mis reproductores?",
        ),
        cl.Starter(
            label="Mis estadísticas",
            message="¿Cuáles son mis estadísticas de escucha de este mes?",
        ),
        cl.Starter(
            label="Crear playlist",
            message="Crea una playlist de jazz suave para trabajar",
        ),
        cl.Starter(
            label="Buscar en mi biblioteca",
            message="Busca álbumes de Pink Floyd en mi biblioteca",
        ),
        cl.Starter(
            label="Lanzamientos recientes",
            message="¿Ha sacado algo nuevo alguno de mis artistas favoritos?",
        ),
    ]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _user_id() -> str:
    user = cl.user_session.get("user")
    if user and hasattr(user, "identifier"):
        return user.identifier
    return cl.context.session.id


async def _patch_thread_author(user_identifier: str) -> None:
    """
    Escribe userIdentifier en la fila del thread actual.

    Chainlit 2.11.1 no persiste userIdentifier en el INSERT de threads,
    así que lo hacemos nosotros en on_chat_start, cuando ya tenemos el
    thread_id y el usuario identificado.
    Sin userIdentifier, list_threads no devuelve nada y la restauración
    de conversaciones del sidebar no funciona.
    """
    session_id = cl.context.session.id
    thread_id: Optional[str] = getattr(cl.context.session, "thread_id", None)

    try:
        async with aiosqlite.connect(_DB_PATH) as db:
            if not thread_id:
                row = await (await db.execute(
                    "SELECT id FROM threads"
                    " WHERE json_extract(metadata, '$.id') = ? LIMIT 1",
                    (session_id,),
                )).fetchone()
                thread_id = row[0] if row else None

            if not thread_id:
                print(f"[warn] patch_thread_author: no thread found for session {session_id}")
                return

            await db.execute(
                '''UPDATE "threads"
                   SET "userIdentifier" = ?,
                       "userId" = (
                           SELECT "id" FROM "users"
                           WHERE "identifier" = ?
                           LIMIT 1
                       )
                   WHERE "id" = ?''',
                (user_identifier, user_identifier, thread_id),
            )
            await db.commit()
            print(f"[info] patch_thread_author: thread={thread_id[:8]}… → user={user_identifier}")
    except Exception as exc:
        print(f"[warn] patch_thread_author: {exc}")


def _html_to_md(text: str) -> str:
    """Convierte el HTML devuelto por el backend a Markdown para Chainlit."""
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r"[\2](\1)", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def _build_actions(raw_actions: list) -> list:
    return [
        cl.Action(
            name=a["id"],
            label=a["label"],
            payload={"action_id": a["id"]},
        )
        for a in raw_actions
    ]


async def _stream_response(text: str, actions: list) -> None:
    """Envía la respuesta palabra a palabra para efecto de streaming visual."""
    msg = cl.Message(content="")
    await msg.send()

    words = text.split(" ")
    for i, word in enumerate(words):
        await msg.stream_token(word + (" " if i < len(words) - 1 else ""))
        await asyncio.sleep(_STREAM_DELAY)

    msg.actions = _build_actions(actions)
    await msg.update()


# ---------------------------------------------------------------------------
# Handlers de Chainlit
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    if user:
        await _patch_thread_author(user.identifier)


@cl.on_message
async def on_message(message: cl.Message):
    text = ""
    actions_data = []

    # Step visible mientras el backend procesa (Navidrome, ListenBrainz, Gemini…)
    async with cl.Step(name="Procesando tu consulta", type="run") as step:
        step.input = message.content
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{BACKEND_URL}/chat/stream",
                    json={"user_id": _user_id(), "message": message.content},
                    headers=_HEADERS,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        event = json.loads(line[6:])
                        if event["type"] == "text":
                            text = _html_to_md(event["content"])
                        elif event["type"] == "done":
                            actions_data = event.get("actions", [])
                        elif event["type"] == "error":
                            raise RuntimeError(event["message"])

            step.output = "✓"

        except httpx.HTTPStatusError as e:
            step.output = f"Error {e.response.status_code}"
            await cl.Message(
                content=f"❌ Error del backend: {e.response.status_code} — {e.response.text}"
            ).send()
            return
        except Exception as e:
            step.output = f"Error: {e}"
            await cl.Message(content=f"❌ No pude conectar con el backend: {e}").send()
            return

    # Respuesta con efecto de streaming visual
    await _stream_response(text, actions_data)


# ---------------------------------------------------------------------------
# Callbacks de botones
# ---------------------------------------------------------------------------

@cl.action_callback("like_rec")
async def on_like(action: cl.Action):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BACKEND_URL}/music/feedback",
                json={"user_id": _user_id(), "track_id": "rec", "feedback_type": "like"},
                headers=_HEADERS,
            )
    except Exception:
        pass
    await cl.Message(content="❤️ ¡Gracias! He registrado que te gusta esta recomendación.").send()
    await action.remove()


@cl.action_callback("dislike_rec")
async def on_dislike(action: cl.Action):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BACKEND_URL}/music/feedback",
                json={"user_id": _user_id(), "track_id": "rec", "feedback_type": "dislike"},
                headers=_HEADERS,
            )
    except Exception:
        pass
    await cl.Message(content="👎 Entendido. Evitaré recomendaciones similares.").send()
    await action.remove()


@cl.action_callback("more_recommendations")
async def on_more(action: cl.Action):
    await action.remove()

    async with cl.Step(name="Buscando más recomendaciones", type="run") as step:
        step.input = "more_recommendations"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{BACKEND_URL}/chat/stream",
                    json={
                        "user_id": _user_id(),
                        "message": "Recomiéndame 5 canciones diferentes basándote en mis gustos",
                    },
                    headers=_HEADERS,
                ) as resp:
                    resp.raise_for_status()
                    text, actions_data = "", []
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        event = json.loads(line[6:])
                        if event["type"] == "text":
                            text = _html_to_md(event["content"])
                        elif event["type"] == "done":
                            actions_data = event.get("actions", [])
                        elif event["type"] == "error":
                            raise RuntimeError(event["message"])
            step.output = "✓"
        except Exception as e:
            step.output = f"Error: {e}"
            await cl.Message(content=f"❌ Error: {e}").send()
            return

    await _stream_response(text, actions_data)
