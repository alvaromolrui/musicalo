import httpx
import os
import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

class MusicBrainzService:
    """Servicio para enriquecer y verificar metadatos usando MusicBrainz
    
    Propósito principal: Búsqueda inversa para identificar artistas de la biblioteca
    que cumplan con criterios específicos (género, país, época) cuando los metadatos
    locales son insuficientes o inexactos.
    """
    
    # Cache persistente compartido entre todas las instancias
    _CACHE_FILE = Path("/app/logs/musicbrainz_cache.json")
    _CACHE_EXPIRY_DAYS = 30
    _persistent_cache = None
    _cache_loaded = False
    
    def __init__(self):
        self.base_url = "https://musicbrainz.org/ws/2"
        self.app_name = os.getenv("APP_NAME", "MusicaloBot")
        self.app_version = "1.0"
        self.app_contact = os.getenv("CONTACT_EMAIL", "contact@musicalo.com")
        
        # MusicBrainz requiere User-Agent identificativo
        self.headers = {
            "User-Agent": f"{self.app_name}/{self.app_version} ( {self.app_contact} )"
        }
        self.client = httpx.AsyncClient(timeout=15.0, headers=self.headers)
        
        # Cargar cache persistente solo una vez
        if not MusicBrainzService._cache_loaded:
            self._load_cache()
            MusicBrainzService._cache_loaded = True
        
        # Rate limiting: última petición
        self._last_request_time = 0
    
    def _load_cache(self):
        """Cargar cache desde archivo"""
        try:
            if MusicBrainzService._CACHE_FILE.exists():
                with open(MusicBrainzService._CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    MusicBrainzService._persistent_cache = data.get('cache', {})
                    last_updated = data.get('last_updated', 0)
                    if last_updated:
                        age_hours = (time.time() - last_updated) / 3600
                        print(f"✅ Cache MusicBrainz cargado: {len(MusicBrainzService._persistent_cache)} artistas (actualizado hace {age_hours:.1f}h)")
                    else:
                        print(f"✅ Cache MusicBrainz cargado: {len(MusicBrainzService._persistent_cache)} artistas")
            else:
                MusicBrainzService._persistent_cache = {}
                print("📝 Cache MusicBrainz inicializado vacío (primera vez)")
        except Exception as e:
            print(f"⚠️ Error cargando cache MusicBrainz: {e}")
            MusicBrainzService._persistent_cache = {}
    
    def _save_cache(self):
        """Guardar cache en archivo"""
        try:
            # Crear directorio si no existe
            MusicBrainzService._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Limpiar entradas expiradas antes de guardar
            expired_count = self._clean_expired_cache()
            
            data = {
                'cache': MusicBrainzService._persistent_cache,
                'last_updated': time.time()
            }
            
            with open(MusicBrainzService._CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            if expired_count > 0:
                print(f"💾 Cache MusicBrainz guardado: {len(MusicBrainzService._persistent_cache)} artistas ({expired_count} expiradas limpiadas)")
            else:
                print(f"💾 Cache MusicBrainz guardado: {len(MusicBrainzService._persistent_cache)} artistas")
        except Exception as e:
            print(f"⚠️ Error guardando cache MusicBrainz: {e}")
    
    def _clean_expired_cache(self) -> int:
        """Eliminar entradas del cache que han expirado
        
        Returns:
            Número de entradas eliminadas
        """
        if not MusicBrainzService._persistent_cache:
            return 0
        
        current_time = time.time()
        expiry_seconds = MusicBrainzService._CACHE_EXPIRY_DAYS * 24 * 60 * 60
        
        expired_keys = []
        for key, value in MusicBrainzService._persistent_cache.items():
            if 'cached_at' in value:
                age = current_time - value['cached_at']
                if age > expiry_seconds:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del MusicBrainzService._persistent_cache[key]
        
        if expired_keys:
            print(f"🧹 Limpiadas {len(expired_keys)} entradas expiradas del cache")
        
        return len(expired_keys)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtener valor del cache persistente"""
        if not MusicBrainzService._persistent_cache:
            return None
        
        cached_data = MusicBrainzService._persistent_cache.get(cache_key)
        if cached_data:
            # Verificar si ha expirado
            current_time = time.time()
            expiry_seconds = MusicBrainzService._CACHE_EXPIRY_DAYS * 24 * 60 * 60
            
            if 'cached_at' in cached_data:
                age = current_time - cached_data['cached_at']
                if age > expiry_seconds:
                    # Expirado, eliminar
                    del MusicBrainzService._persistent_cache[cache_key]
                    return None
            
            return cached_data.get('data')
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Guardar valor en cache persistente (solo en memoria)
        
        El guardado a disco se hace al final del batch o al cerrar el servicio.
        """
        if MusicBrainzService._persistent_cache is None:
            MusicBrainzService._persistent_cache = {}
        
        MusicBrainzService._persistent_cache[cache_key] = {
            'data': data,
            'cached_at': time.time()
        }
    
    async def _rate_limit(self):
        """Asegurar que respetamos el rate limit de MusicBrainz (1 req/seg)"""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < 1.1:  # 1.1 seg para estar seguros
            await asyncio.sleep(1.1 - time_since_last)
        
        self._last_request_time = time.time()
    
    async def find_matching_artists_in_library(
        self,
        library_artists: List[str],
        filters: Dict[str, Any],
        max_artists: int = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Buscar qué artistas de la biblioteca cumplen con filtros específicos
        
        Este es el método clave para la búsqueda "inversa":
        - Toma una lista de artistas de la biblioteca local
        - Consulta MusicBrainz para cada uno
        - Devuelve solo los que cumplen los filtros
        
        Args:
            library_artists: Lista de nombres de artistas de tu biblioteca
            filters: Filtros a aplicar (genre, country, year_from, year_to)
            max_artists: Máximo de artistas a verificar (si None, usa MUSICBRAINZ_BATCH_SIZE)
            offset: Desde qué artista empezar (para búsquedas incrementales)
        
        Returns:
            Diccionario con artistas que cumplen y metadata de búsqueda:
            {
                "artists": List[Dict],
                "offset": int,
                "next_offset": int,
                "has_more": bool,
                "total_artists": int,
                "checked_this_batch": int
            }
        """
        try:
            # Usar variable de entorno si no se especifica max_artists
            if max_artists is None:
                max_artists = int(os.getenv("MUSICBRAINZ_BATCH_SIZE", "20"))
            
            # Verificar límite máximo total
            max_total = int(os.getenv("MUSICBRAINZ_MAX_TOTAL", "100"))
            if offset >= max_total:
                print(f"   ⚠️ Límite máximo alcanzado ({max_total} artistas)")
                return {
                    "artists": [],
                    "offset": offset,
                    "next_offset": offset,
                    "has_more": False,
                    "total_artists": len(library_artists),
                    "checked_this_batch": 0,
                    "max_reached": True
                }
            
            # Calcular slice de artistas a verificar
            end_index = min(offset + max_artists, len(library_artists), max_total)
            artists_to_check = library_artists[offset:end_index]
            
            print(f"🔍 MusicBrainz: Verificando artistas {offset+1} a {end_index} de {len(library_artists)}...")
            print(f"   Filtros: {filters}")
            print(f"   Batch size: {max_artists}")
            
            matching_artists = []
            checked_count = 0
            cache_hits = 0
            api_requests = 0
            
            for i, artist_name in enumerate(artists_to_check):
                checked_count += 1
                
                # Contar cache hits y API requests antes de verificar
                cache_key = f"artist_{artist_name.lower()}"
                is_cached = self._get_from_cache(cache_key) is not None
                
                # Verificar el artista contra los filtros
                verification = await self.verify_artist_metadata(artist_name, filters)
                
                # Actualizar contadores (verificar de nuevo después porque puede haberse cacheado)
                if is_cached:
                    cache_hits += 1
                else:
                    api_requests += 1
                
                if verification.get("matches", False):
                    matching_artists.append({
                        "name": artist_name,
                        "mb_data": verification
                    })
                    print(f"   ✅ [{offset+i+1}/{len(library_artists)}] {artist_name} - CUMPLE")
                else:
                    print(f"   ❌ [{offset+i+1}/{len(library_artists)}] {artist_name} - no cumple")
                
                # Mostrar progreso cada 10 artistas
                if (i + 1) % 10 == 0:
                    print(f"   📊 Progreso: {offset+i+1}/{len(library_artists)} verificados, {len(matching_artists)} coinciden")
                    print(f"      💾 Cache: {cache_hits} hits | 🌐 API: {api_requests} requests")
            
            has_more = end_index < len(library_artists) and end_index < max_total
            print(f"✅ MusicBrainz: {len(matching_artists)}/{checked_count} artistas cumplen los filtros")
            print(f"   💾 Cache usado: {cache_hits}/{checked_count} artistas ({cache_hits/checked_count*100:.0f}%)")
            print(f"   🌐 API requests: {api_requests}/{checked_count} artistas ({api_requests/checked_count*100:.0f}%)")
            
            # Guardar cache ahora si hay nuevas entradas
            if api_requests > 0:
                self._save_cache()
                print(f"   💾 Cache guardado en disco ({len(MusicBrainzService._persistent_cache)} artistas total)")
            if has_more:
                remaining = min(len(library_artists) - end_index, max_total - end_index)
                print(f"💡 Quedan {remaining} artistas por verificar. Di 'busca más' para continuar")
            
            return {
                "artists": matching_artists,
                "offset": offset,
                "next_offset": end_index,
                "has_more": has_more,
                "total_artists": len(library_artists),
                "checked_this_batch": checked_count
            }
            
        except Exception as e:
            print(f"❌ Error en búsqueda inversa de MusicBrainz: {e}")
            import traceback
            traceback.print_exc()
            return {
                "artists": [],
                "offset": offset,
                "next_offset": offset,
                "has_more": False,
                "total_artists": 0,
                "checked_this_batch": 0
            }
    
    async def verify_artist_metadata(
        self,
        artist_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verificar metadatos de un artista contra filtros específicos
        
        Args:
            artist_name: Nombre del artista a verificar
            filters: Diccionario con filtros a verificar:
                - genre: género musical (ej: "indie", "rock")
                - country: país (ej: "ES" para España)
                - language: idioma (ej: "spa" para español)
                - year_from: año desde (ej: 2000)
                - year_to: año hasta (ej: 2009)
        
        Returns:
            {
                "found": bool,
                "matches": bool,
                "artist_name": str,
                "country": str,
                "genres": List[str],
                "tags": List[str],
                "life_span": Dict,
                "match_details": Dict
            }
        """
        try:
            # Verificar cache PERSISTENTE
            cache_key = f"artist_{artist_name.lower()}"
            cached_data = self._get_from_cache(cache_key)
            
            if cached_data:
                artist_info = cached_data
                print(f"   💾 CACHE HIT: {artist_name} (datos cacheados)")
            else:
                # Buscar artista
                print(f"   🌐 API REQUEST: {artist_name} (consultando MusicBrainz...)")
                artist_info = await self._search_and_get_artist(artist_name)
                
                if not artist_info or not artist_info.get("found"):
                    return {
                        "found": False,
                        "matches": False,
                        "artist_name": artist_name
                    }
                
                # Guardar en cache PERSISTENTE
                self._save_to_cache(cache_key, artist_info)
            
            # Si no hay filtros, solo devolver la info
            if not filters:
                return {
                    **artist_info,
                    "matches": True,
                    "match_details": {}
                }
            
            # Verificar cada filtro
            match_details = {}
            all_match = True
            
            # Verificar país
            if "country" in filters:
                requested_country = filters["country"].upper()
                artist_country = artist_info.get("country", "").upper()
                
                # También considerar el área si no hay país
                artist_area = artist_info.get("area", "").upper()
                
                matches_country = (
                    artist_country == requested_country or
                    requested_country in artist_area
                )
                
                match_details["country"] = {
                    "requested": requested_country,
                    "actual": artist_country,
                    "area": artist_area,
                    "matches": matches_country
                }
                all_match = all_match and matches_country
            
            # Verificar género (más flexible)
            if "genre" in filters:
                requested_genre = filters["genre"].lower()
                artist_genres = [g.lower() for g in artist_info.get("genres", [])]
                artist_tags = [t.lower() for t in artist_info.get("tags", [])]
                
                # Mapeo de géneros relacionados
                genre_mappings = {
                    "indie": ["indie", "alternative", "indie rock", "indie pop", "independent"],
                    "rock": ["rock", "alternative rock", "indie rock", "hard rock"],
                    "pop": ["pop", "indie pop", "synthpop", "pop rock"],
                    "electronic": ["electronic", "electronica", "electro", "techno", "house"],
                    "folk": ["folk", "folk rock", "indie folk"],
                    "metal": ["metal", "heavy metal", "metalcore"],
                }
                
                # Obtener sinónimos del género solicitado
                related_genres = genre_mappings.get(requested_genre, [requested_genre])
                
                # Buscar coincidencias flexibles
                matches_genre = False
                for related in related_genres:
                    if matches_genre:
                        break
                    
                    # Buscar en géneros
                    for genre in artist_genres:
                        if related in genre or genre in related:
                            matches_genre = True
                            break
                    
                    # Buscar en tags
                    if not matches_genre:
                        for tag in artist_tags:
                            if related in tag or tag in related:
                                matches_genre = True
                                break
                
                match_details["genre"] = {
                    "requested": requested_genre,
                    "related": related_genres,
                    "artist_genres": artist_genres[:5],
                    "artist_tags": artist_tags[:5],
                    "matches": matches_genre
                }
                all_match = all_match and matches_genre
            
            # Verificar rango de años
            if "year_from" in filters or "year_to" in filters:
                year_from = filters.get("year_from")
                year_to = filters.get("year_to")
                
                life_span = artist_info.get("life_span", {})
                begin_year = life_span.get("begin")
                
                # Extraer año del string "YYYY-MM-DD"
                if begin_year and isinstance(begin_year, str):
                    try:
                        begin_year = int(begin_year.split("-")[0])
                    except:
                        begin_year = None
                
                matches_year = True
                if begin_year:
                    if year_from and begin_year < year_from:
                        matches_year = False
                    if year_to and begin_year > year_to:
                        matches_year = False
                else:
                    # Si no hay año, ser más permisivo (no rechazar automáticamente)
                    matches_year = None  # Neutral
                
                match_details["years"] = {
                    "requested_range": f"{year_from or '?'}-{year_to or '?'}",
                    "artist_begin": begin_year,
                    "matches": matches_year
                }
                
                # Solo fallar si explícitamente no cumple
                if matches_year == False:
                    all_match = False
            
            result = {
                **artist_info,
                "matches": all_match,
                "match_details": match_details
            }
            
            return result
            
        except Exception as e:
            print(f"⚠️ Error verificando '{artist_name}': {e}")
            return {
                "found": False,
                "matches": False,
                "artist_name": artist_name,
                "error": str(e)
            }
    
    async def _search_and_get_artist(self, artist_name: str) -> Dict[str, Any]:
        """Buscar y obtener detalles completos de un artista"""
        try:
            # Rate limiting
            await self._rate_limit()
            
            # Búsqueda inicial
            data = await self._make_request(
                "artist",
                {"query": f'artist:"{artist_name}"', "limit": 3}
            )
            
            artists = data.get("artists", [])
            if not artists:
                return {"found": False}
            
            # Tomar el primer resultado (mejor score)
            best_match = artists[0]
            artist_id = best_match.get("id")
            
            # Rate limiting antes de la segunda petición
            await self._rate_limit()
            
            # Obtener detalles completos
            details = await self._make_request(
                f"artist/{artist_id}",
                {"inc": "tags+genres+ratings+url-rels"}
            )
            
            if not details:
                return {"found": False}
            
            # Extraer géneros
            genres = [g.get("name") for g in details.get("genres", [])]
            if not genres:  # Fallback a tags
                genres = [t.get("name") for t in details.get("tags", [])][:5]
            
            # Extraer todos los tags
            tags = [t.get("name") for t in details.get("tags", [])]
            
            return {
                "found": True,
                "id": details.get("id"),
                "name": details.get("name"),
                "type": details.get("type"),
                "country": details.get("country"),
                "area": details.get("area", {}).get("name"),
                "life_span": {
                    "begin": details.get("life-span", {}).get("begin"),
                    "end": details.get("life-span", {}).get("end"),
                    "ended": details.get("life-span", {}).get("ended", False)
                },
                "genres": genres,
                "tags": tags,
                "url": f"https://musicbrainz.org/artist/{details.get('id')}"
            }
            
        except Exception as e:
            print(f"Error en búsqueda de artista: {e}")
            return {"found": False, "error": str(e)}
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Realizar petición a la API de MusicBrainz"""
        request_params = {"fmt": "json"}
        
        if params:
            request_params.update(params)
        
        try:
            response = await self.client.get(
                f"{self.base_url}/{endpoint}",
                params=request_params
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ Error en petición MusicBrainz ({endpoint}): {e}")
            return {}
    
    async def close(self):
        """Cerrar conexión y guardar cache"""
        await self.client.aclose()
        # Guardar cache al cerrar
        self._save_cache()

