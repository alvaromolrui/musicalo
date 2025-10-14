import httpx
import os
from typing import List, Optional, Dict, Any
import hashlib
import random
import string
from models.schemas import Track, Album, Artist

class NavidromeService:
    def __init__(self):
        self.base_url = os.getenv("NAVIDROME_URL", "http://localhost:4533")
        self.username = os.getenv("NAVIDROME_USERNAME", "admin")
        self.password = os.getenv("NAVIDROME_PASSWORD", "password")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.client_name = "musicalo"
        self.api_version = "1.16.1"
    
    def _get_auth_params(self):
        """Generar parámetros de autenticación para Subsonic API"""
        # Generar salt aleatorio
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # Crear token: md5(password + salt)
        token = hashlib.md5((self.password + salt).encode()).hexdigest()
        
        return {
            "u": self.username,
            "t": token,
            "s": salt,
            "v": self.api_version,
            "c": self.client_name,
            "f": "json"
        }
    
    async def test_connection(self):
        """Probar conexión con Navidrome"""
        try:
            params = self._get_auth_params()
            response = await self.client.get(
                f"{self.base_url}/rest/ping.view",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                subsonic_response = data.get("subsonic-response", {})
                if subsonic_response.get("status") == "ok":
                    print(f"✅ Conexión exitosa con Navidrome")
                    return True
            
            print(f"❌ Error de conexión Navidrome: {response.status_code}")
            return False
                
        except Exception as e:
            print(f"❌ Error probando conexión Navidrome: {e}")
            return False
    
    async def _make_request(self, endpoint: str, extra_params: Optional[Dict] = None):
        """Realizar petición autenticada a Navidrome usando Subsonic API"""
        try:
            # Combinar parámetros de autenticación con parámetros adicionales
            params = self._get_auth_params()
            if extra_params:
                params.update(extra_params)
            
            response = await self.client.get(
                f"{self.base_url}/rest/{endpoint}.view",
                params=params
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Verificar respuesta de Subsonic
            subsonic_response = data.get("subsonic-response", {})
            if subsonic_response.get("status") == "failed":
                error = subsonic_response.get("error", {})
                raise Exception(f"Navidrome error: {error.get('message', 'Unknown error')}")
            
            return subsonic_response
            
        except Exception as e:
            print(f"❌ Error en petición Navidrome ({endpoint}): {e}")
            raise
    
    async def get_tracks(self, limit: int = 50, offset: int = 0, **filters) -> List[Track]:
        """Obtener canciones de la biblioteca"""
        try:
            params = {
                "limit": limit,
                "offset": offset,
                **filters
            }
            
            data = await self._make_request("song", params)
            tracks = []
            
            for item in data.get("content", []):
                track = Track(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    artist=item.get("artist", ""),
                    album=item.get("album", ""),
                    duration=item.get("duration"),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    play_count=item.get("playCount"),
                    path=item.get("path"),
                    cover_url=item.get("albumCoverArtUrl")
                )
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"Error obteniendo tracks: {e}")
            return []
    
    async def get_albums(self, limit: int = 50, offset: int = 0, **filters) -> List[Album]:
        """Obtener álbumes de la biblioteca"""
        try:
            params = {
                "limit": limit,
                "offset": offset,
                **filters
            }
            
            data = await self._make_request("album", params)
            albums = []
            
            for item in data.get("content", []):
                album = Album(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    artist=item.get("artist", ""),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    track_count=item.get("songCount"),
                    duration=item.get("duration"),
                    cover_url=item.get("coverArtUrl"),
                    play_count=item.get("playCount")
                )
                albums.append(album)
            
            return albums
            
        except Exception as e:
            print(f"Error obteniendo álbumes: {e}")
            return []
    
    async def get_artists(self, limit: int = 50, offset: int = 0, **filters) -> List[Artist]:
        """Obtener artistas de la biblioteca"""
        try:
            params = {
                "limit": limit,
                "offset": offset,
                **filters
            }
            
            data = await self._make_request("artist", params)
            artists = []
            
            for item in data.get("content", []):
                artist = Artist(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    album_count=item.get("albumCount"),
                    track_count=item.get("songCount"),
                    play_count=item.get("playCount"),
                    genre=item.get("genre"),
                    image_url=item.get("imageUrl")
                )
                artists.append(artist)
            
            return artists
            
        except Exception as e:
            print(f"Error obteniendo artistas: {e}")
            return []
    
    async def search(self, query: str, limit: int = 20) -> Dict[str, List]:
        """Buscar en la biblioteca usando Subsonic API"""
        try:
            print(f"🔍 Buscando '{query}' en Navidrome...")
            params = {
                "query": query,
                "songCount": limit,
                "albumCount": limit,
                "artistCount": limit
            }
            
            data = await self._make_request("search3", params)
            search_result = data.get("searchResult3", {})
            
            songs = search_result.get("song", [])
            albums = search_result.get("album", [])
            artists = search_result.get("artist", [])
            
            print(f"📊 Resultados de búsqueda: {len(songs)} canciones, {len(albums)} álbumes, {len(artists)} artistas")
            
            results = {
                "tracks": [],
                "albums": [],
                "artists": []
            }
            
            # Procesar canciones
            for item in songs:
                track = Track(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    artist=item.get("artist", ""),
                    album=item.get("album", ""),
                    duration=item.get("duration"),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    play_count=item.get("playCount"),
                    path=item.get("path"),
                    cover_url=None  # Subsonic API no incluye cover URL directo en songs
                )
                results["tracks"].append(track)
            
            # Procesar álbumes
            for item in albums:
                album = Album(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    artist=item.get("artist", ""),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    track_count=item.get("songCount"),
                    duration=item.get("duration"),
                    cover_url=None,  # Se puede construir con getCoverArt si es necesario
                    play_count=item.get("playCount")
                )
                results["albums"].append(album)
            
            # Procesar artistas
            for item in artists:
                artist = Artist(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    album_count=item.get("albumCount"),
                    genre=None,  # No disponible en search3
                    image_url=None  # Se puede construir con getArtistInfo si es necesario
                )
                results["artists"].append(artist)
            
            return results
            
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            return {"tracks": [], "albums": [], "artists": []}
    
    async def close(self):
        """Cerrar conexión"""
        await self.client.aclose()
