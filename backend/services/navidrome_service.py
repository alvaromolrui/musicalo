import httpx
import os
from typing import List, Optional, Dict, Any
import base64
from models.schemas import Track, Album, Artist

class NavidromeService:
    def __init__(self):
        self.base_url = os.getenv("NAVIDROME_URL", "http://localhost:4533")
        self.username = os.getenv("NAVIDROME_USERNAME", "admin")
        self.password = os.getenv("NAVIDROME_PASSWORD", "password")
        self.token = None
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def authenticate(self):
        """Autenticar con Navidrome y obtener token"""
        try:
            # Crear credenciales básicas
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Login para obtener token
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/login",
                data=login_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                print(f"✅ Autenticación exitosa con Navidrome")
                return True
            else:
                print(f"❌ Error de autenticación Navidrome: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error en autenticación Navidrome: {e}")
            return False
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None):
        """Realizar petición autenticada a Navidrome"""
        if not self.token:
            await self.authenticate()
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/{endpoint}",
                headers=headers,
                params=params or {}
            )
            
            if response.status_code == 401:
                # Token expirado, reautenticar
                await self.authenticate()
                headers["Authorization"] = f"Bearer {self.token}"
                response = await self.client.get(
                    f"{self.base_url}/api/{endpoint}",
                    headers=headers,
                    params=params or {}
                )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error en petición Navidrome: {e}")
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
        """Buscar en la biblioteca"""
        try:
            print(f"🔍 Buscando '{query}' en Navidrome...")
            params = {
                "q": query,
                "limit": limit
            }
            
            data = await self._make_request("search3", params)
            print(f"📊 Resultados de búsqueda: {len(data.get('song', []))} canciones, {len(data.get('album', []))} álbumes, {len(data.get('artist', []))} artistas")
            
            results = {
                "tracks": [],
                "albums": [],
                "artists": []
            }
            
            # Procesar resultados
            for item in data.get("song", []):
                track = Track(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    artist=item.get("artist", ""),
                    album=item.get("album", ""),
                    duration=item.get("duration"),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    cover_url=item.get("albumCoverArtUrl")
                )
                results["tracks"].append(track)
            
            for item in data.get("album", []):
                album = Album(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    artist=item.get("artist", ""),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    cover_url=item.get("coverArtUrl")
                )
                results["albums"].append(album)
            
            for item in data.get("artist", []):
                artist = Artist(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    genre=item.get("genre"),
                    image_url=item.get("imageUrl")
                )
                results["artists"].append(artist)
            
            return results
            
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            return {"tracks": [], "albums": [], "artists": []}
    
    async def close(self):
        """Cerrar conexión"""
        await self.client.aclose()
