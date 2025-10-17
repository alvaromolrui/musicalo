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
        """Obtener canciones aleatorias de la biblioteca"""
        try:
            print(f"🎵 Obteniendo {limit} canciones aleatorias de Navidrome...")
            
            # Usar getRandomSongs para obtener canciones aleatorias
            params = {
                "size": min(limit, 500)  # Máximo 500 según API de Subsonic
            }
            
            # Agregar filtros si existen
            if filters.get("genre"):
                params["genre"] = filters["genre"]
            if filters.get("fromYear"):
                params["fromYear"] = filters["fromYear"]
            if filters.get("toYear"):
                params["toYear"] = filters["toYear"]
            
            data = await self._make_request("getRandomSongs", params)
            tracks = []
            
            songs = data.get("randomSongs", {}).get("song", [])
            if isinstance(songs, dict):
                songs = [songs]
            
            for item in songs:
                # Debug: imprimir todos los campos disponibles (solo primero)
                if len(tracks) == 0:
                    print(f"🔍 Campos disponibles en song: {list(item.keys())}")
                    if 'path' in item:
                        print(f"   path: {item.get('path')}")
                    if 'suffix' in item:
                        print(f"   suffix: {item.get('suffix')}")
                
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
                    cover_url=None
                )
                tracks.append(track)
            
            print(f"✅ Obtenidas {len(tracks)} canciones de Navidrome")
            return tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo tracks: {e}")
            return []
    
    async def get_albums(self, limit: int = 50, offset: int = 0, **filters) -> List[Album]:
        """Obtener álbumes de la biblioteca"""
        try:
            print(f"📀 Obteniendo {limit} álbumes de Navidrome...")
            
            # Usar getAlbumList2 (tipo: random, newest, frequent, recent, etc)
            params = {
                "type": "random",
                "size": min(limit, 500),
                "offset": offset
            }
            
            data = await self._make_request("getAlbumList2", params)
            albums = []
            
            album_list = data.get("albumList2", {}).get("album", [])
            if isinstance(album_list, dict):
                album_list = [album_list]
            
            for item in album_list:
                album = Album(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    artist=item.get("artist", ""),
                    year=item.get("year"),
                    genre=item.get("genre"),
                    track_count=item.get("songCount"),
                    duration=item.get("duration"),
                    cover_url=None,
                    play_count=item.get("playCount")
                )
                albums.append(album)
            
            print(f"✅ Obtenidos {len(albums)} álbumes de Navidrome")
            return albums
            
        except Exception as e:
            print(f"❌ Error obteniendo álbumes: {e}")
            return []
    
    async def get_artists(self, limit: int = 50, offset: int = 0, **filters) -> List[Artist]:
        """Obtener artistas de la biblioteca"""
        try:
            print(f"🎤 Obteniendo artistas de Navidrome...")
            
            # Usar getArtists para obtener todos los artistas
            data = await self._make_request("getArtists", {})
            artists = []
            
            # La API de Subsonic agrupa artistas por índice (A, B, C, etc.)
            indexes = data.get("artists", {}).get("index", [])
            if isinstance(indexes, dict):
                indexes = [indexes]
            
            artist_count = 0
            for index in indexes:
                artists_in_index = index.get("artist", [])
                if isinstance(artists_in_index, dict):
                    artists_in_index = [artists_in_index]
                
                for item in artists_in_index:
                    if artist_count >= limit:
                        break
                    
                    artist = Artist(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        album_count=item.get("albumCount"),
                        track_count=None,  # No disponible en getArtists
                        play_count=None,   # No disponible en getArtists
                        genre=None,        # No disponible en getArtists
                        image_url=None
                    )
                    artists.append(artist)
                    artist_count += 1
                
                if artist_count >= limit:
                    break
            
            print(f"✅ Obtenidos {len(artists)} artistas de Navidrome")
            return artists
            
        except Exception as e:
            print(f"❌ Error obteniendo artistas: {e}")
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
