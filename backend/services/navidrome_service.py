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
    
    async def create_playlist(self, name: str, song_ids: List[str]) -> Optional[str]:
        """Crear playlist en Navidrome usando la API
        
        Args:
            name: Nombre de la playlist
            song_ids: Lista de IDs de canciones a agregar
            
        Returns:
            ID de la playlist creada o None si falla
        """
        try:
            print(f"🎵 Creando playlist '{name}' en Navidrome con {len(song_ids)} canciones...")
            
            # Crear playlist vacía
            params = self._get_auth_params()
            params["name"] = name
            
            data = await self._make_request("createPlaylist", params)
            playlist_data = data.get("playlist", {})
            playlist_id = playlist_data.get("id")
            
            if not playlist_id:
                print(f"❌ No se pudo obtener ID de playlist creada")
                return None
            
            print(f"✅ Playlist creada con ID: {playlist_id}")
            
            # Agregar canciones a la playlist
            # La API de Subsonic requiere múltiples parámetros songIdToAdd
            params = self._get_auth_params()
            params["playlistId"] = playlist_id
            
            # Construir URL con múltiples parámetros songIdToAdd
            url = f"{self.base_url}/rest/updatePlaylist.view"
            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            song_params = "&".join([f"songIdToAdd={sid}" for sid in song_ids])
            full_url = f"{url}?{url_params}&{song_params}"
            
            response = await self.client.get(full_url)
            if response.status_code != 200:
                print(f"❌ Error al agregar canciones: {response.status_code}")
                return None
            
            print(f"✅ Agregadas {len(song_ids)} canciones a la playlist")
            
            return playlist_id
            
        except Exception as e:
            print(f"❌ Error creando playlist en Navidrome: {e}")
            return None
    
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
    
    async def create_share(
        self, 
        item_ids: List[str], 
        description: Optional[str] = None,
        expires: Optional[int] = None,
        downloadable: bool = True
    ) -> Optional[Dict[str, str]]:
        """Crear enlace compartible para canciones o álbumes
        
        Args:
            item_ids: Lista de IDs de canciones o álbumes a compartir
            description: Descripción opcional del share
            expires: Tiempo de expiración en milisegundos desde epoch (opcional)
            downloadable: Si el share permite descargas (por defecto True)
            
        Returns:
            Dict con 'id', 'url' y 'description' del share, o None si falla
        """
        try:
            print(f"🔗 Creando share para {len(item_ids)} items (downloadable={downloadable})...")
            
            # Construir parámetros
            params = self._get_auth_params()
            if description:
                params["description"] = description
            if expires:
                params["expires"] = str(expires)
            # Agregar parámetro downloadable explícitamente
            params["downloadable"] = "true" if downloadable else "false"
            
            # La API requiere múltiples parámetros 'id' para cada item
            url = f"{self.base_url}/rest/createShare.view"
            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            id_params = "&".join([f"id={item_id}" for item_id in item_ids])
            full_url = f"{url}?{url_params}&{id_params}"
            
            # Debug: imprimir URL completa (sin mostrar password/token por seguridad)
            debug_params = {k: v for k, v in params.items() if k not in ['t', 's']}
            print(f"🔍 DEBUG - Parámetros del share: {debug_params}")
            print(f"🔍 DEBUG - IDs compartidos: {len(item_ids)} items")
            
            response = await self.client.get(full_url)
            
            if response.status_code != 200:
                print(f"❌ Error al crear share: {response.status_code}")
                return None
            
            data = response.json()
            subsonic_response = data.get("subsonic-response", {})
            
            if subsonic_response.get("status") == "failed":
                error = subsonic_response.get("error", {})
                print(f"❌ Error de Subsonic: {error.get('message', 'Unknown')}")
                return None
            
            # Extraer información del share
            shares = subsonic_response.get("shares", {}).get("share", [])
            if isinstance(shares, dict):
                shares = [shares]
            
            if not shares:
                print(f"❌ No se recibió información del share")
                return None
            
            share = shares[0]
            share_id = share.get("id", "")
            share_url = share.get("url", "")
            
            # Debug: ver todos los campos devueltos por el share
            print(f"🔍 DEBUG - Respuesta del share: {share}")
            print(f"🔍 DEBUG - Campo 'downloadable' en respuesta: {share.get('downloadable', 'NO PRESENTE')}")
            
            # IMPORTANTE: Navidrome IGNORA el parámetro downloadable en createShare
            # Debemos usar updateShare después para forzar downloadable=true
            if downloadable:
                print(f"🔄 Ejecutando updateShare para forzar downloadable=true...")
                try:
                    update_params = self._get_auth_params()
                    update_params["id"] = share_id  # updateShare usa 'id', no 'shareId'
                    update_params["downloadable"] = "true"
                    
                    update_url = f"{self.base_url}/rest/updateShare.view"
                    url_params = "&".join([f"{k}={v}" for k, v in update_params.items()])
                    update_full_url = f"{update_url}?{url_params}"
                    
                    print(f"🔍 DEBUG - Llamando updateShare con id={share_id}")
                    update_response = await self.client.get(update_full_url)
                    
                    if update_response.status_code == 200:
                        update_data = update_response.json()
                        update_subsonic = update_data.get("subsonic-response", {})
                        if update_subsonic.get("status") == "ok":
                            print(f"✅ Share actualizado exitosamente con downloadable=true")
                        else:
                            error_msg = update_subsonic.get("error", {}).get("message", "Unknown")
                            print(f"⚠️ updateShare falló: {error_msg}")
                    else:
                        print(f"⚠️ updateShare HTTP error: {update_response.status_code}")
                        print(f"   Respuesta: {update_response.text}")
                except Exception as e:
                    print(f"⚠️ Error al ejecutar updateShare: {e}")
                    import traceback
                    traceback.print_exc()
            
            share_info = {
                "id": share_id,
                "url": share_url,
                "description": share.get("description", description or ""),
                "created": share.get("created", ""),
                "expires": share.get("expires"),
                "visit_count": share.get("visitCount", 0),
                "downloadable": share.get("downloadable")  # Agregar campo downloadable
            }
            
            print(f"✅ Share creado: {share_url}")
            print(f"   Downloadable: {share.get('downloadable', 'no especificado')}")
            return share_info
            
        except Exception as e:
            print(f"❌ Error creando share: {e}")
            return None
    
    async def get_album_tracks(self, album_id: str) -> List[Track]:
        """Obtener todas las canciones de un álbum
        
        Args:
            album_id: ID del álbum
            
        Returns:
            Lista de tracks del álbum
        """
        try:
            data = await self._make_request("getAlbum", {"id": album_id})
            album_data = data.get("album", {})
            
            songs = album_data.get("song", [])
            if isinstance(songs, dict):
                songs = [songs]
            
            tracks = []
            for song in songs:
                track = Track(
                    id=song.get("id", ""),
                    title=song.get("title", ""),
                    artist=song.get("artist", ""),
                    album=song.get("album", ""),
                    duration=song.get("duration"),
                    year=song.get("year"),
                    genre=song.get("genre"),
                    play_count=song.get("playCount"),
                    path=song.get("path"),
                    cover_url=None
                )
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo tracks del álbum: {e}")
            return []
    
    async def get_now_playing(self) -> List[Dict[str, Any]]:
        """Obtener información de lo que se está reproduciendo actualmente
        
        Returns:
            Lista de diccionarios con información de reproducción actual en todos los reproductores.
            Cada diccionario contiene:
            - track: Título de la canción
            - artist: Artista
            - album: Álbum
            - username: Usuario que está reproduciendo
            - player_name: Nombre del reproductor
            - minutes_ago: Hace cuántos minutos comenzó
            - duration: Duración de la canción
            - year: Año de lanzamiento
        """
        try:
            print(f"🎵 Obteniendo información de reproducción actual...")
            
            data = await self._make_request("getNowPlaying", {})
            entries = data.get("nowPlaying", {}).get("entry", [])
            
            # Normalizar a lista si es un solo elemento
            if isinstance(entries, dict):
                entries = [entries]
            
            now_playing = []
            for entry in entries:
                now_playing.append({
                    "track": entry.get("title", ""),
                    "artist": entry.get("artist", ""),
                    "album": entry.get("album", ""),
                    "username": entry.get("username", ""),
                    "player_name": entry.get("playerName", ""),
                    "minutes_ago": entry.get("minutesAgo", 0),
                    "duration": entry.get("duration"),
                    "year": entry.get("year")
                })
            
            print(f"✅ Encontradas {len(now_playing)} reproducciones activas")
            return now_playing
            
        except Exception as e:
            print(f"❌ Error obteniendo now playing: {e}")
            return []
    
    async def close(self):
        """Cerrar conexión"""
        await self.client.aclose()
