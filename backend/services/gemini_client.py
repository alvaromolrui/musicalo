"""
Punto único de acceso a Gemini (SDK `google-genai`).

Centraliza tres cosas que antes estaban repetidas en cada servicio:

- **Modelo**: `GEMINI_MODEL` (default `gemini-2.5-flash`). Cambiar de modelo es
  cambiar una variable de entorno, no buscar el nombre por todo el código.
- **Razonamiento**: `GEMINI_THINKING_LEVEL` opcional (`minimal`/`low`/`medium`/
  `high`). Solo se envía si está seteada, porque los modelos 2.5 no aceptan
  `thinking_level` (solo la serie 3 en adelante). Nunca se usa `thinking_budget`:
  Google lo retira y los modelos nuevos responden 400 si llega.
- **Sin parámetros de muestreo**: no se envían `temperature`/`top_p`/`top_k`.
  Desde Gemini 3.6 Flash se ignoran y los modelos siguientes los rechazan con 400.
  Tampoco se pone `max_output_tokens` por defecto: en los modelos con
  razonamiento, el "thinking" consume de ese mismo tope y un límite bajo (300,
  800) acababa en respuestas vacías o cortadas.
"""
import os
import logging
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
THINKING_LEVEL = (os.getenv("GEMINI_THINKING_LEVEL") or "").strip().lower() or None

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Cliente compartido (se crea la primera vez que se usa, no al importar)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


def build_config(**kwargs) -> types.GenerateContentConfig:
    """`GenerateContentConfig` con los criterios comunes del proyecto.

    Desactiva siempre el *automatic function calling* del SDK (aquí las tools
    son async y se orquestan a mano, ver `MusicAgentService`) y añade
    `thinking_level` solo si `GEMINI_THINKING_LEVEL` está configurada.
    """
    kwargs.setdefault(
        "automatic_function_calling",
        types.AutomaticFunctionCallingConfig(disable=True),
    )
    if THINKING_LEVEL and "thinking_config" not in kwargs:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=THINKING_LEVEL)
    return types.GenerateContentConfig(**kwargs)


async def generate_text(prompt: str, **config_kwargs) -> str:
    """Genera texto a partir de un prompt simple (sin tools ni historial).

    Devuelve "" si el modelo no produce texto (bloqueo de seguridad, respuesta
    vacía...) en vez de lanzar excepción, igual que hacía cada llamador a mano
    con el SDK anterior.
    """
    response = await get_client().aio.models.generate_content(
        model=MODEL_NAME, contents=prompt, config=build_config(**config_kwargs),
    )
    return (response.text or "").strip()


def generate_text_sync(prompt: str, **config_kwargs) -> str:
    """Versión síncrona de `generate_text`, para los métodos que no son async."""
    response = get_client().models.generate_content(
        model=MODEL_NAME, contents=prompt, config=build_config(**config_kwargs),
    )
    return (response.text or "").strip()
