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
# Espera antes de la PRIMERA comprobación tras arrancar (no en las siguientes).
# Evita que cada redeploy dispare un escaneo completo de la biblioteca contra
# MusicBrainz justo cuando más se está usando la app en ese momento (visto en
# producción: 559 artistas escaneados a la vez que una conversación en curso,
# MusicBrainz devolviendo 503 y la conversación acabando en timeout).
_INITIAL_DELAY_SECONDS = max(0, int(os.getenv("RELEASES_INITIAL_DELAY_MINUTES", "10"))) * 60

# "Artistas" que en realidad son un cajón de sastre de recopilatorios, no un
# artista real cuyos lanzamientos tenga sentido avisar. Ampliable vía env si
# hiciera falta más adelante.
_EXCLUDED_ARTISTS = {
    name.strip().lower()
    for name in os.getenv("RELEASES_EXCLUDED_ARTISTS", "Various Artists").split(",")
    if name.strip()
}

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
    artist_names = [
        a.name for a in artists
        if a.name and a.name.strip().lower() not in _EXCLUDED_ARTISTS
    ]
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
    """Bucle: comprueba cada RELEASES_CHECK_INTERVAL_HOURS horas (default 24).

    Espera RELEASES_INITIAL_DELAY_MINUTES (default 10) antes de la primera
    pasada, para no competir con el tráfico justo después de un redeploy.
    Para probarlo sin esperar, usa trigger_check_now() (p.ej. desde un
    endpoint manual) en vez de bajar este valor a 0.
    """
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
            "Ningún canal de notificación configurado (NTFY_TOPIC / TELEGRAM_NOTIFY_CHAT_ID) - "
            "release watcher queda inactivo, se puede configurar más tarde sin reiniciar nada"
        )

    try:
        if _INITIAL_DELAY_SECONDS:
            logger.info(f"🔔 Primera comprobación de lanzamientos en {_INITIAL_DELAY_SECONDS // 60} min")
            await asyncio.sleep(_INITIAL_DELAY_SECONDS)

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


async def trigger_check_now() -> int:
    """Ejecuta una comprobación inmediata, fuera del bucle periódico - para
    probar manualmente (p.ej. desde un endpoint) sin esperar al intervalo
    normal ni bajar RELEASES_INITIAL_DELAY_MINUTES a 0.

    Usa instancias propias y de vida corta (no las del bucle de fondo, que
    puede que todavía esté en su espera inicial) y las cierra al terminar.
    """
    navidrome = NavidromeService()
    musicbrainz = MusicBrainzService()
    notifier = NotificationService()
    try:
        return await check_once(navidrome, musicbrainz, notifier)
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
