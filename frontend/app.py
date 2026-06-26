"""
Musicalo Frontend — interfaz de chat web construida con Chainlit.

Conecta con la API REST de Musicalo (backend) vía HTTP.
Variables de entorno:
  BACKEND_URL           URL base del backend (default: http://localhost:8000)
  MUSICALO_API_KEY      Clave de API del backend (vacía = sin auth)
  CHAINLIT_DEFAULT_USER Usuario por defecto cuando no hay reverse proxy (default: musicalo)
  CHAINLIT_DB_PATH      Ruta al fichero SQLite de historial (default: /app/data/chainlit.db)
"""
import os
import re
from typing import Optional

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

# Data layer persistente: guarda threads y mensajes en SQLite
_DB_PATH = os.getenv("CHAINLIT_DB_PATH", "/app/data/chainlit.db")
cl_data._data_layer = SQLAlchemyDataLayer(conninfo=f"sqlite+aiosqlite:///{_DB_PATH}")


# ---------------------------------------------------------------------------
# Auth: identifica al usuario sin mostrar formulario de login
# ---------------------------------------------------------------------------

@cl.header_auth_callback
def header_auth_callback(headers: dict) -> Optional[cl.User]:
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
    return cl.User(identifier=username)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _user_id() -> str:
    """
    Devuelve el identificador estable del usuario autenticado.
    Al usar header auth, este valor es el mismo en todas las sesiones del mismo usuario,
    lo que permite al backend mantener contexto conversacional persistente.
    """
    user = cl.user_session.get("user")
    if user and hasattr(user, "identifier"):
        return user.identifier
    return cl.context.session.id


def _html_to_md(text: str) -> str:
    """Convierte el HTML devuelto por el backend a Markdown para Chainlit."""
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r"[\2](\1)", text)
    text = re.sub(r"<[^>]+>", "", text)  # eliminar etiquetas restantes
    return text


def _build_actions(raw_actions: list) -> list:
    """Convierte la lista de acciones de la API en objetos cl.Action."""
    return [
        cl.Action(
            name=a["id"],
            label=a["label"],
            payload={"action_id": a["id"]},
        )
        for a in raw_actions
    ]


async def _call_chat(message: str) -> dict:
    """Llama a POST /chat/ y devuelve el JSON de respuesta."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{BACKEND_URL}/chat/",
            json={"user_id": _user_id(), "message": message},
            headers=_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Handlers de Chainlit
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content=(
            "## 🎵 Bienvenido a Musicalo\n\n"
            "Soy tu asistente musical con IA. Puedes hablarme en lenguaje natural:\n\n"
            "- *\"Recomiéndame rock progresivo de los 70s\"*\n"
            "- *\"¿Qué álbumes tengo de Pink Floyd?\"*\n"
            "- *\"Crea una playlist de jazz suave\"*\n"
            "- *\"¿Qué estoy escuchando ahora?\"*\n\n"
            "¿Por dónde empezamos? 🎶"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    thinking = cl.Message(content="🤔 Analizando tu mensaje...")
    await thinking.send()

    try:
        data = await _call_chat(message.content)
    except httpx.HTTPStatusError as e:
        thinking.content = f"❌ Error del backend: {e.response.status_code} — {e.response.text}"
        await thinking.update()
        return
    except Exception as e:
        thinking.content = f"❌ No pude conectar con el backend: {e}"
        await thinking.update()
        return

    text = _html_to_md(data.get("text", ""))
    actions = _build_actions(data.get("actions", []))
    thinking.content = text
    thinking.actions = actions
    await thinking.update()


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

    thinking = cl.Message(content="🔄 Generando más recomendaciones...")
    await thinking.send()

    try:
        data = await _call_chat("Recomiéndame 5 canciones diferentes basándote en mis gustos")
    except Exception as e:
        thinking.content = f"❌ Error: {e}"
        await thinking.update()
        return

    text = _html_to_md(data.get("text", ""))
    actions = _build_actions(data.get("actions", []))
    thinking.content = text
    thinking.actions = actions
    await thinking.update()
