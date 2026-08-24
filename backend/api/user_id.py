"""Resolución del identificador de sesión (string) al int que usa MusicAssistant."""
import hashlib


def resolve_uid(raw: str) -> int:
    """Convierte un user_id de la API (string, p.ej. "musicalo:abc-123-thread-id"
    desde Chainlit, o un id numérico de Telegram) al int que espera MusicAssistant.

    No usa hash() de Python: está salteado por proceso (PYTHONHASHSEED aleatorio
    por defecto), así que el mismo string daría un id distinto en cada reinicio
    del contenedor - la conversación "se olvidaría de sí misma" en cada redeploy.
    Con md5 el mismo string siempre da el mismo id, entre reinicios incluidos.
    """
    if raw.isdigit():
        return int(raw)
    return int(hashlib.md5(raw.encode("utf-8")).hexdigest()[:12], 16)
