import httpx
import os
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.schemas import LastFMTrack, LastFMArtist

class ListenBrainzService:
    def __init__(self):
        self.username = os.getenv("LISTENBRAINZ_USERNAME")
        self.token = os.getenv("LISTENBRAINZ_TOKEN")  # Opcional
        self.base_url = "https://api.listenbrainz.org/1"  # API v1, no v1.0
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Cache para recomendaciones (se renueva cada 5 minutos)
        self._recommendations_cache = None
        self._recommendations_cache_time = 0
        self._cache_ttl = 300  # 5 minutos
    
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
    
    async def get_recommendations(self, count: int = 50) -> List[Dict[str, Any]]:
        """Obtener recomendaciones colaborativas personalizadas de ListenBrainz
        
        Usa collaborative filtering basado en usuarios similares.
        Cache de 5 minutos para optimizar velocidad.
        
        Args:
            count: Número de recomendaciones a obtener
        
        Returns:
            Lista de grabaciones recomendadas
        """
        try:
            # Usar cache si está disponible y no ha expirado
            import time
            current_time = time.time()
            
            if (self._recommendations_cache is not None and 
                current_time - self._recommendations_cache_time < self._cache_ttl):
                print(f"💾 Usando cache de recomendaciones ({len(self._recommendations_cache)} recomendaciones)")
                return self._recommendations_cache[:count]
            
            # Cache expirado o no existe, obtener de nuevo
            params = {"count": count}
            data = await self._make_request(
                f"cf/recommendation/user/{self.username}/recording",
                params
            )
            
            recommendations = []
            recordings = data.get("payload", {}).get("mbids", [])
            
            for rec in recordings:
                recommendations.append({
                    "recording_mbid": rec.get("recording_mbid"),
                    "score": rec.get("score", 0),
                    # Metadata adicional si está disponible
                    "artist_name": rec.get("artist_name"),
                    "track_name": rec.get("track_name"),
                    "release_name": rec.get("release_name")
                })
            
            # Guardar en cache
            self._recommendations_cache = recommendations
            self._recommendations_cache_time = current_time
            
            print(f"✅ Obtenidas {len(recommendations)} recomendaciones de ListenBrainz (cacheadas por 5min)")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error obteniendo recomendaciones: {e}")
            return []
    
    async def get_similar_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener usuarios con gustos musicales similares
        
        Args:
            limit: Número de usuarios similares a obtener
        
        Returns:
            Lista de usuarios similares
        """
        try:
            data = await self._make_request(f"user/{self.username}/similar-users")
            
            similar_users = []
            users = data.get("payload", [])[:limit]
            
            for user in users:
                similar_users.append({
                    "user_name": user.get("user_name"),
                    "similarity": user.get("similarity", 0)
                })
            
            return similar_users
            
        except Exception as e:
            print(f"❌ Error obteniendo usuarios similares: {e}")
            return []
    
    async def get_lb_radio(
        self, 
        mode: str = "easy", 
        seed_artist_mbid: str = None,
        count: int = 50
    ) -> List[Dict[str, Any]]:
        """Obtener radio personalizada de ListenBrainz
        
        Genera una secuencia de canciones basada en diferentes modos.
        
        Args:
            mode: Modo de radio - "easy" (similar), "medium" (balanceado), "hard" (explorador)
            seed_artist_mbid: MBID del artista semilla (opcional)
            count: Número de canciones a obtener
        
        Returns:
            Lista de grabaciones para la radio
        """
        try:
            params = {
                "mode": mode,
                "count": count
            }
            
            if seed_artist_mbid:
                params["seed_artist_mbid"] = seed_artist_mbid
            
            data = await self._make_request(
                f"lb-radio/user/{self.username}",
                params
            )
            
            radio_tracks = []
            recordings = data.get("payload", {}).get("recordings", [])
            
            for rec in recordings:
                radio_tracks.append({
                    "recording_mbid": rec.get("recording_mbid"),
                    "artist_name": rec.get("artist_name"),
                    "track_name": rec.get("track_name"),
                    "release_name": rec.get("release_name")
                })
            
            print(f"✅ Obtenidas {len(radio_tracks)} canciones para radio (modo: {mode})")
            return radio_tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo radio: {e}")
            return []
    
    async def get_explore_playlists(self) -> List[Dict[str, Any]]:
        """Obtener playlists de descubrimiento generadas automáticamente
        
        Returns:
            Lista de playlists de exploración
        """
        try:
            data = await self._make_request(f"user/{self.username}/playlists/createdfor")
            
            playlists = []
            created_for = data.get("payload", {}).get("playlists", [])
            
            for playlist in created_for:
                playlists.append({
                    "playlist_mbid": playlist.get("playlist", {}).get("identifier"),
                    "title": playlist.get("playlist", {}).get("title"),
                    "description": playlist.get("playlist", {}).get("annotation"),
                    "track_count": len(playlist.get("playlist", {}).get("track", []))
                })
            
            return playlists
            
        except Exception as e:
            print(f"❌ Error obteniendo playlists de exploración: {e}")
            return []
    
    async def get_similar_recordings(
        self, 
        recording_mbid: str, 
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Obtener grabaciones similares a una grabación específica
        
        Args:
            recording_mbid: MBID de la grabación de referencia
            count: Número de grabaciones similares a obtener
        
        Returns:
            Lista de grabaciones similares
        """
        try:
            params = {"count": count}
            data = await self._make_request(
                f"cf/recommendation/recording/{recording_mbid}",
                params
            )
            
            similar = []
            recordings = data.get("payload", {}).get("mbids", [])
            
            for rec in recordings:
                similar.append({
                    "recording_mbid": rec.get("recording_mbid"),
                    "score": rec.get("score", 0),
                    "artist_name": rec.get("artist_name"),
                    "track_name": rec.get("track_name")
                })
            
            return similar
            
        except Exception as e:
            print(f"❌ Error obteniendo grabaciones similares: {e}")
            return []
    
    async def get_sitewide_stats(
        self, 
        stat_type: str = "artists", 
        range_type: str = "this_week"
    ) -> List[Dict[str, Any]]:
        """Obtener estadísticas globales del sitio (trending/popular)
        
        Args:
            stat_type: "artists", "recordings", o "releases"
            range_type: "this_week", "this_month", "this_year", "all_time"
        
        Returns:
            Lista de artistas/grabaciones/lanzamientos más populares globalmente
        """
        try:
            params = {"range": range_type}
            data = await self._make_request(f"stats/sitewide/{stat_type}", params)
            
            stats = []
            items = data.get("payload", {}).get(stat_type, [])
            
            for item in items:
                if stat_type == "artists":
                    stats.append({
                        "artist_name": item.get("artist_name"),
                        "artist_mbid": item.get("artist_mbid"),
                        "listen_count": item.get("listen_count", 0)
                    })
                elif stat_type == "recordings":
                    stats.append({
                        "track_name": item.get("track_name"),
                        "artist_name": item.get("artist_name"),
                        "recording_mbid": item.get("recording_mbid"),
                        "listen_count": item.get("listen_count", 0)
                    })
                elif stat_type == "releases":
                    stats.append({
                        "release_name": item.get("release_name"),
                        "artist_name": item.get("artist_name"),
                        "release_mbid": item.get("release_mbid"),
                        "listen_count": item.get("listen_count", 0)
                    })
            
            return stats
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas globales: {e}")
            return []
    
    async def get_similar_artists_from_recording(
        self,
        artist_name: str,
        limit: int = 10,
        musicbrainz_service = None
    ) -> List[LastFMArtist]:
        """Obtener artistas similares usando ListenBrainz CF o MusicBrainz como fallback
        
        Estrategia:
        1. Intentar con recomendaciones de ListenBrainz (collaborative filtering)
        2. Si no hay resultados, usar MusicBrainz para buscar por metadatos
        
        Args:
            artist_name: Nombre del artista de referencia
            limit: Número de artistas similares a obtener
            musicbrainz_service: Instancia de MusicBrainzService (opcional, para fallback)
        
        Returns:
            Lista de artistas similares
        """
        try:
            similar_artists = []
            
            # ESTRATEGIA 1: Usar recomendaciones de ListenBrainz
            print(f"   📊 Estrategia 1: Intentando con recomendaciones de ListenBrainz CF...")
            try:
                # OPTIMIZACIÓN: Reducido de 100 a 50 para ser más rápido (usa cache si existe)
                recommendations = await self.get_recommendations(count=50)
                
                if recommendations:
                    print(f"   📊 Obtenidas {len(recommendations)} recomendaciones de ListenBrainz")
                    # Agrupar por artista
                    artist_counts = {}
                    for rec in recommendations:
                        artist = rec.get("artist_name")
                        if artist and artist.lower() != artist_name.lower():
                            if artist not in artist_counts:
                                artist_counts[artist] = {
                                    "count": 0,
                                    "score": 0,
                                    "artist_name": artist
                                }
                            artist_counts[artist]["count"] += 1
                            artist_counts[artist]["score"] += rec.get("score", 0)
                    
                    # Ordenar por score y tomar los top N
                    sorted_artists = sorted(
                        artist_counts.values(),
                        key=lambda x: (x["score"], x["count"]),
                        reverse=True
                    )[:limit]
                    
                    # Convertir a formato LastFMArtist
                    for i, artist_data in enumerate(sorted_artists):
                        artist = LastFMArtist(
                            name=artist_data["artist_name"],
                            playcount=artist_data["count"],
                            rank=i + 1,
                            url=f"https://listenbrainz.org/artist/{artist_data['artist_name'].replace(' ', '+')}"
                        )
                        similar_artists.append(artist)
                    
                    if similar_artists:
                        print(f"✅ Encontrados {len(similar_artists)} artistas similares a '{artist_name}' (ListenBrainz CF)")
                        return similar_artists
                else:
                    print(f"   ⚠️ No hay recomendaciones disponibles en ListenBrainz")
            except Exception as e:
                print(f"   ⚠️ ListenBrainz CF no disponible: {e}")
            
            # ESTRATEGIA 2: Si no hay resultados y tenemos MusicBrainz, buscar por tags/géneros
            if not similar_artists and musicbrainz_service:
                print(f"   📊 Estrategia 2: Buscando por tags/géneros similares en MusicBrainz...")
                try:
                    # Usar el método de búsqueda por tags
                    tag_similar = await musicbrainz_service.find_similar_by_tags(artist_name, limit=limit)
                    
                    if tag_similar:
                        # Convertir a LastFMArtist
                        for i, artist_data in enumerate(tag_similar):
                            artist = LastFMArtist(
                                name=artist_data["name"],
                                playcount=0,
                                rank=i + 1,
                                url=f"https://musicbrainz.org/artist/{artist_data['mbid']}" if artist_data.get('mbid') else ""
                            )
                            similar_artists.append(artist)
                        
                        print(f"✅ Encontrados {len(similar_artists)} artistas similares por tags/géneros (MusicBrainz)")
                        return similar_artists
                    else:
                        print(f"   ⚠️ No se encontraron artistas con tags similares en MusicBrainz")
                        print(f"   💡 El artista '{artist_name}' probablemente no tiene tags/géneros en MusicBrainz")
                except Exception as e:
                    print(f"   ⚠️ Error buscando en MusicBrainz: {e}")
            elif not similar_artists and not musicbrainz_service:
                print(f"   💡 Tip: Habilita MusicBrainz para buscar artistas por relaciones/colaboraciones")
            
            # ESTRATEGIA 3: Si todo falla, usar IA para generar recomendaciones basadas en conocimiento general
            # Esto es especialmente útil para artistas sin metadata en MusicBrainz
            if not similar_artists:
                print(f"   📊 Estrategia 3: Usando IA para generar similares basándose en conocimiento musical general...")
                try:
                    # Importar aquí para evitar dependencias circulares
                    import google.generativeai as genai
                    
                    # Usar IA para generar artistas similares
                    # OPTIMIZACIÓN: Usar modelo flash-exp más rápido
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    
                    prompt = f"""Eres un experto en música. Genera una lista de {limit} artistas similares a "{artist_name}".

IMPORTANTE:
- Genera SOLO nombres de artistas/bandas, uno por línea
- NO agregues numeración, guiones, ni explicaciones
- Solo artistas reales y verificables
- Artistas que sean musicalmente similares en estilo, género o época

Formato:
[NOMBRE DEL ARTISTA]

Ejemplo:
The Velvet Underground
Sonic Youth
Yo La Tengo

Genera {limit} artistas similares a {artist_name}:"""
                    
                    # OPTIMIZACIÓN: Configuración para respuesta más rápida
                    generation_config = {
                        'temperature': 0.5,  # Más determinista
                        'max_output_tokens': 300,  # Solo necesitamos nombres
                        'top_p': 0.8
                    }
                    
                    response = model.generate_content(prompt, generation_config=generation_config)
                    ai_response = response.text.strip()
                    
                    # Parsear respuesta
                    for line in ai_response.split('\n'):
                        if len(similar_artists) >= limit:
                            break
                        
                        line = line.strip()
                        # Remover numeración si existe
                        line = re.sub(r'^\d+[\.\)]\s*', '', line)
                        # Remover guiones al inicio
                        line = re.sub(r'^[-*]\s*', '', line)
                        
                        if line and len(line) > 2:
                            artist = LastFMArtist(
                                name=line,
                                playcount=0,
                                rank=len(similar_artists) + 1,
                                url=""
                            )
                            similar_artists.append(artist)
                    
                    if similar_artists:
                        print(f"✅ Encontrados {len(similar_artists)} artistas similares usando IA (conocimiento general)")
                        return similar_artists
                except Exception as e:
                    print(f"   ⚠️ Error usando IA para similares: {e}")
            
            # Si no hay resultados, devolver lista vacía
            if not similar_artists:
                print(f"⚠️ No se encontraron artistas similares a '{artist_name}'")
                print(f"   💡 Esto puede pasar si:")
                print(f"      - ListenBrainz no tiene suficientes datos de ese artista")
                print(f"      - MusicBrainz no tiene relaciones/tags registradas")
                print(f"      - El artista es muy nuevo o poco conocido")
                print(f"      - La IA no pudo generar recomendaciones fiables")
            
            return similar_artists
            
        except Exception as e:
            print(f"❌ Error obteniendo artistas similares: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_similar_tracks_from_recording(
        self,
        track_name: str,
        artist_name: str,
        limit: int = 10
    ) -> List[LastFMTrack]:
        """Obtener canciones similares basándose en recomendaciones de ListenBrainz
        
        Simula get_similar_tracks de Last.fm usando collaborative filtering.
        
        Args:
            track_name: Nombre de la canción de referencia
            artist_name: Nombre del artista
            limit: Número de canciones similares a obtener
        
        Returns:
            Lista de canciones similares
        """
        try:
            # Obtener recomendaciones generales y filtrar
            # OPTIMIZACIÓN: Usar cache si existe
            recommendations = await self.get_recommendations(count=min(50, limit * 2))
            
            similar_tracks = []
            for rec in recommendations:
                if rec.get("track_name") and rec.get("artist_name"):
                    # Evitar la misma canción
                    if (rec.get("track_name").lower() == track_name.lower() and
                        rec.get("artist_name").lower() == artist_name.lower()):
                        continue
                    
                    track = LastFMTrack(
                        name=rec.get("track_name"),
                        artist=rec.get("artist_name"),
                        album=rec.get("release_name"),
                        playcount=int(rec.get("score", 0) * 100),  # Convertir score a playcount simulado
                        url=f"https://musicbrainz.org/recording/{rec.get('recording_mbid')}"
                            if rec.get('recording_mbid') else None
                    )
                    similar_tracks.append(track)
                    
                    if len(similar_tracks) >= limit:
                        break
            
            print(f"✅ Encontradas {len(similar_tracks)} canciones similares")
            return similar_tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo canciones similares: {e}")
            return []
    
    async def close(self):
        """Cerrar conexión"""
        await self.client.aclose()
