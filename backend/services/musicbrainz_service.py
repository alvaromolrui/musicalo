import httpx
import os
import asyncio
from typing import Optional, Dict, Any, List

class MusicBrainzService:
    """Servicio para enriquecer y verificar metadatos usando MusicBrainz
    
    Propósito principal: Búsqueda inversa para identificar artistas de la biblioteca
    que cumplan con criterios específicos (género, país, época) cuando los metadatos
    locales son insuficientes o inexactos.
    """
    
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
        
        # Cache persistente en memoria para toda la sesión
        self._cache = {}
        
        # Rate limiting: última petición
        self._last_request_time = 0
    
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
        max_artists: int = 50
    ) -> List[Dict[str, Any]]:
        """Buscar qué artistas de la biblioteca cumplen con filtros específicos
        
        Este es el método clave para la búsqueda "inversa":
        - Toma una lista de artistas de la biblioteca local
        - Consulta MusicBrainz para cada uno
        - Devuelve solo los que cumplen los filtros
        
        Args:
            library_artists: Lista de nombres de artistas de tu biblioteca
            filters: Filtros a aplicar (genre, country, year_from, year_to)
            max_artists: Máximo de artistas a verificar (para no hacer miles de requests)
        
        Returns:
            Lista de artistas que cumplen con los filtros, con su info de MusicBrainz
        """
        try:
            print(f"🔍 MusicBrainz: Verificando {len(library_artists)} artistas de biblioteca...")
            print(f"   Filtros: {filters}")
            
            matching_artists = []
            checked_count = 0
            
            # Limitar la cantidad para no hacer demasiadas requests
            artists_to_check = library_artists[:max_artists]
            
            for i, artist_name in enumerate(artists_to_check):
                checked_count += 1
                
                # Verificar el artista contra los filtros
                verification = await self.verify_artist_metadata(artist_name, filters)
                
                if verification.get("matches", False):
                    matching_artists.append({
                        "name": artist_name,
                        "mb_data": verification
                    })
                    print(f"   ✅ [{i+1}/{len(artists_to_check)}] {artist_name} - CUMPLE")
                else:
                    print(f"   ❌ [{i+1}/{len(artists_to_check)}] {artist_name} - no cumple")
                
                # Mostrar progreso cada 10 artistas
                if (i + 1) % 10 == 0:
                    print(f"   📊 Progreso: {i+1}/{len(artists_to_check)} verificados, {len(matching_artists)} coinciden")
            
            print(f"✅ MusicBrainz: {len(matching_artists)}/{checked_count} artistas cumplen los filtros")
            
            return matching_artists
            
        except Exception as e:
            print(f"❌ Error en búsqueda inversa de MusicBrainz: {e}")
            import traceback
            traceback.print_exc()
            return []
    
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
            # Verificar cache
            cache_key = f"artist_{artist_name.lower()}"
            if cache_key in self._cache:
                artist_info = self._cache[cache_key]
            else:
                # Buscar artista
                artist_info = await self._search_and_get_artist(artist_name)
                
                if not artist_info or not artist_info.get("found"):
                    return {
                        "found": False,
                        "matches": False,
                        "artist_name": artist_name
                    }
                
                # Guardar en cache
                self._cache[cache_key] = artist_info
            
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
        """Cerrar conexión"""
        await self.client.aclose()

