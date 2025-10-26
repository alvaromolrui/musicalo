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
            
            if not details or not isinstance(details, dict) or "id" not in details:
                print(f"   ⚠️ MusicBrainz no devolvió detalles válidos para '{artist_name}'")
                return {"found": False}
            
            # Extraer géneros con manejo seguro
            genres = []
            try:
                genres = [g.get("name") for g in details.get("genres", []) if isinstance(g, dict) and g.get("name")]
                if not genres:  # Fallback a tags
                    genres = [t.get("name") for t in details.get("tags", [])[:5] if isinstance(t, dict) and t.get("name")]
            except Exception as e:
                print(f"   ⚠️ Error extrayendo géneros para '{artist_name}': {e}")
            
            # Extraer todos los tags con manejo seguro
            tags = []
            try:
                tags = [t.get("name") for t in details.get("tags", []) if isinstance(t, dict) and t.get("name")]
            except Exception as e:
                print(f"   ⚠️ Error extrayendo tags para '{artist_name}': {e}")
            
            # Extraer area de forma segura
            area_name = None
            try:
                area_data = details.get("area")
                if isinstance(area_data, dict):
                    area_name = area_data.get("name")
            except:
                pass
            
            # Extraer life-span de forma segura
            life_span_data = {"begin": None, "end": None, "ended": False}
            try:
                life_span = details.get("life-span")
                if isinstance(life_span, dict):
                    life_span_data = {
                        "begin": life_span.get("begin"),
                        "end": life_span.get("end"),
                        "ended": life_span.get("ended", False)
                    }
            except:
                pass
            
            return {
                "found": True,
                "id": details.get("id"),
                "name": details.get("name"),
                "type": details.get("type"),
                "country": details.get("country"),
                "area": area_name,
                "life_span": life_span_data,
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
    
    async def get_latest_releases_by_artist(
        self,
        artist_name: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Obtener los últimos N releases de un artista específico
        
        Este método busca los releases más recientes de un artista,
        sin importar la fecha, solo ordenados cronológicamente.
        
        Args:
            artist_name: Nombre del artista
            limit: Número de releases a obtener (default: 3)
        
        Returns:
            Lista de releases ordenados por fecha (más reciente primero)
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🔍 Buscando últimos {limit} releases de '{artist_name}'...")
            
            # Búsqueda simple por artista con ordenamiento por fecha
            query = f'artist:"{artist_name}" AND status:official AND (type:album OR type:ep)'
            
            await self._rate_limit()
            
            data = await self._make_request(
                "release-group",
                {
                    "query": query,
                    "limit": 100  # Obtener más para poder ordenar
                }
            )
            
            release_groups = data.get("release-groups", [])
            
            if not release_groups:
                logger.info(f"   ⚠️ No se encontraron releases para '{artist_name}'")
                return []
            
            # Parsear y ordenar por fecha
            all_releases = []
            for rg in release_groups:
                # Extraer información del artista
                artist_credit = rg.get("artist-credit", [])
                artist_name_from_mb = None
                artist_mbid = None
                
                if artist_credit and len(artist_credit) > 0:
                    artist_info = artist_credit[0].get("artist", {})
                    artist_name_from_mb = artist_info.get("name")
                    artist_mbid = artist_info.get("id")
                
                release_date = rg.get("first-release-date")
                
                # Solo agregar si tiene artista y fecha
                if artist_name_from_mb and release_date:
                    all_releases.append({
                        "title": rg.get("title"),
                        "artist": artist_name_from_mb,
                        "artist_mbid": artist_mbid,
                        "date": release_date,
                        "type": rg.get("primary-type"),
                        "mbid": rg.get("id"),
                        "url": f"https://musicbrainz.org/release-group/{rg.get('id')}"
                    })
            
            # Ordenar por fecha (más reciente primero)
            all_releases.sort(key=lambda x: x.get("date", ""), reverse=True)
            
            # Tomar solo los N más recientes
            latest_releases = all_releases[:limit]
            
            logger.info(f"✅ Encontrados {len(latest_releases)} releases de '{artist_name}'")
            
            if latest_releases:
                logger.info(f"   📝 Últimos releases:")
                for r in latest_releases:
                    logger.info(f"      {r.get('title')} ({r.get('date')})")
            
            return latest_releases
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo releases de '{artist_name}': {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_recent_releases_for_artists(
        self, 
        artist_names: List[str], 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Obtener releases recientes de una lista específica de artistas
        
        Este método es MUCHO más eficiente que buscar todos los releases globales.
        En lugar de descargar miles de releases y filtrar, solo busca releases
        de los artistas específicos de tu biblioteca.
        
        Args:
            artist_names: Lista de nombres de artistas de tu biblioteca
            days: Días hacia atrás desde hoy (default: 30)
        
        Returns:
            Lista de releases de esos artistas específicos
        """
        try:
            from datetime import datetime, timedelta
            import logging
            import os
            logger = logging.getLogger(__name__)
            
            # Calcular rango de fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"🔍 Buscando releases de {len(artist_names)} artistas desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}...")
            logger.info(f"   📅 DEBUG: Fecha actual del sistema: {end_date}")
            logger.info(f"   📅 DEBUG: Fecha inicio: {start_date}")
            
            all_releases = []
            
            # Procesar artistas en lotes (chunks) para no hacer queries demasiado largas
            chunk_size = 10  # 10 artistas por query
            total_chunks = (len(artist_names) + chunk_size - 1) // chunk_size
            
            for chunk_idx in range(0, len(artist_names), chunk_size):
                chunk = artist_names[chunk_idx:chunk_idx + chunk_size]
                chunk_num = (chunk_idx // chunk_size) + 1
                
                # Construcción de query con OR para múltiples artistas
                # Usar búsqueda exacta para evitar coincidencias parciales
                # Ejemplo: (artist:"Pink Floyd" OR artist:"Queen" OR ...)
                artist_queries = ' OR '.join([f'artist:"{name}"' for name in chunk])
                
                query = (
                    f'firstreleasedate:[{start_date.strftime("%Y-%m-%d")} TO {end_date.strftime("%Y-%m-%d")}] '
                    f'AND status:official '
                    f'AND (type:album OR type:ep) '
                    f'AND ({artist_queries})'
                )
                
                logger.info(f"   🔍 Chunk {chunk_num}/{total_chunks}: Buscando releases de {len(chunk)} artistas...")
                logger.info(f"   📝 Artistas en este chunk: {chunk}")
                
                # Hacer request a MusicBrainz
                await self._rate_limit()
                
                data = await self._make_request(
                    "release-group",
                    {
                        "query": query,
                        "limit": 100  # Suficiente para 10 artistas en un período corto
                    }
                )
                
                release_groups = data.get("release-groups", [])
                
                # Parsear releases
                for rg in release_groups:
                    # Extraer información del artista
                    artist_credit = rg.get("artist-credit", [])
                    artist_name = None
                    artist_mbid = None
                    
                    if artist_credit and len(artist_credit) > 0:
                        artist_info = artist_credit[0].get("artist", {})
                        artist_name = artist_info.get("name")
                        artist_mbid = artist_info.get("id")
                    
                    # Solo agregar si tiene artista Y coincide exactamente con uno de la biblioteca
                    if artist_name and artist_name in chunk:
                        logger.info(f"      ✅ Release válido: {artist_name} - {rg.get('title')}")
                        all_releases.append({
                            "title": rg.get("title"),
                            "artist": artist_name,
                            "artist_mbid": artist_mbid,
                            "date": rg.get("first-release-date"),
                            "type": rg.get("primary-type"),
                            "mbid": rg.get("id"),
                            "url": f"https://musicbrainz.org/release-group/{rg.get('id')}"
                        })
                    elif artist_name:
                        logger.info(f"      ❌ Release filtrado (artista no en biblioteca): {artist_name} - {rg.get('title')}")
                
                logger.info(f"      ✅ {len(release_groups)} releases encontrados en este chunk")
            
            logger.info(f"✅ Total de releases encontrados: {len(all_releases)}")
            
            # DEBUG: Mostrar algunos ejemplos
            if all_releases:
                logger.info(f"   📝 DEBUG - Primeros 5 releases encontrados:")
                for r in all_releases[:5]:
                    logger.info(f"      {r.get('artist')} - {r.get('title')} ({r.get('date')})")
            
            return all_releases
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo releases de artistas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_all_recent_releases(self, days: int = 30) -> List[Dict[str, Any]]:
        """Obtener todos los releases recientes del período especificado
        
        Este método realiza UNA búsqueda global a MusicBrainz para obtener
        todos los lanzamientos del período, en lugar de consultar artista por artista.
        
        Args:
            days: Días hacia atrás desde hoy (default: 30)
        
        Returns:
            Lista de releases con información completa
        """
        try:
            from datetime import datetime, timedelta
            import logging
            import os
            logger = logging.getLogger(__name__)
            
            # Calcular rango de fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"🔍 Buscando releases en MusicBrainz desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}...")
            logger.info(f"   📅 DEBUG: Fecha actual del sistema: {end_date}")
            logger.info(f"   📅 DEBUG: Fecha inicio: {start_date}")
            
            # Construcción de query Lucene para MusicBrainz
            # firstreleasedate: fecha de primer lanzamiento
            # status:official: solo lanzamientos oficiales (no bootlegs)
            # type:album OR type:ep: álbumes y EPs
            query = (
                f'firstreleasedate:[{start_date.strftime("%Y-%m-%d")} TO {end_date.strftime("%Y-%m-%d")}] '
                f'AND status:official AND (type:album OR type:ep)'
            )
            
            all_releases = []
            offset = 0
            limit = 100  # MusicBrainz permite máximo 100 por request
            
            # Paginación para obtener todos los resultados
            while True:
                await self._rate_limit()
                
                data = await self._make_request(
                    "release-group",
                    {
                        "query": query,
                        "limit": limit,
                        "offset": offset
                    }
                )
                
                release_groups = data.get("release-groups", [])
                
                if not release_groups:
                    break
                
                # Parsear releases
                for rg in release_groups:
                    # Extraer información del artista
                    artist_credit = rg.get("artist-credit", [])
                    artist_name = None
                    artist_mbid = None
                    
                    if artist_credit and len(artist_credit) > 0:
                        artist_info = artist_credit[0].get("artist", {})
                        artist_name = artist_info.get("name")
                        artist_mbid = artist_info.get("id")
                    
                    # Solo agregar si tiene artista
                    if artist_name:
                        all_releases.append({
                            "title": rg.get("title"),
                            "artist": artist_name,
                            "artist_mbid": artist_mbid,
                            "date": rg.get("first-release-date"),
                            "type": rg.get("primary-type"),
                            "mbid": rg.get("id"),
                            "url": f"https://musicbrainz.org/release-group/{rg.get('id')}"
                        })
                
                logger.info(f"   📊 Obtenidos {len(release_groups)} releases (offset: {offset}, total acumulado: {len(all_releases)})")
                
                # Si obtuvimos menos del límite, ya no hay más
                if len(release_groups) < limit:
                    break
                
                offset += limit
                
                # Límite de seguridad: máximo 2000 releases (configurable)
                max_releases = int(os.getenv("MUSICBRAINZ_MAX_RELEASES", "2000"))
                if offset >= max_releases:
                    logger.warning(f"   ⚠️ Límite de seguridad alcanzado ({max_releases} releases)")
                    logger.info(f"   💡 Puedes aumentar este límite con MUSICBRAINZ_MAX_RELEASES en .env")
                    break
            
            logger.info(f"✅ Total de releases encontrados: {len(all_releases)}")
            
            # DEBUG: Mostrar algunos ejemplos
            if all_releases:
                logger.info(f"   📝 DEBUG - Primeros 5 releases encontrados:")
                for r in all_releases[:5]:
                    logger.info(f"      {r.get('artist')} - {r.get('title')} ({r.get('date')})")
            return all_releases
            
        except Exception as e:
            print(f"❌ Error obteniendo releases recientes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def match_releases_with_library(
        self, 
        recent_releases: List[Dict[str, Any]], 
        library_artists: List[Any]
    ) -> List[Dict[str, Any]]:
        """Hacer matching de releases con artistas de la biblioteca
        
        Usa normalización de texto para comparar nombres de artistas,
        manejando variaciones comunes (mayúsculas, "The", acentos, etc.)
        
        Args:
            recent_releases: Lista de releases de MusicBrainz
            library_artists: Lista de artistas de Navidrome
        
        Returns:
            Lista de releases que coinciden con la biblioteca
        """
        import unicodedata
        import re
        
        def normalize_artist_name(name: str) -> str:
            """Normalizar nombre de artista para comparación
            
            Ejemplos:
                "The Beatles" -> "beatles"
                "Café Tacvba" -> "cafe tacvba"
                "MGMT" -> "mgmt"
            """
            if not name:
                return ""
            
            # Convertir a minúsculas
            normalized = name.lower()
            
            # Eliminar "the" al inicio
            normalized = re.sub(r'^\s*the\s+', '', normalized)
            
            # Normalizar Unicode (eliminar acentos)
            nfd = unicodedata.normalize('NFD', normalized)
            normalized = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
            
            # Eliminar puntuación excepto espacios
            normalized = re.sub(r'[^\w\s]', '', normalized)
            
            # Normalizar espacios
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            
            return normalized
        
        # Crear conjunto de nombres normalizados de la biblioteca
        library_names = set()
        library_name_map = {}  # normalizado -> nombre original
        
        for artist in library_artists:
            original = artist.name if hasattr(artist, 'name') else str(artist)
            normalized = normalize_artist_name(original)
            library_names.add(normalized)
            if normalized not in library_name_map:
                library_name_map[normalized] = original
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"📚 Artistas en biblioteca: {len(library_names)}")
        logger.info(f"🔍 Releases a verificar: {len(recent_releases)}")
        
        # DEBUG: Mostrar algunos ejemplos de artistas de biblioteca
        library_sample = list(library_names)[:10]
        logger.info(f"   📝 DEBUG - Muestra de artistas en biblioteca (normalizados):")
        for artist in library_sample:
            logger.info(f"      '{artist}'")
        
        # DEBUG: Mostrar algunos ejemplos de releases
        if recent_releases:
            logger.info(f"   📝 DEBUG - Muestra de releases encontrados:")
            for r in recent_releases[:5]:
                logger.info(f"      {r['artist']} - {r['title']} ({r['date']})")
        
        # Filtrar releases que coincidan
        matching_releases = []
        
        for release in recent_releases:
            artist_normalized = normalize_artist_name(release["artist"])
            
            if artist_normalized in library_names:
                # Agregar el nombre original de la biblioteca
                release["matched_library_name"] = library_name_map.get(artist_normalized)
                matching_releases.append(release)
                logger.info(f"   ✅ MATCH: '{release['artist']}' → '{artist_normalized}' encontrado en biblioteca")
        
        logger.info(f"✅ Releases coincidentes: {len(matching_releases)}")
        
        # DEBUG: Si no hay matches, mostrar más info
        if not matching_releases and recent_releases:
            logger.warning(f"   ⚠️ DEBUG - No se encontraron matches. Verificando normalización...")
            for release in recent_releases[:10]:
                artist_norm = normalize_artist_name(release["artist"])
                in_lib = artist_norm in library_names
                logger.info(f"      '{release['artist']}' → '{artist_norm}' | en biblioteca: {in_lib}")
        
        return matching_releases
    
    async def get_artist_relationships(
        self,
        artist_name: str,
        relation_types: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Obtener relaciones de un artista (colaboraciones, miembros, etc.)
        
        Args:
            artist_name: Nombre del artista
            relation_types: Tipos de relaciones a buscar. Si None, obtiene todas.
                Ejemplos: "member of band", "collaboration", "supporting musician"
        
        Returns:
            Diccionario agrupado por tipo de relación con artistas relacionados
        """
        try:
            print(f"🔍 Buscando relaciones de '{artist_name}'...")
            
            # Buscar el artista primero
            await self._rate_limit()
            artist_data = await self._search_and_get_artist(artist_name)
            
            if not artist_data.get("found"):
                print(f"   ⚠️ Artista '{artist_name}' no encontrado")
                return {}
            
            artist_id = artist_data.get("id")
            
            # Obtener detalles con relaciones
            await self._rate_limit()
            details = await self._make_request(
                f"artist/{artist_id}",
                {"inc": "artist-rels"}
            )
            
            if not details:
                return {}
            
            # Parsear relaciones
            relations = details.get("relations", [])
            grouped_relations = {}
            
            for relation in relations:
                rel_type = relation.get("type")
                
                # Filtrar por tipos si se especificaron
                if relation_types and rel_type not in relation_types:
                    continue
                
                # Solo procesar relaciones con artistas
                if "artist" not in relation:
                    continue
                
                related_artist = relation.get("artist", {})
                
                if rel_type not in grouped_relations:
                    grouped_relations[rel_type] = []
                
                grouped_relations[rel_type].append({
                    "name": related_artist.get("name"),
                    "mbid": related_artist.get("id"),
                    "type": related_artist.get("type"),
                    "direction": relation.get("direction", "forward"),
                    "url": f"https://musicbrainz.org/artist/{related_artist.get('id')}"
                })
            
            print(f"✅ Encontradas {sum(len(v) for v in grouped_relations.values())} relaciones")
            return grouped_relations
            
        except Exception as e:
            print(f"❌ Error obteniendo relaciones: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def discover_similar_artists(
        self,
        artist_name: str,
        library_artists: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Descubrir artistas similares de tu biblioteca basándose en metadatos
        
        Busca artistas en tu biblioteca que compartan:
        - Géneros/tags similares
        - Mismo país/área
        - Misma época
        - Relaciones directas (colaboraciones, miembros)
        
        Args:
            artist_name: Artista de referencia
            library_artists: Lista de artistas en tu biblioteca
            limit: Máximo de artistas similares a retornar
        
        Returns:
            Lista de artistas similares ordenados por relevancia
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🔍 Buscando artistas similares a '{artist_name}' en biblioteca...")
            
            # Obtener metadata del artista de referencia
            reference = await self.verify_artist_metadata(artist_name)
            
            if not reference.get("found"):
                logger.warning(f"   ⚠️ Artista de referencia no encontrado")
                return []
            
            # Obtener relaciones directas (si existen)
            relationships = await self.get_artist_relationships(artist_name)
            related_names = set()
            for rel_type, artists in relationships.items():
                for artist in artists:
                    related_names.add(artist["name"].lower())
            
            # Calcular similitud con cada artista de la biblioteca
            similarities = []
            
            for lib_artist in library_artists[:100]:  # Limitar para no exceder rate limit
                # Verificar metadata
                lib_metadata = await self.verify_artist_metadata(lib_artist)
                
                if not lib_metadata.get("found"):
                    continue
                
                # Calcular score de similitud
                score = 0
                reasons = []
                
                # 1. Relación directa (muy fuerte)
                if lib_artist.lower() in related_names:
                    score += 50
                    reasons.append("colaboración/relación directa")
                
                # 2. Géneros compartidos
                ref_genres = set(g.lower() for g in reference.get("genres", []))
                lib_genres = set(g.lower() for g in lib_metadata.get("genres", []))
                genre_overlap = len(ref_genres & lib_genres)
                if genre_overlap > 0:
                    score += genre_overlap * 10
                    reasons.append(f"{genre_overlap} género(s) en común")
                
                # 3. Tags compartidos
                ref_tags = set(t.lower() for t in reference.get("tags", [])[:10])
                lib_tags = set(t.lower() for t in lib_metadata.get("tags", [])[:10])
                tag_overlap = len(ref_tags & lib_tags)
                if tag_overlap > 0:
                    score += tag_overlap * 5
                    reasons.append(f"{tag_overlap} tag(s) en común")
                
                # 4. Mismo país
                if reference.get("country") and reference.get("country") == lib_metadata.get("country"):
                    score += 15
                    reasons.append(f"mismo país ({reference.get('country')})")
                
                # 5. Misma área (más flexible que país)
                if reference.get("area") and reference.get("area") == lib_metadata.get("area"):
                    score += 10
                    reasons.append(f"misma área ({reference.get('area')})")
                
                # 6. Época similar (±5 años)
                ref_year = reference.get("life_span", {}).get("begin")
                lib_year = lib_metadata.get("life_span", {}).get("begin")
                
                if ref_year and lib_year:
                    try:
                        ref_y = int(ref_year.split("-")[0]) if isinstance(ref_year, str) else ref_year
                        lib_y = int(lib_year.split("-")[0]) if isinstance(lib_year, str) else lib_year
                        
                        year_diff = abs(ref_y - lib_y)
                        if year_diff <= 5:
                            score += 10
                            reasons.append(f"época similar ({lib_y})")
                        elif year_diff <= 10:
                            score += 5
                    except:
                        pass
                
                if score > 0:
                    similarities.append({
                        "name": lib_artist,
                        "score": score,
                        "reasons": reasons,
                        "metadata": {
                            "genres": lib_metadata.get("genres", [])[:3],
                            "country": lib_metadata.get("country"),
                            "tags": lib_metadata.get("tags", [])[:3]
                        }
                    })
                    logger.info(f"   ✓ {lib_artist}: score={score} ({', '.join(reasons)})")
            
            # Ordenar por score
            similarities.sort(key=lambda x: x["score"], reverse=True)
            
            result = similarities[:limit]
            logger.info(f"✅ Encontrados {len(result)} artistas similares")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error descubriendo artistas similares: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def find_similar_by_tags(
        self,
        artist_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Buscar artistas similares globalmente usando tags/géneros de MusicBrainz
        
        Busca artistas que compartan tags y géneros similares sin necesidad
        de tener una biblioteca específica.
        
        Args:
            artist_name: Artista de referencia
            limit: Máximo de artistas similares a retornar
        
        Returns:
            Lista de artistas similares
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🔍 Buscando artistas similares globalmente a '{artist_name}'...")
            
            # Obtener metadata del artista de referencia
            reference = await self.verify_artist_metadata(artist_name)
            
            if not reference.get("found"):
                logger.warning(f"   ⚠️ Artista de referencia no encontrado en MusicBrainz")
                logger.info(f"   💡 Intenta verificar el nombre exacto del artista")
                return []
            
            logger.info(f"   ✅ Artista encontrado: {reference.get('name')} (MBID: {reference.get('id')})")
            
            # Obtener géneros y tags principales
            ref_genres = reference.get("genres", [])[:3]  # Top 3 géneros
            ref_tags = reference.get("tags", [])[:5]  # Top 5 tags
            
            logger.info(f"   📊 Géneros: {ref_genres}")
            logger.info(f"   🏷️ Tags: {ref_tags}")
            
            if not ref_genres and not ref_tags:
                logger.warning(f"   ⚠️ No hay tags/géneros para '{artist_name}'")
                logger.info(f"   💡 Este artista no tiene metadata suficiente en MusicBrainz")
                return []
            
            # Buscar por los tags más relevantes
            search_tags = ref_genres + ref_tags
            similar_artists = []
            seen_artists = set([artist_name.lower()])
            
            # OPTIMIZACIÓN: Reducido de 3 a 2 tags para ser más rápido (cada búsqueda tarda ~1 seg)
            for tag in search_tags[:2]:  # Usar solo los 2 tags principales
                if len(similar_artists) >= limit:
                    break
                
                logger.info(f"   🔍 Buscando artistas con tag '{tag}'...")
                await self._rate_limit()
                
                # Buscar artistas con este tag
                # OPTIMIZACIÓN: Reducido de 20 a 15 para ser más rápido
                data = await self._make_request(
                    "artist",
                    {
                        "query": f'tag:"{tag}"',
                        "limit": 15
                    }
                )
                
                artists = data.get("artists", [])
                logger.info(f"   📊 Encontrados {len(artists)} artistas con tag '{tag}'")
                
                for artist in artists:
                    if len(similar_artists) >= limit:
                        break
                    
                    name = artist.get("name")
                    if name and name.lower() not in seen_artists:
                        # Evitar personas individuales, queremos bandas/proyectos
                        if artist.get("type") not in ['Person']:
                            similar_artists.append({
                                "name": name,
                                "mbid": artist.get("id"),
                                "score": artist.get("score", 0),
                                "shared_tag": tag,
                                "type": artist.get("type")
                            })
                            seen_artists.add(name.lower())
            
            logger.info(f"✅ Encontrados {len(similar_artists)} artistas similares por tags")
            return similar_artists
            
        except Exception as e:
            logger.error(f"❌ Error buscando similares por tags: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_artist_top_albums_enhanced(
        self,
        artist_name: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtener álbumes top de un artista con más detalles
        
        Similar a get_artist_top_albums pero con información adicional
        para recomendaciones.
        
        Args:
            artist_name: Nombre del artista
            limit: Número de álbumes a obtener
        
        Returns:
            Lista de álbumes con metadata completa
        """
        try:
            # Reutilizar el método existente pero agregar más información
            albums = await self.get_artist_top_albums(artist_name, limit)
            
            # Agregar información adicional si está disponible
            enhanced_albums = []
            for album in albums:
                enhanced = {
                    **album,
                    "recommendation_score": album.get("playcount", 0) / 1000,  # Normalizar
                    "source": "musicbrainz"
                }
                enhanced_albums.append(enhanced)
            
            return enhanced_albums
            
        except Exception as e:
            print(f"❌ Error obteniendo álbumes: {e}")
            return []
    
    async def get_artist_top_tracks_enhanced(
        self,
        artist_name: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtener canciones top de un artista con más detalles
        
        Similar a get_artist_top_tracks pero preparado para recomendaciones.
        """
        try:
            tracks = await self.get_artist_top_tracks(artist_name, limit)
            
            enhanced_tracks = []
            for track in tracks:
                enhanced = {
                    "name": track.name,
                    "artist": track.artist,
                    "playcount": track.playcount or 0,
                    "url": track.url,
                    "image_url": track.image_url,
                    "source": "musicbrainz"
                }
                enhanced_tracks.append(enhanced)
            
            return enhanced_tracks
            
        except Exception as e:
            print(f"❌ Error obteniendo tracks: {e}")
            return []
    
    async def close(self):
        """Cerrar conexión y guardar cache"""
        await self.client.aclose()
        # Guardar cache al cerrar
        self._save_cache()

