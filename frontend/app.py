"""
Musicalo Frontend — interfaz de chat web construida con Chainlit.

Conecta con la API REST de Musicalo (backend) vía HTTP.
Variables de entorno:
  BACKEND_URL      URL base del backend (default: http://localhost:8000)
  MUSICALO_API_KEY Clave de API del backend (vacía = sin auth)
"""
import os
import re
import httpx
import chainlit as cl

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("MUSICALO_API_KEY", "").strip()
_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
_TIMEOUT = 90  # segundos — las respuestas de IA pueden tardar


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _user_id() -> str:
    """ID de sesión único por pestaña de navegador."""
    return str(abs(hash(cl.context.session.id)) % 10**9)


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


async def _send_response(data: dict):
    """Envía el texto + botones de una respuesta de la API como mensaje Chainlit."""
    text = _html_to_md(data.get("text", ""))
    actions = _build_actions(data.get("actions", []))
    await cl.Message(content=text, actions=actions).send()


# ---------------------------------------------------------------------------
# Handlers de Chainlit
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("user_id", _user_id())

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
    # Mostrar indicador de espera
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

    # Reemplazar el mensaje de espera con la respuesta real
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
