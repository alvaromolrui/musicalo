"""
ReleaseWatcher: comprueba periódicamente si hay lanzamientos nuevos de los
artistas de la biblioteca y avisa por notificación push (ntfy hoy, vía
NotificationService).

No usa el agente conversacional ni Gemini - es un trabajo de datos plano:
biblioteca completa -> MusicBrainzService.get_recent_releases_for_artists()
(ya existe y ya agrupa por lotes) -> filtrar los ya avisados -> notificar.

Arranca como tarea de fondo del propio event loop (asyncio.create_task),
sin APScheduler ni el JobQueue de python-telegram-bot: un simple bucle con
sleep es suficiente para "una vez al día" y no añade dependencias nuevas.
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Set, Any, Dict, List

from services.navidrome_service import NavidromeService
from services.musicbrainz_service import MusicBrainzService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

_STATE_FILE = Path(os.getenv("RELEASES_STATE_FILE", "/app/logs/notified_releases.json"))
_CHECK_INTERVAL_SECONDS = max(1, int(os.getenv("RELEASES_CHECK_INTERVAL_HOURS", "24"))) * 3600
_LOOKBACK_DAYS = int(os.getenv("RELEASES_LOOKBACK_DAYS", "30"))

_started = False  # evita arrancar el bucle dos veces si algún día se arranca desde dos sitios


def _load_notified() -> Set[str]:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            return set(data.get("notified_mbids", []))
    except Exception as e:
        logger.warning(f"No se pudo leer el estado de releases notificados: {e}")
    return set()


def _save_notified(mbids: Set[str]):
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps({"notified_mbids": sorted(mbids)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"No se pudo guardar el estado de releases notificados: {e}")


async def check_once(
    navidrome: NavidromeService,
    musicbrainz: MusicBrainzService,
    notifier: NotificationService,
) -> int:
    """Ejecuta una comprobación. Devuelve cuántas notificaciones se mandaron."""
    if not notifier.configured:
        logger.info("NTFY_TOPIC no configurado - release watcher no manda nada en esta pasada")
        return 0

    artists = await navidrome.get_all_artists()
    artist_names = [a.name for a in artists if a.name]
    if not artist_names:
        logger.info("Biblioteca sin artistas - nada que comprobar")
        return 0

    releases: List[Dict[str, Any]] = await musicbrainz.get_recent_releases_for_artists(
        artist_names, days=_LOOKBACK_DAYS
    )

    notified = _load_notified()
    new_releases = [r for r in releases if r.get("mbid") and r["mbid"] not in notified]

    sent = 0
    for release in new_releases:
        artist = release.get("artist", "?")
        title = release.get("title", "?")
        date = release.get("date", "?")
        rel_type = (release.get("type") or "álbum").lower()
        ok = await notifier.send(
            message=f"🎵 Nuevo lanzamiento: {artist} - {title} ({rel_type}, {date})",
            url=release.get("url"),
            tags="musical_note,new",
        )
        if ok:
            notified.add(release["mbid"])
            sent += 1
        else:
            # Si falló el envío, no lo marcamos como notificado - se reintenta en la próxima pasada
            logger.warning(f"No se pudo notificar el lanzamiento de {artist} - {title}")

    if sent:
        _save_notified(notified)
        logger.info(f"📢 {sent} lanzamiento(s) nuevo(s) notificado(s) por ntfy")
    else:
        logger.info(f"Sin lanzamientos nuevos ({len(releases)} encontrados en total, ya notificados)")

    return sent


async def run_forever():
    """Bucle: comprueba cada RELEASES_CHECK_INTERVAL_HOURS horas (default 24)."""
    navidrome = NavidromeService()
    musicbrainz_enabled = os.getenv("ENABLE_MUSICBRAINZ", "true").lower() == "true"
    musicbrainz = MusicBrainzService() if musicbrainz_enabled else None
    notifier = NotificationService()

    if not musicbrainz:
        logger.warning("MusicBrainz deshabilitado (ENABLE_MUSICBRAINZ=false) - release watcher no puede arrancar")
        await navidrome.close()
        await notifier.close()
        return

    if not notifier.configured:
        logger.info(
            "NTFY_TOPIC no configurado - release watcher queda inactivo "
            "(se puede configurar más tarde sin reiniciar nada, se comprueba en cada pasada)"
        )

    try:
        while True:
            try:
                await check_once(navidrome, musicbrainz, notifier)
            except Exception as e:
                logger.error(f"Error en la comprobación de lanzamientos: {e}")
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
    finally:
        await navidrome.close()
        await musicbrainz.close()
        await notifier.close()


def start_background_task():
    """Arranca el watcher como tarea de fondo del event loop en marcha.

    Idempotente: si ya se llamó en este proceso, no arranca una segunda copia
    (relevante por si algún día se invoca tanto desde la API como desde el bot
    de Telegram en el mismo proceso).
    """
    global _started
    if _started:
        return
    _started = True
    asyncio.create_task(run_forever())
    logger.info(
        f"🔔 Release watcher arrancado (cada {_CHECK_INTERVAL_SECONDS // 3600}h, "
        f"ventana de {_LOOKBACK_DAYS} días)"
    )
