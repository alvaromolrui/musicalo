import httpx
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.schemas import LastFMTrack, LastFMArtist

class LastFMService:
    def __init__(self):
        self.api_key = os.getenv("LASTFM_API_KEY")
        self.username = os.getenv("LASTFM_USERNAME")
        self.base_url = "https://ws.audioscrobbler.com/2.0/"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _make_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Realizar petición a la API de Last.fm"""
        if not self.api_key:
            raise ValueError("LASTFM_API_KEY no está configurado")
        
        if not self.username:
            raise ValueError("LASTFM_USERNAME no está configurado")
        
        request_params = {
            "method": method,
            "user": self.username,
            "api_key": self.api_key,
            "format": "json"
        }
        
        if params:
            request_params.update(params)
        
        try:
            response = await self.client.get(self.base_url, params=request_params)
            response.raise_for_status()
            data = response.json()
            
            # Verificar si hay error en la respuesta
            if "error" in data:
                error_message = data.get("message", "Unknown error")
                print(f"❌ Last.fm API error: {error_message}")
                return {}
            
            return data
            
        except Exception as e:
            print(f"❌ Error en petición Last.fm: {e}")
            return {}
    
    async def get_recent_tracks(self, limit: int = 50) -> List[LastFMTrack]:
        """Obtener escuchas recientes del usuario"""
        try:
            print(f"🎵 Obteniendo últimas {limit} canciones de Last.fm...")
            
            data = await self._make_request(
                "user.getrecenttracks",
                {"limit": limit}
            )
            
            tracks = []
            recent_tracks = data.get("recenttracks", {}).get("track", [])
            
            if isinstance(recent_tracks, dict):
                recent_tracks = [recent_tracks]
            
            for track_data in recent_tracks:
                # Parsear fecha
                date_parsed = None
                date_info = track_data.get("date")
                if date_info:
                    try:
                        timestamp = int(date_info.get("uts", 0))
                        date_parsed = datetime.fromtimestamp(timestamp)
                    except:
                        pass
                
                # Obtener imagen
                images = track_data.get("image", [])
                image_url = None
                if images:
                    for img in images:
                        if img.get("size") == "large":
                            image_url = img.get("#text")
                            break
                
                track = LastFMTrack(
                    name=track_data.get("name", ""),
                    artist=track_data.get("artist", {}).get("#text", "") if isinstance(track_data.get("artist"), dict) else track_data.get("artist", ""),
                    album=track_data.get("album", {}).get("#text", "") if isinstance(track_data.get("album"), dict) else None,
                    playcount=int(track_data.get("playcount", 1)),
                    date=date_parsed,
                    url=track_data.get("url"),
                    image_url=image_url
                )
                tracks.append(track)
            
            print(f"✅ Obtenidas {len(tracks)} canciones de Last.fm")
            return tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo tracks recientes: {e}")
            return []
    
    async def get_top_artists(self, period: str = "overall", limit: int = 50) -> List[LastFMArtist]:
        """Obtener artistas más escuchados
        
        Args:
            period: overall, 7day, 1month, 3month, 6month, 12month
            limit: número de artistas a obtener
        """
        try:
            print(f"🎤 Obteniendo top {limit} artistas de Last.fm (período: {period})...")
            
            data = await self._make_request(
                "user.gettopartists",
                {"period": period, "limit": limit}
            )
            
            artists = []
            top_artists = data.get("topartists", {}).get("artist", [])
            
            if isinstance(top_artists, dict):
                top_artists = [top_artists]
            
            for i, artist_data in enumerate(top_artists):
                # Obtener imagen
                images = artist_data.get("image", [])
                image_url = None
                if images:
                    for img in images:
                        if img.get("size") == "large":
                            image_url = img.get("#text")
                            break
                
                artist = LastFMArtist(
                    name=artist_data.get("name", ""),
                    playcount=int(artist_data.get("playcount", 0)),
                    url=artist_data.get("url"),
                    rank=i + 1,
                    image_url=image_url
                )
                artists.append(artist)
            
            print(f"✅ Obtenidos {len(artists)} artistas de Last.fm")
            return artists
            
        except Exception as e:
            print(f"❌ Error obteniendo top artistas: {e}")
            return []
    
    async def get_top_tracks(self, period: str = "overall", limit: int = 50) -> List[LastFMTrack]:
        """Obtener canciones más escuchadas
        
        Args:
            period: overall, 7day, 1month, 3month, 6month, 12month
            limit: número de canciones a obtener
        """
        try:
            print(f"🎵 Obteniendo top {limit} canciones de Last.fm (período: {period})...")
            
            data = await self._make_request(
                "user.gettoptracks",
                {"period": period, "limit": limit}
            )
            
            tracks = []
            top_tracks = data.get("toptracks", {}).get("track", [])
            
            if isinstance(top_tracks, dict):
                top_tracks = [top_tracks]
            
            for track_data in top_tracks:
                # Obtener imagen
                images = track_data.get("image", [])
                image_url = None
                if images:
                    for img in images:
                        if img.get("size") == "large":
                            image_url = img.get("#text")
                            break
                
                track = LastFMTrack(
                    name=track_data.get("name", ""),
                    artist=track_data.get("artist", {}).get("name", "") if isinstance(track_data.get("artist"), dict) else track_data.get("artist", ""),
                    playcount=int(track_data.get("playcount", 0)),
                    url=track_data.get("url"),
                    image_url=image_url
                )
                tracks.append(track)
            
            print(f"✅ Obtenidas {len(tracks)} canciones de Last.fm")
            return tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo top tracks: {e}")
            return []
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Obtener información del usuario"""
        try:
            data = await self._make_request("user.getinfo")
            
            user = data.get("user", {})
            
            return {
                "name": user.get("name"),
                "real_name": user.get("realname"),
                "playcount": int(user.get("playcount", 0)),
                "country": user.get("country"),
                "registered": user.get("registered", {}).get("#text"),
                "url": user.get("url"),
                "image": user.get("image", [{}])[-1].get("#text")  # Última imagen (más grande)
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo info del usuario: {e}")
            return {}
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del usuario (formato compatible con el bot)"""
        try:
            print("📊 Calculando estadísticas detalladas de Last.fm...")
            
            # Obtener info básica
            user_info = await self.get_user_info()
            total_listens = user_info.get("playcount", 0)
            
            # Obtener canciones recientes para calcular únicos
            recent_tracks = await self.get_recent_tracks(limit=1000)
            
            # Calcular artistas, álbumes y canciones únicas
            unique_artists = set()
            unique_albums = set()
            unique_tracks = set()
            
            for track in recent_tracks:
                if track.artist:
                    unique_artists.add(track.artist)
                if track.album:
                    unique_albums.add(track.album)
                if track.name and track.artist:
                    unique_tracks.add(f"{track.artist} - {track.name}")
            
            stats = {
                "total_listens": total_listens,
                "total_artists": len(unique_artists),
                "total_albums": len(unique_albums),
                "total_tracks": len(unique_tracks),
                "user_name": user_info.get("name"),
                "country": user_info.get("country")
            }
            
            print(f"✅ Estadísticas: {stats['total_listens']} escuchas, {stats['total_artists']} artistas únicos")
            return stats
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return {}
    
    async def search_track(self, track_name: str, artist_name: str) -> Dict[str, Any]:
        """Buscar información de una canción específica"""
        try:
            data = await self._make_request(
                "track.getInfo",
                {"track": track_name, "artist": artist_name, "autocorrect": 1}
            )
            
            track = data.get("track", {})
            
            if not track:
                return {"found": False}
            
            return {
                "found": True,
                "name": track.get("name"),
                "artist": track.get("artist", {}).get("name"),
                "album": track.get("album", {}).get("title"),
                "playcount": int(track.get("playcount", 0)),
                "listeners": int(track.get("listeners", 0)),
                "url": track.get("url"),
                "duration": int(track.get("duration", 0))
            }
            
        except Exception as e:
            print(f"❌ Error buscando track: {e}")
            return {"found": False}
    
    async def get_similar_tracks(self, track_name: str, artist_name: str, limit: int = 10) -> List[LastFMTrack]:
        """Obtener canciones similares a una canción dada"""
        try:
            data = await self._make_request(
                "track.getSimilar",
                {"track": track_name, "artist": artist_name, "limit": limit, "autocorrect": 1}
            )
            
            tracks = []
            similar_tracks = data.get("similartracks", {}).get("track", [])
            
            if isinstance(similar_tracks, dict):
                similar_tracks = [similar_tracks]
            
            for track_data in similar_tracks:
                track = LastFMTrack(
                    name=track_data.get("name", ""),
                    artist=track_data.get("artist", {}).get("name", "") if isinstance(track_data.get("artist"), dict) else track_data.get("artist", ""),
                    url=track_data.get("url")
                )
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo canciones similares: {e}")
            return []
    
    async def get_similar_artists(self, artist_name: str, limit: int = 10) -> List[LastFMArtist]:
        """Obtener artistas similares a un artista dado"""
        try:
            data = await self._make_request(
                "artist.getSimilar",
                {"artist": artist_name, "limit": limit, "autocorrect": 1}
            )
            
            artists = []
            similar_artists = data.get("similarartists", {}).get("artist", [])
            
            if isinstance(similar_artists, dict):
                similar_artists = [similar_artists]
            
            for i, artist_data in enumerate(similar_artists):
                # Obtener imagen
                images = artist_data.get("image", [])
                image_url = None
                if images:
                    for img in images:
                        if img.get("size") == "large":
                            image_url = img.get("#text")
                            break
                
                artist = LastFMArtist(
                    name=artist_data.get("name", ""),
                    url=artist_data.get("url"),
                    rank=i + 1,
                    image_url=image_url
                )
                artists.append(artist)
            
            return artists
            
        except Exception as e:
            print(f"❌ Error obteniendo artistas similares: {e}")
            return []
    
    async def get_artist_top_albums(self, artist_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtener los álbumes top de un artista"""
        try:
            data = await self._make_request(
                "artist.gettopalbums",
                {"artist": artist_name, "limit": limit, "autocorrect": 1}
            )
            
            albums = []
            top_albums = data.get("topalbums", {}).get("album", [])
            
            if isinstance(top_albums, dict):
                top_albums = [top_albums]
            
            for album_data in top_albums:
                # Obtener imagen
                images = album_data.get("image", [])
                image_url = None
                if images:
                    for img in images:
                        if img.get("size") == "large":
                            image_url = img.get("#text")
                            break
                
                albums.append({
                    "name": album_data.get("name", ""),
                    "artist": album_data.get("artist", {}).get("name", "") if isinstance(album_data.get("artist"), dict) else artist_name,
                    "url": album_data.get("url"),
                    "playcount": int(album_data.get("playcount", 0)),
                    "image_url": image_url
                })
            
            return albums
            
        except Exception as e:
            print(f"❌ Error obteniendo top álbumes: {e}")
            return []
    
    async def get_artist_top_tracks(self, artist_name: str, limit: int = 5) -> List[LastFMTrack]:
        """Obtener las canciones top de un artista específico"""
        try:
            data = await self._make_request(
                "artist.gettoptracks",
                {"artist": artist_name, "limit": limit, "autocorrect": 1}
            )
            
            tracks = []
            top_tracks = data.get("toptracks", {}).get("track", [])
            
            if isinstance(top_tracks, dict):
                top_tracks = [top_tracks]
            
            for track_data in top_tracks:
                # Obtener imagen
                images = track_data.get("image", [])
                image_url = None
                if images:
                    for img in images:
                        if img.get("size") == "large":
                            image_url = img.get("#text")
                            break
                
                track = LastFMTrack(
                    name=track_data.get("name", ""),
                    artist=track_data.get("artist", {}).get("name", "") if isinstance(track_data.get("artist"), dict) else artist_name,
                    playcount=int(track_data.get("playcount", 0)),
                    url=track_data.get("url"),
                    image_url=image_url
                )
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo top tracks del artista: {e}")
            return []
    
    async def get_listening_activity(self, days: int = 30) -> Dict[str, Any]:
        """Obtener actividad de escucha por días"""
        try:
            print(f"📅 Obteniendo actividad de los últimos {days} días...")
            
            # Obtener escuchas recientes (Last.fm devuelve hasta 1000)
            recent_tracks = await self.get_recent_tracks(limit=1000)
            
            # Agrupar por fecha
            from datetime import datetime, timedelta
            daily_activity = {}
            
            # Calcular fecha límite
            date_limit = datetime.now() - timedelta(days=days)
            
            for track in recent_tracks:
                if track.date and track.date >= date_limit:
                    date_str = track.date.strftime("%Y-%m-%d")
                    if date_str not in daily_activity:
                        daily_activity[date_str] = 0
                    daily_activity[date_str] += 1
            
            avg_listens = sum(daily_activity.values()) / max(len(daily_activity), 1)
            
            result = {
                "daily_listens": daily_activity,
                "total_days": len(daily_activity),
                "avg_daily_listens": avg_listens,
                "date_range_days": days
            }
            
            print(f"✅ Actividad: {len(daily_activity)} días activos, promedio {avg_listens:.1f} escuchas/día")
            return result
            
        except Exception as e:
            print(f"❌ Error obteniendo actividad: {e}")
            return {}
    
    async def close(self):
        """Cerrar conexión"""
        await self.client.aclose()

