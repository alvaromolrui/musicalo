import httpx
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.schemas import LastFMTrack, LastFMArtist

class ListenBrainzService:
    def __init__(self):
        self.username = os.getenv("LISTENBRAINZ_USERNAME")
        self.token = os.getenv("LISTENBRAINZ_TOKEN")  # Opcional
        self.base_url = "https://api.listenbrainz.org/1"  # API v1, no v1.0
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Realizar petición a la API de ListenBrainz"""
        if not self.username:
            raise ValueError("LISTENBRAINZ_USERNAME no está configurado")
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        
        try:
            response = await self.client.get(
                f"{self.base_url}/{endpoint}",
                params=params or {},
                headers=headers
            )
            
            if response.status_code == 404:
                print(f"⚠️ Usuario {self.username} no encontrado en ListenBrainz")
                raise ValueError(f"Usuario {self.username} no encontrado en ListenBrainz")
            
            if response.status_code == 410:
                print(f"⚠️ Usuario {self.username}: perfil no disponible o privado en ListenBrainz")
                raise ValueError(f"Perfil de {self.username} no disponible en ListenBrainz (privado o deshabilitado)")
            
            response.raise_for_status()
            return response.json()
            
        except ValueError:
            # Re-lanzar errores de validación (404, 410)
            raise
        except Exception as e:
            print(f"Error en petición ListenBrainz: {e}")
            raise
    
    async def get_recent_tracks(self, limit: int = 50) -> List[LastFMTrack]:
        """Obtener escuchas recientes del usuario"""
        try:
            params = {"count": limit}
            data = await self._make_request(f"user/{self.username}/listens", params)
            tracks = []
            
            listens = data.get("payload", {}).get("listens", [])
            if isinstance(listens, dict):
                listens = [listens]
            
            for listen in listens:
                track_metadata = listen.get("track_metadata", {})
                
                # Parsear fecha
                listened_at = listen.get("listened_at")
                date_parsed = None
                if listened_at:
                    try:
                        date_parsed = datetime.fromtimestamp(listened_at)
                    except:
                        pass
                
                track = LastFMTrack(
                    name=track_metadata.get("track_name", ""),
                    artist=track_metadata.get("artist_name", ""),
                    album=track_metadata.get("release_name"),
                    playcount=1,  # ListenBrainz no tiene playcount directo
                    date=date_parsed,
                    url=track_metadata.get("additional_info", {}).get("spotify_id"),
                    image_url=track_metadata.get("additional_info", {}).get("cover_art")
                )
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"Error obteniendo tracks recientes: {e}")
            return []
    
    async def get_top_artists(self, period: str = "this_month", limit: int = 50) -> List[LastFMArtist]:
        """Obtener artistas más escuchados usando la API de estadísticas de ListenBrainz
        
        Args:
            period: Rango de tiempo. Opciones:
                - this_week, this_month, this_year
                - last_week, last_month, last_year
                - all_time (default en la API)
            limit: Número de artistas a devolver
        """
        try:
            # Mapear period a formato de ListenBrainz (convertir espacios a guiones bajos)
            lb_range = period.replace(" ", "_").lower()
            
            params = {
                "range": lb_range,
                "count": limit
            }
            
            data = await self._make_request(f"stats/user/{self.username}/artists", params)
            
            artists = []
            artist_stats = data.get("payload", {}).get("artists", [])
            
            for i, artist_data in enumerate(artist_stats):
                artist = LastFMArtist(
                    name=artist_data.get("artist_name", ""),
                    playcount=artist_data.get("listen_count", 0),
                    url=artist_data.get("artist_mbid") and f"https://musicbrainz.org/artist/{artist_data['artist_mbid']}" or "",
                    rank=i + 1
                )
                artists.append(artist)
            
            return artists
            
        except Exception as e:
            print(f"Error obteniendo top artistas: {e}")
            return []
    
    async def get_top_tracks(self, period: str = "this_month", limit: int = 50) -> List[LastFMTrack]:
        """Obtener canciones más escuchadas usando la API de estadísticas de ListenBrainz
        
        Args:
            period: Rango de tiempo. Opciones:
                - this_week, this_month, this_year
                - last_week, last_month, last_year
                - all_time
            limit: Número de canciones a devolver
        """
        try:
            # Mapear period a formato de ListenBrainz
            lb_range = period.replace(" ", "_").lower()
            
            params = {
                "range": lb_range,
                "count": limit
            }
            
            data = await self._make_request(f"stats/user/{self.username}/recordings", params)
            
            tracks = []
            track_stats = data.get("payload", {}).get("recordings", [])
            
            for track_data in track_stats:
                track = LastFMTrack(
                    name=track_data.get("track_name", ""),
                    artist=track_data.get("artist_name", ""),
                    album=track_data.get("release_name"),
                    playcount=track_data.get("listen_count", 0),
                    date=None,
                    url=track_data.get("recording_mbid") and f"https://musicbrainz.org/recording/{track_data['recording_mbid']}" or None,
                    image_url=None
                )
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"Error obteniendo top tracks: {e}")
            return []
    
    async def get_user_stats(self, period: str = "all_time") -> Dict[str, Any]:
        """Obtener estadísticas generales del usuario
        
        Args:
            period: Rango de tiempo para las estadísticas (solo afecta contadores si la API lo soporta)
        """
        try:
            # El endpoint de stats generales no acepta parámetros de rango
            # Obtiene estadísticas de todo el tiempo del usuario
            data = await self._make_request(f"stats/user/{self.username}/listening-activity")
            
            stats = data.get("payload", {})
            
            # Calcular totales desde listening-activity
            listening_activity = stats.get("listening_activity", [])
            total_listens = sum(item.get("listen_count", 0) for item in listening_activity)
            
            return {
                "total_listens": total_listens,
                "total_artists": None,  # No disponible en este endpoint
                "total_albums": None,   # No disponible en este endpoint
                "total_tracks": None,   # No disponible en este endpoint
                "period": period,
                "from_ts": stats.get("from_ts"),
                "to_ts": stats.get("to_ts"),
                "last_updated": stats.get("last_updated"),
                "user_id": stats.get("user_id")
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {}
    
    async def get_top_albums(self, period: str = "this_month", limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener álbumes más escuchados usando la API de estadísticas de ListenBrainz
        
        Args:
            period: Rango de tiempo. Opciones:
                - this_week, this_month, this_year
                - last_week, last_month, last_year
                - all_time
            limit: Número de álbumes a devolver
        """
        try:
            lb_range = period.replace(" ", "_").lower()
            
            params = {
                "range": lb_range,
                "count": limit
            }
            
            data = await self._make_request(f"stats/user/{self.username}/releases", params)
            
            albums = []
            release_stats = data.get("payload", {}).get("releases", [])
            
            for release_data in release_stats:
                album = {
                    "name": release_data.get("release_name", ""),
                    "artist": release_data.get("artist_name", ""),
                    "listen_count": release_data.get("listen_count", 0),
                    "mbid": release_data.get("release_mbid"),
                    "url": release_data.get("release_mbid") and f"https://musicbrainz.org/release/{release_data['release_mbid']}" or ""
                }
                albums.append(album)
            
            return albums
            
        except Exception as e:
            print(f"Error obteniendo top álbumes: {e}")
            return []
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Obtener información básica del usuario"""
        try:
            data = await self._make_request(f"user/{self.username}")
            
            user_info = data.get("payload", {})
            
            return {
                "name": user_info.get("name"),
                "user_id": user_info.get("user_id"),
                "created": user_info.get("created"),
                "last_login": user_info.get("last_login"),
                "musicbrainz_id": user_info.get("musicbrainz_id")
            }
            
        except Exception as e:
            print(f"Error obteniendo info del usuario: {e}")
            return {}
    
    async def search_track(self, track_name: str, artist_name: str) -> Dict[str, Any]:
        """Buscar información de una canción específica"""
        try:
            # ListenBrainz no tiene endpoint de búsqueda directo
            # Podemos buscar en las escuchas del usuario
            recent_tracks = await self.get_recent_tracks(limit=500)
            
            for track in recent_tracks:
                if (track.name.lower() == track_name.lower() and 
                    track.artist.lower() == artist_name.lower()):
                    return {
                        "found": True,
                        "track": track,
                        "playcount": track.playcount or 0
                    }
            
            return {
                "found": False,
                "track": None,
                "playcount": 0
            }
            
        except Exception as e:
            print(f"Error buscando track: {e}")
            return {"found": False, "track": None, "playcount": 0}
    
    async def get_listening_activity(self, days: int = 30) -> Dict[str, Any]:
        """Obtener actividad de escucha por días"""
        try:
            # Obtener escuchas recientes
            recent_tracks = await self.get_recent_tracks(limit=2000)
            
            # Agrupar por fecha
            daily_activity = {}
            for track in recent_tracks:
                if track.date:
                    date_str = track.date.strftime("%Y-%m-%d")
                    if date_str not in daily_activity:
                        daily_activity[date_str] = 0
                    daily_activity[date_str] += 1
            
            return {
                "daily_listens": daily_activity,
                "total_days": len(daily_activity),
                "avg_daily_listens": sum(daily_activity.values()) / max(len(daily_activity), 1)
            }
            
        except Exception as e:
            print(f"Error obteniendo actividad: {e}")
            return {}
    
    async def close(self):
        """Cerrar conexión"""
        await self.client.aclose()
