"""
NotificationService: envío de notificaciones push, desacoplado del canal.

Implementa ntfy y Telegram (envío directo vía Bot API, sin necesidad de que
el bot interactivo esté corriendo - por eso funciona igual en START_MODE=api).
NotificationService manda por todos los canales que estén configurados a la
vez; quien la usa (el release watcher) no necesita saber cuáles hay.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class NtfyChannel:
    """Cliente mínimo para la API HTTP de ntfy (https://docs.ntfy.sh/publish/)."""

    def __init__(self):
        self.base_url = (os.getenv("NTFY_URL") or "https://ntfy.sh").rstrip("/")
        self.topic = os.getenv("NTFY_TOPIC")
        self.token = os.getenv("NTFY_TOKEN")  # opcional: auth de instancias auto-hospedadas
        self.client = httpx.AsyncClient(timeout=10.0)

    @property
    def configured(self) -> bool:
        return bool(self.topic)

    async def send(
        self,
        message: str,
        url: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> bool:
        """Publica una notificación. Devuelve True si ntfy la aceptó.

        El título/mensaje va siempre en el body (UTF-8 sin restricciones) en
        vez de en la cabecera `Title`, para no depender de que ntfy/httpx
        acepten bien tildes/emojis en cabeceras HTTP.
        """
        if not self.configured:
            return False
        headers = {}
        if url:
            headers["Click"] = url
        if tags:
            headers["Tags"] = tags
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = await self.client.post(
                f"{self.base_url}/{self.topic}",
                content=message.encode("utf-8"),
                headers=headers,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Error enviando notificación por ntfy: {e}")
            return False

    async def close(self):
        await self.client.aclose()


class TelegramChannel:
    """Envío directo a la Bot API de Telegram (sendMessage), sin depender de
    que el bot interactivo esté corriendo (funciona en START_MODE=api solo)."""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        # Por defecto, el primer ID de TELEGRAM_ALLOWED_USER_IDS (en un bot privado
        # de un solo usuario, tu chat_id de DM es tu propio user id) - se puede
        # sobreescribir con TELEGRAM_NOTIFY_CHAT_ID si se quiere mandar a otro sitio
        # (p.ej. un grupo).
        self.chat_id = os.getenv("TELEGRAM_NOTIFY_CHAT_ID") or self._first_allowed_user_id()
        self.client = httpx.AsyncClient(timeout=10.0)

    @staticmethod
    def _first_allowed_user_id() -> Optional[str]:
        raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        first = raw.split(",")[0].strip()
        return first or None

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send(self, message: str, url: Optional[str] = None, tags: Optional[str] = None) -> bool:
        if not self.configured:
            return False
        text = f"{message}\n\n{url}" if url else message
        try:
            response = await self.client.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Error enviando notificación por Telegram: {e}")
            return False

    async def close(self):
        await self.client.aclose()


class NotificationService:
    """Punto único de envío de notificaciones de la app - manda por todos los
    canales configurados a la vez (hoy: ntfy, Telegram)."""

    def __init__(self):
        self.ntfy = NtfyChannel()
        self.telegram = TelegramChannel()
        self._channels = [self.ntfy, self.telegram]

    @property
    def configured(self) -> bool:
        return any(c.configured for c in self._channels)

    async def send(self, message: str, url: Optional[str] = None, tags: Optional[str] = None) -> bool:
        """Manda por todos los canales configurados. Devuelve True si al menos uno lo aceptó."""
        results = [await c.send(message, url=url, tags=tags) for c in self._channels if c.configured]
        return any(results)

    async def close(self):
        for c in self._channels:
            await c.close()
