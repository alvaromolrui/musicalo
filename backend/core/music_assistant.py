"""
MusicAssistant: núcleo de la lógica de negocio, agnóstico de la interfaz de usuario.

Este módulo no importa nada de telegram ni de ningún framework de UI.
Puede ser consumido por TelegramService, FastAPI, Chainlit o cualquier otro adaptador.
"""
import os
import random
import logging
from typing import Optional, List

from models.schemas import Recommendation, Track, UserProfile
from models.responses import AssistantResponse, AssistantAction, RecommendParams, ShareResult
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.koito_service import KoitoService
from services.setlistfm_service import SetlistfmService
from services.ai_service import MusicRecommendationService
from services.playlist_service import PlaylistService
from services.music_agent_service import MusicAgentService
from services.conversation_manager import ConversationManager
from services.analytics_system import analytics_system

logger = logging.getLogger(__name__)


class MusicAssistant:
    """
    Orquestador central de Musicalo.

    Expone métodos de alto nivel (chat, get_recommendations, create_share, ...)
    que devuelven AssistantResponse. Cualquier adaptador de UI traduce esas
    respuestas a su formato nativo.
    """

    def __init__(self):
        self.navidrome = NavidromeService()
        self.listenbrainz = ListenBrainzService()
        self.koito = KoitoService()
        self.setlistfm = SetlistfmService()
        self.ai = MusicRecommendationService()
        self.playlist_service = PlaylistService()
        self.agent = MusicAgentService()
        self.conversation_manager = ConversationManager()

        # Koito tiene prioridad si está configurado (KOITO_URL); si no, ListenBrainz
        # (LISTENBRAINZ_USERNAME). Mismo shape de datos en ambos - el resto de la
        # clase solo usa self.music_service, no le importa cuál sea.
        if os.getenv("KOITO_URL"):
            self.music_service = self.koito
            self.music_service_name = "Koito"
            logger.info("Usando Koito como servicio de escucha")
        elif os.getenv("LISTENBRAINZ_USERNAME"):
            self.music_service = self.listenbrainz
            self.music_service_name = "ListenBrainz"
            logger.info("Usando ListenBrainz como servicio de escucha")
        else:
            self.music_service = None
            self.music_service_name = None
            logger.warning("Sin servicio de scrobbling configurado")

    async def initialize(self):
        """Llamar tras construir la instancia para inicializar subsistemas async."""
        await self.ai.initialize_monitoring()

    # ------------------------------------------------------------------
    # Punto de entrada principal: lenguaje natural
    # ------------------------------------------------------------------

    async def chat(self, user_id: int, message: str) -> AssistantResponse:
        """
        Procesa un mensaje en lenguaje natural y devuelve una respuesta.

        Ya no hay un clasificador de intents previo: el agente conversacional
        (`self.agent`, con tool-calling sobre Navidrome/ListenBrainz/MusicBrainz)
        decide él mismo qué hacer con el mensaje y redacta la respuesta. Se
        conserva únicamente el atajo determinista de setlist.fm, porque es un
        match de URL sin ambigüedad (no una clasificación de lenguaje natural).
        """
        setlist_id = self.setlistfm.parse_setlist_url(message)
        if setlist_id:
            return await self._build_setlist_playlist(setlist_id, user_id)

        return await self._agent_query(message, user_id)

    # ------------------------------------------------------------------
    # Setlist (setlist.fm) -> Playlist en Navidrome
    # ------------------------------------------------------------------

    async def _build_setlist_playlist(self, setlist_id: str, user_id: int) -> AssistantResponse:
        """Crea una playlist en Navidrome a partir de un setlist de setlist.fm.

        El fetch + emparejado + creación vive en `SetlistfmService.build_playlist_from_setlist`,
        compartido con la tool `crear_playlist_desde_setlist` del agente (búsqueda de
        conciertos por nombre) para no mantener dos copias de la misma lógica de matching.
        """
        setlist = await self.setlistfm.get_setlist(setlist_id)
        if not setlist:
            return AssistantResponse.error("No pude encontrar ese setlist en setlist.fm.")

        result = await self.setlistfm.build_playlist_from_setlist(self.navidrome, setlist)
        if not result.get("success"):
            return AssistantResponse.error(result.get("error", "No pude crear la playlist."))

        text = (
            f"Playlist creada: \"{result['playlist_name']}\"\n"
            f"{result['matched_count']} de {result['total_songs']} canciones encontradas en tu biblioteca."
        )
        if result["unmatched"]:
            text += "\n\nNo encontré en tu biblioteca:\n" + "\n".join(f"- {t}" for t in result["unmatched"])

        return AssistantResponse(text=text)

    # ------------------------------------------------------------------
    # Recomendaciones
    # ------------------------------------------------------------------

    async def get_recommendations(self, user_id: int, params: RecommendParams) -> list:
        """Devuelve list[Recommendation]."""
        if params.similar_to:
            return await self._get_similar_recommendations(params)
        return await self._get_profile_recommendations(params)

    async def _get_similar_recommendations(self, params: RecommendParams) -> list:
        if not self.music_service:
            return []

        search_limit = max(30, params.limit * 5)
        similar_artists = await self.music_service.get_similar_artists_from_recording(
            params.similar_to,
            limit=search_limit,
            musicbrainz_service=self.agent.musicbrainz,
        )

        if not similar_artists:
            return []

        top, rest = similar_artists[:5], similar_artists[5:]
        random.shuffle(rest)
        candidates = top + rest

        recommendations = []
        for artist in candidates:
            if len(recommendations) >= params.limit:
                break

            title = ""
            album_name = ""
            artist_url = artist.url or ""
            reason = ""

            if params.rec_type == "album":
                top_albums = (
                    await self.agent.musicbrainz.get_artist_top_albums_enhanced(artist.name, limit=1)
                    if self.agent.musicbrainz
                    else []
                )
                if not top_albums:
                    continue
                album_data = top_albums[0]
                album_name = album_data.get("name", artist.name)
                title = album_name
                artist_url = album_data.get("url", artist_url)
                reason = f"Álbum top de {artist.name}, artista similar a {params.similar_to}"

            elif params.rec_type == "track":
                top_tracks = (
                    await self.agent.musicbrainz.get_artist_top_tracks_enhanced(artist.name, limit=1)
                    if self.agent.musicbrainz
                    else []
                )
                if top_tracks:
                    track_data = top_tracks[0]
                    title = track_data.get("name", f"Música de {artist.name}")
                    artist_url = track_data.get("url", artist_url)
                else:
                    title = f"Música de {artist.name}"
                reason = f"Canción top de artista similar a {params.similar_to}"

            else:
                title = artist.name
                reason = f"Similar a {params.similar_to}"

            track = Track(
                id=f"listenbrainz_similar_{artist.name.replace(' ', '_')}",
                title=title,
                artist=artist.name,
                album=album_name,
                duration=None,
                year=None,
                genre="",
                play_count=None,
                path=artist_url,
                cover_url=None,
            )
            recommendations.append(
                Recommendation(
                    track=track,
                    reason=reason,
                    confidence=0.9,
                    source="ListenBrainz+MusicBrainz",
                    tags=[],
                )
            )

        return recommendations

    async def _get_profile_recommendations(self, params: RecommendParams) -> list:
        if not self.music_service:
            return []

        recent_tracks = await self.music_service.get_recent_tracks(limit=20)
        top_artists = await self.music_service.get_top_artists(limit=10)

        if not recent_tracks:
            return []

        user_profile = UserProfile(
            recent_tracks=recent_tracks,
            top_artists=top_artists,
            favorite_genres=[],
            mood_preference="",
            activity_context="",
        )

        return await self.ai.generate_recommendations(
            user_profile,
            limit=params.limit,
            recommendation_type=params.rec_type,
            genre_filter=params.genre_filter,
            custom_prompt=params.custom_prompt,
            from_library_only=params.from_library_only,
        )

    # ------------------------------------------------------------------
    # Compartir música
    # ------------------------------------------------------------------

    async def create_share(self, search_term: str) -> Optional[ShareResult]:
        """Busca en Navidrome y crea un enlace compartible. Devuelve None si no hay resultados."""
        search_term = " ".join(search_term.split())
        variations = self._search_variations(search_term.lower())

        results = None
        used_flexible = False

        for variation in variations:
            temp = await self.navidrome.search(variation, limit=20)
            if temp.get("albums") or temp.get("tracks") or temp.get("artists"):
                results = temp
                if variation != search_term.lower():
                    used_flexible = True
                break

        if not results:
            results = await self.navidrome.search(search_term, limit=20)

        items_to_share = []
        share_type = ""
        found_name = ""

        if results.get("albums"):
            album = results["albums"][0]
            found_name = f"{album.artist} - {album.name}"
            share_type = "álbum"
            tracks = await self.navidrome.get_album_tracks(album.id)
            items_to_share = [t.id for t in tracks]

        elif results.get("tracks"):
            track = results["tracks"][0]
            found_name = f"{track.artist} - {track.title}"
            share_type = "canción"
            items_to_share = [track.id]

        elif results.get("artists"):
            artist = results["artists"][0]
            found_name = artist.name
            share_type = "artista"
            artist_tracks = await self.navidrome.search(artist.name, limit=500)
            name_lower = artist.name.lower().strip()
            items_to_share = [
                t.id
                for t in artist_tracks.get("tracks", [])
                if name_lower in t.artist.lower() or t.artist.lower() in name_lower
            ]

        # Fallback: búsqueda flexible palabra a palabra
        if not items_to_share:
            words = search_term.split()
            if len(words) > 1:
                alt = await self.navidrome.search(words[0], limit=20)
                for album in alt.get("albums", []):
                    if any(w.lower() in album.name.lower() or w.lower() in album.artist.lower() for w in words):
                        found_name = f"{album.artist} - {album.name}"
                        share_type = "álbum"
                        tracks = await self.navidrome.get_album_tracks(album.id)
                        items_to_share = [t.id for t in tracks]
                        used_flexible = True
                        break
                if not items_to_share:
                    for track in alt.get("tracks", []):
                        if any(w.lower() in track.title.lower() or w.lower() in track.artist.lower() for w in words):
                            found_name = f"{track.artist} - {track.title}"
                            share_type = "canción"
                            items_to_share = [track.id]
                            used_flexible = True
                            break

        if not items_to_share:
            return None

        share_info = await self.navidrome.create_share(
            items_to_share,
            description=f"Compartido desde Musicalo: {found_name}",
        )

        if not share_info:
            return None

        return ShareResult(
            url=share_info["url"],
            id=share_info["id"],
            item_count=len(items_to_share),
            found_name=found_name,
            share_type=share_type,
            used_flexible_search=used_flexible,
        )

    # ------------------------------------------------------------------
    # Feedback de recomendaciones
    # ------------------------------------------------------------------

    async def process_feedback(self, user_id: int, track_id: str, feedback_type: str) -> None:
        from datetime import datetime
        await self.ai.process_recommendation_feedback(
            user_id=user_id,
            recommendation_id=track_id,
            feedback_type=feedback_type,
            recommendation_context={"timestamp": datetime.now().isoformat()},
        )

    # ------------------------------------------------------------------
    # Biblioteca
    # ------------------------------------------------------------------

    async def get_library_items(self, category: str, limit: int = 15) -> AssistantResponse:
        if category == "tracks":
            items = await self.navidrome.get_tracks(limit=limit + 5)
            text = "<b>Canciones de tu biblioteca:</b>\n\n"
            for i, t in enumerate(items[:limit], 1):
                text += f"{i}. {t.artist} - {t.title}\n"

        elif category == "albums":
            items = await self.navidrome.get_albums(limit=limit + 5)
            text = "<b>Álbumes de tu biblioteca:</b>\n\n"
            for i, a in enumerate(items[:limit], 1):
                text += f"{i}. {a.artist} - {a.name}\n"

        elif category == "artists":
            items = await self.navidrome.get_artists(limit=limit + 5)
            text = "<b>Artistas de tu biblioteca:</b>\n\n"
            for i, a in enumerate(items[:limit], 1):
                text += f"{i}. {a.name}\n"

        else:
            return AssistantResponse.error(f"Categoría no reconocida: {category}")

        return AssistantResponse(text=text)

    # ------------------------------------------------------------------
    # Estadísticas
    # ------------------------------------------------------------------

    async def get_stats_for_period(self, period: str) -> AssistantResponse:
        if not self.music_service:
            return AssistantResponse.error("No hay servicio de scrobbling configurado.")

        period_names = {
            "this_week": "Esta Semana",
            "this_month": "Este Mes",
            "this_year": "Este Año",
            "last_week": "Semana Pasada",
            "last_month": "Mes Pasado",
            "last_year": "Año Pasado",
            "all_time": "Todo el Tiempo",
        }
        period_name = period_names.get(period, "Este Mes")

        top_artists = await self.music_service.get_top_artists(period=period, limit=10)
        top_tracks = (
            await self.music_service.get_top_tracks(period=period, limit=5)
            if hasattr(self.music_service, "get_top_tracks")
            else []
        )
        recent_tracks = await self.music_service.get_recent_tracks(limit=5)
        top_albums = (
            await self.music_service.get_top_albums(period=period, limit=5)
            if hasattr(self.music_service, "get_top_albums")
            else []
        )

        text = f"<b>Estadísticas de {period_name}</b>\n<i>{self.music_service_name}</i>\n\n"

        if top_artists:
            text += "<b>Top 5 Artistas:</b>\n"
            for i, a in enumerate(top_artists[:5], 1):
                text += f"{i}. {a.name} - {a.playcount} escuchas\n"
            text += "\n"

        if top_albums:
            text += "<b>Top 3 Álbumes:</b>\n"
            for i, a in enumerate(top_albums[:3], 1):
                text += f"{i}. {a['artist']} - {a['name']} ({a['listen_count']} escuchas)\n"
            text += "\n"

        if top_tracks:
            text += "<b>Top 3 Canciones:</b>\n"
            for i, t in enumerate(top_tracks[:3], 1):
                text += f"{i}. {t.artist} - {t.name} ({t.playcount} escuchas)\n"
            text += "\n"

        if recent_tracks:
            text += "<b>Última escucha:</b>\n"
            text += f"{recent_tracks[0].artist} - {recent_tracks[0].name}\n"

        return AssistantResponse(text=text)

    async def get_user_stats_summary(self) -> dict:
        """Estadísticas generales del usuario (total de escuchas, artistas, etc.)"""
        if not self.music_service:
            return {}
        if hasattr(self.music_service, "get_user_stats"):
            return await self.music_service.get_user_stats()
        return {}

    async def get_listening_activity(self, days: int = 30) -> dict:
        if self.music_service and hasattr(self.music_service, "get_listening_activity"):
            return await self.music_service.get_listening_activity(days=days)
        return {}

    # ------------------------------------------------------------------
    # Sistema / salud / analytics
    # ------------------------------------------------------------------

    def get_health(self) -> dict:
        return self.ai.get_health_status()

    def get_system_health(self) -> dict:
        return self.ai.get_system_health()

    async def get_analytics(self) -> dict:
        return await analytics_system.get_system_insights()

    async def get_insights(self, user_id: int) -> dict:
        return await self.ai.get_user_learning_insights(user_id)

    # ------------------------------------------------------------------
    # Perfil de usuario (para hybrid/profile/discover)
    # ------------------------------------------------------------------

    async def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        if not self.music_service:
            return None
        recent_tracks = await self.music_service.get_recent_tracks(limit=20)
        top_artists = await self.music_service.get_top_artists(limit=10)
        if not recent_tracks:
            return None
        return UserProfile(
            recent_tracks=recent_tracks,
            top_artists=top_artists,
            favorite_genres=[],
            mood_preference="",
            activity_context="",
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _agent_query(self, query: str, user_id: int, context: dict = None) -> AssistantResponse:
        result = await self.agent.query(query, user_id=user_id, context=context or {})
        if result.get("success") and result.get("answer"):
            answer = result["answer"]
            links = result.get("links", [])
            if links:
                answer += "\n\n<b>Enlaces relevantes:</b>\n"
                for link in links[:5]:
                    answer += f"• {link}\n"
            return AssistantResponse(text=answer)
        return AssistantResponse.error("No pude procesar tu consulta en este momento.")

    def _format_recommendations(
        self,
        recommendations: list,
        similar_to: str = None,
        custom_prompt: str = None,
        rec_type: str = "general",
        genre_filter: str = None,
        from_library: bool = False,
    ) -> AssistantResponse:
        if not recommendations:
            return AssistantResponse.error("No pude generar recomendaciones en este momento.")

        if custom_prompt:
            text = f"<b>Recomendaciones para:</b> <i>{custom_prompt}</i>\n\n"
        elif similar_to:
            text = f"<b>Música similar a '{similar_to}':</b>\n\n"
        elif rec_type == "album":
            text = f"<b>Álbumes recomendados{f' de {genre_filter}' if genre_filter else ''}:</b>\n\n"
        elif rec_type == "artist":
            text = f"<b>Artistas recomendados{f' de {genre_filter}' if genre_filter else ''}:</b>\n\n"
        elif rec_type == "track":
            text = f"<b>Canciones recomendadas{f' de {genre_filter}' if genre_filter else ''}:</b>\n\n"
        else:
            text = "<b>Tus recomendaciones personalizadas:</b>\n\n"

        for i, rec in enumerate(recommendations, 1):
            if rec_type == "album":
                text += f"<b>{i}. {rec.track.title}</b>\n   🎤 Artista: {rec.track.artist}\n"
            elif rec_type == "artist":
                text += f"<b>{i}. 🎤 {rec.track.artist}</b>\n"
            else:
                text += f"<b>{i}.</b> {rec.track.artist} - {rec.track.title}\n"
                if rec.track.album:
                    text += f"   📀 {rec.track.album}\n"

            text += f"   💡 {rec.reason}\n"
            if rec.source:
                text += f"   🔗 Fuente: {rec.source}\n"
            if rec.track.path:
                if "musicbrainz.org" in rec.track.path:
                    svc = "MusicBrainz"
                elif "listenbrainz.org" in rec.track.path:
                    svc = "ListenBrainz"
                else:
                    svc = "Ver información"
                text += f"   🌐 <a href=\"{rec.track.path}\">Ver en {svc}</a>\n"
            text += f"   🎯 {int(rec.confidence * 100)}% match\n\n"

        actions = [
            AssistantAction(id="like_rec", label="❤️ Me gusta"),
            AssistantAction(id="dislike_rec", label="👎 No me gusta"),
            AssistantAction(id="more_recommendations", label="🔄 Más recomendaciones"),
        ]

        return AssistantResponse(text=text, actions=actions, recommendations=recommendations)

    def _search_variations(self, search_term: str) -> list:
        variations = [search_term]
        if search_term.endswith("s") and len(search_term) > 2:
            variations.append(search_term[:-1])
        if "qu" in search_term or "c" in search_term:
            variant = search_term.replace("qu", "k").replace("c", "k")
            variations.append(variant)
            if variant.endswith("s"):
                variations.append(variant[:-1])
        if "k" in search_term:
            variations.append(search_term.replace("k", "qu"))
            variations.append(search_term.replace("k", "c"))
        words = search_term.split()
        if len(words) > 1:
            variations.extend(words)
            variations.append(" ".join(reversed(words)))
        return list(set(v for v in variations if v and len(v) > 1))
