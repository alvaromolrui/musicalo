"""
KoitoService: cliente para un servidor Koito auto-hospedado (https://koito.io),
como alternativa a ListenBrainzService para datos de escucha.

Expone la misma interfaz pública que ListenBrainzService (los métodos que
realmente usa el resto de la app: get_recent_tracks, get_top_artists,
get_top_tracks, get_top_albums, get_user_stats, get_listening_activity,
get_similar_artists_from_recording) para poder intercambiarlas por config
sin tocar music_assistant.py ni music_agent_service.py.

Diferencias de fondo con ListenBrainz:
- Koito es de un solo usuario (auto-hospedado): no hay username en las URLs,
  la API key ya identifica al usuario. No hay collaborative filtering (no
  hay otros usuarios con los que comparar) - get_similar_artists_from_recording
  usa directamente MusicBrainz (tags) y, si eso falla, IA como último recurso.
- Los campos de la API se confirmaron leyendo el código fuente de Koito
  (internal/models/*.go, internal/db/sqlite/*.go) en la rama main de
  https://github.com/gabehf/koito, no documentación pública (no la hay
  detallada). Merece la pena validar contra tu instancia si algo no cuadra.
"""
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from models.schemas import ScrobbleTrack, ScrobbleArtist


class KoitoService:
    def __init__(self):
        self.base_url = (os.getenv("KOITO_URL") or "").rstrip("/")
        self.api_key = os.getenv("KOITO_API_KEY")
        import httpx
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Realizar petición a la API web de Koito (/apis/web/v1/...)"""
        if not self.base_url:
            raise ValueError("KOITO_URL no está configurado")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"

        try:
            response = await self.client.get(
                f"{self.base_url}/apis/web/v1/{endpoint}",
                params={k: v for k, v in (params or {}).items() if v is not None},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error en petición Koito ({endpoint}): {e}")
            raise

    @staticmethod
    def _period_to_params(period: str) -> Dict[str, Any]:
        """Traduce el vocabulario de periodo de la app (this_month, last_week...) a lo
        que entiende Koito: period=day|week|month|year|all_time para el periodo ACTUAL,
        o from/to (unix timestamps) para rangos pasados - así evitamos depender de cómo
        Koito calcule "la semana/mes/año número N", que no está documentado.
        """
        p = (period or "this_month").lower().strip()
        now = datetime.now()

        if p == "all_time":
            return {"period": "all_time"}
        if p == "this_week":
            return {"period": "week"}
        if p == "this_month":
            return {"period": "month"}
        if p == "this_year":
            return {"period": "year"}

        if p == "last_week":
            this_week_start = now - timedelta(days=now.weekday())
            start = this_week_start - timedelta(days=7)
            return {"from": int(start.timestamp()), "to": int(this_week_start.timestamp())}
        if p == "last_month":
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = first_this_month - timedelta(seconds=1)
            last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return {"from": int(last_month_start.timestamp()), "to": int(first_this_month.timestamp())}
        if p == "last_year":
            start = datetime(now.year - 1, 1, 1)
            end = datetime(now.year, 1, 1)
            return {"from": int(start.timestamp()), "to": int(end.timestamp())}

        # Desconocido: cae a "este mes"
        return {"period": "month"}

    @staticmethod
    def _artist_names(item: Dict[str, Any]) -> str:
        return ", ".join(a.get("name", "") for a in item.get("artists", []) if a.get("name")) or "Desconocido"

    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Interfaz compartida con ListenBrainzService
    # ------------------------------------------------------------------

    async def get_recent_tracks(self, limit: int = 50) -> List[ScrobbleTrack]:
        """Obtener escuchas recientes del usuario, más reciente primero.

        Nota: a diferencia de los demás métodos, este es el único que no tenía
        ningún periodo/rango en la petición - si Koito interpreta "sin periodo"
        como from=0 (1970) en vez de "sin filtro", eso devolvería siempre vacío.
        Se manda `period=all_time` explícito para evitar esa ambigüedad.
        """
        try:
            data = await self._make_request("listens", {"limit": limit, "page": 1, "period": "all_time"})
            tracks = []
            for entry in data.get("items", []):
                track_data = entry.get("track", {})
                image = track_data.get("image") or {}
                tracks.append(ScrobbleTrack(
                    name=track_data.get("title", ""),
                    artist=self._artist_names(track_data),
                    album=None,  # /listens devuelve SimpleTrack, sin nombre de álbum
                    playcount=1,
                    date=self._parse_iso(entry.get("time")),
                    url=None,
                    image_url=image.get("medium") or None,
                ))
            return tracks
        except Exception as e:
            print(f"Error obteniendo tracks recientes de Koito: {e}")
            return []

    async def get_top_artists(self, period: str = "this_month", limit: int = 50) -> List[ScrobbleArtist]:
        """Artistas más escuchados en un periodo."""
        try:
            params = {"limit": limit, **self._period_to_params(period)}
            data = await self._make_request("top/artists", params)
            artists = []
            for entry in data.get("items", []):
                item = entry.get("item", {})
                mbid = item.get("musicbrainz_id")
                artists.append(ScrobbleArtist(
                    name=item.get("name", ""),
                    playcount=item.get("listen_count", 0),
                    url=f"https://musicbrainz.org/artist/{mbid}" if mbid else "",
                    rank=entry.get("rank"),
                ))
            return artists
        except Exception as e:
            print(f"Error obteniendo top artistas de Koito: {e}")
            return []

    async def get_top_tracks(self, period: str = "this_month", limit: int = 50) -> List[ScrobbleTrack]:
        """Canciones más escuchadas en un periodo."""
        try:
            params = {"limit": limit, **self._period_to_params(period)}
            data = await self._make_request("top/tracks", params)
            tracks = []
            for entry in data.get("items", []):
                item = entry.get("item", {})
                mbid = item.get("musicbrainz_id")
                image = item.get("image") or {}
                tracks.append(ScrobbleTrack(
                    name=item.get("title", ""),
                    artist=self._artist_names(item),
                    album=None,  # el Track de Koito solo trae album_id, no el título
                    playcount=item.get("listen_count", 0),
                    date=None,
                    url=f"https://musicbrainz.org/recording/{mbid}" if mbid else None,
                    image_url=image.get("medium") or None,
                ))
            return tracks
        except Exception as e:
            print(f"Error obteniendo top tracks de Koito: {e}")
            return []

    async def get_top_albums(self, period: str = "this_month", limit: int = 50) -> List[Dict[str, Any]]:
        """Álbumes más escuchados en un periodo (dicts planos, igual que ListenBrainzService)."""
        try:
            params = {"limit": limit, **self._period_to_params(period)}
            data = await self._make_request("top/albums", params)
            albums = []
            for entry in data.get("items", []):
                item = entry.get("item", {})
                mbid = item.get("musicbrainz_id")
                artist_name = self._artist_names(item)
                if item.get("is_various_artists") and artist_name == "Desconocido":
                    artist_name = "Varios artistas"
                albums.append({
                    "name": item.get("title", ""),
                    "artist": artist_name,
                    "listen_count": item.get("listen_count", 0),
                    "mbid": mbid,
                    "url": f"https://musicbrainz.org/release-group/{mbid}" if mbid else "",
                })
            return albums
        except Exception as e:
            print(f"Error obteniendo top álbumes de Koito: {e}")
            return []

    async def get_user_stats(self, period: str = "all_time") -> Dict[str, Any]:
        """Estadísticas generales del usuario, vía /summary (agregado en el propio Koito)."""
        try:
            params = self._period_to_params(period)
            data = await self._make_request("summary", params)
            return {
                "total_listens": data.get("plays", 0),
                "total_artists": data.get("unique_artists"),
                "total_albums": data.get("unique_albums"),
                "total_tracks": data.get("unique_tracks"),
                "period": period,
                "minutes_listened": data.get("minutes_listened"),
                "avg_plays_per_day": data.get("avg_plays_per_day"),
                "new_artists": data.get("new_artists"),
                "new_albums": data.get("new_albums"),
                "new_tracks": data.get("new_tracks"),
            }
        except Exception as e:
            print(f"Error obteniendo estadísticas de Koito: {e}")
            return {}

    async def get_listening_activity(self, days: int = 30) -> Dict[str, Any]:
        """Actividad de escucha por día, en los últimos `days` días."""
        try:
            now = datetime.now()
            start = now - timedelta(days=days)
            data = await self._make_request("listen-activity", {
                "from": int(start.timestamp()),
                "to": int(now.timestamp()),
            })
            daily_activity: Dict[str, int] = {}
            for item in data.get("activity", []):
                dt = self._parse_iso(item.get("start_time"))
                if dt:
                    daily_activity[dt.strftime("%Y-%m-%d")] = item.get("listens", 0)

            return {
                "daily_listens": daily_activity,
                "total_days": len(daily_activity),
                "avg_daily_listens": sum(daily_activity.values()) / max(len(daily_activity), 1),
            }
        except Exception as e:
            print(f"Error obteniendo actividad de Koito: {e}")
            return {}

    async def get_similar_artists_from_recording(
        self,
        artist_name: str,
        limit: int = 10,
        musicbrainz_service=None,
    ) -> List[ScrobbleArtist]:
        """Artistas similares a uno dado.

        Koito no tiene collaborative filtering (es de un solo usuario, no hay
        con quién comparar gustos), así que a diferencia de ListenBrainzService
        aquí se salta directo a las estrategias que sí tienen sentido:
        1. MusicBrainz (tags/géneros), si hay musicbrainz_service disponible.
        2. IA (conocimiento general del modelo), como último recurso.
        """
        similar_artists: List[ScrobbleArtist] = []

        if musicbrainz_service:
            try:
                tag_similar = await musicbrainz_service.find_similar_by_tags(artist_name, limit=limit)
                if tag_similar:
                    for i, artist_data in enumerate(tag_similar):
                        similar_artists.append(ScrobbleArtist(
                            name=artist_data["name"],
                            playcount=0,
                            rank=i + 1,
                            url=f"https://musicbrainz.org/artist/{artist_data['mbid']}" if artist_data.get("mbid") else "",
                        ))
                    print(f"✅ Encontrados {len(similar_artists)} artistas similares por tags (MusicBrainz)")
                    return similar_artists
            except Exception as e:
                print(f"⚠️ Error buscando similares por tags en MusicBrainz: {e}")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            prompt = (
                f"Eres un experto en música. Genera una lista de {limit} artistas similares a "
                f'"{artist_name}".\n\n'
                "IMPORTANTE:\n"
                "- Genera SOLO nombres de artistas/bandas, uno por línea\n"
                "- NO agregues numeración, guiones, ni explicaciones\n"
                "- Solo artistas reales y verificables\n"
                "- Artistas musicalmente similares en estilo, género o época\n\n"
                f"Genera {limit} artistas similares a {artist_name}:"
            )
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=300,
                    top_p=0.8,
                    # No se le pasan tools; desactivar AFC evita el aviso del SDK
                    # ("Direct use of AFC in AsyncModels.generate_content...") y
                    # el overhead de su bucle de function-calling para nada.
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            ai_response = (response.text or "").strip()

            for line in ai_response.split("\n"):
                if len(similar_artists) >= limit:
                    break
                line = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
                line = re.sub(r"^[-*]\s*", "", line)
                if line and len(line) > 2:
                    similar_artists.append(ScrobbleArtist(name=line, playcount=0, rank=len(similar_artists) + 1, url=""))

            if similar_artists:
                print(f"✅ Encontrados {len(similar_artists)} artistas similares usando IA")
        except Exception as e:
            print(f"⚠️ Error usando IA para similares: {e}")

        return similar_artists

    async def close(self):
        await self.client.aclose()
