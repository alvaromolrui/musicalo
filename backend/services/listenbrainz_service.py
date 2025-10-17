import httpx
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.schemas import LastFMTrack, LastFMArtist

class ListenBrainzService:
    def __init__(self):
        self.username = os.getenv("LISTENBRAINZ_USERNAME")
        self.token = os.getenv("LISTENBRAINZ_TOKEN")  # Opcional
        self.base_url = "https://api.listenbrainz.org/1.0"
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
    
    async def get_top_artists(self, period: str = "all_time", limit: int = 50) -> List[LastFMArtist]:
        """Obtener artistas más escuchados"""
        try:
            # ListenBrainz no tiene endpoint directo para top artists
            # Vamos a calcularlo desde las escuchas recientes
            recent_tracks = await self.get_recent_tracks(limit=1000)  # Obtener más datos
            
            # Contar artistas
            artist_counts = {}
            for track in recent_tracks:
                artist = track.artist
                if artist:
                    artist_counts[artist] = artist_counts.get(artist, 0) + 1
            
            # Ordenar por reproducciones
            sorted_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)
            
            artists = []
            for i, (artist_name, count) in enumerate(sorted_artists[:limit]):
                artist = LastFMArtist(
                    name=artist_name,
                    playcount=count,
                    url=f"https://musicbrainz.org/search?query={artist_name}&type=artist",
                    rank=i + 1
                )
                artists.append(artist)
            
            return artists
            
        except Exception as e:
            print(f"Error obteniendo top artistas: {e}")
            return []
    
    async def get_top_tracks(self, period: str = "all_time", limit: int = 50) -> List[LastFMTrack]:
        """Obtener canciones más escuchadas"""
        try:
            # Similar a top artists, calcular desde escuchas recientes
            recent_tracks = await self.get_recent_tracks(limit=1000)
            
            # Contar canciones
            track_counts = {}
            for track in recent_tracks:
                key = f"{track.artist} - {track.name}"
                if key not in track_counts:
                    track_counts[key] = {
                        'track': track,
                        'count': 0
                    }
                track_counts[key]['count'] += 1
            
            # Ordenar por reproducciones
            sorted_tracks = sorted(track_counts.values(), key=lambda x: x['count'], reverse=True)
            
            tracks = []
            for item in sorted_tracks[:limit]:
                track = item['track']
                track.playcount = item['count']
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"Error obteniendo top tracks: {e}")
            return []
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del usuario"""
        try:
            data = await self._make_request(f"user/{self.username}/stats")
            
            stats = data.get("payload", {})
            
            return {
                "total_listens": stats.get("total_listens", 0),
                "total_artists": stats.get("total_artists", 0),
                "total_albums": stats.get("total_albums", 0),
                "total_tracks": stats.get("total_tracks", 0),
                "last_updated": stats.get("last_updated"),
                "user_id": stats.get("user_id"),
                "user_name": stats.get("user_name")
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {}
    
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
