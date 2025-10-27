import google.generativeai as genai
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.musicbrainz_service import MusicBrainzService
from services.conversation_manager import ConversationManager
from services.system_prompts import SystemPrompts

class MusicAgentService:
    """
    Agente musical inteligente que combina todas las fuentes de datos
    para responder consultas conversacionales sobre música
    """
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Gestor de conversaciones
        self.conversation_manager = ConversationManager()
        
        # Inicializar servicios disponibles
        self.navidrome = NavidromeService()
        
        self.listenbrainz = None
        listenbrainz_available = False
        if os.getenv("LISTENBRAINZ_USERNAME"):
            try:
                self.listenbrainz = ListenBrainzService()
                print("✅ Agente musical: ListenBrainz configurado")
                listenbrainz_available = True
            except Exception as e:
                print(f"⚠️ Agente musical: Error inicializando ListenBrainz: {e}")
        
        # Determinar servicios para cada propósito
        # HISTORIAL Y DESCUBRIMIENTO: ListenBrainz (open-source, sin límites)
        if listenbrainz_available and self.listenbrainz:
            self.history_service = self.listenbrainz
            self.history_service_name = "ListenBrainz"
            self.discovery_service = self.listenbrainz
        else:
            self.history_service = None
            self.history_service_name = None
            self.discovery_service = None
        
        # MUSICBRAINZ: Para verificación de metadatos
        self.musicbrainz = None
        if os.getenv("ENABLE_MUSICBRAINZ", "true").lower() == "true":
            try:
                self.musicbrainz = MusicBrainzService()
                print("✅ Agente musical: MusicBrainz habilitado para verificación de metadatos")
            except Exception as e:
                print(f"⚠️ Agente musical: Error inicializando MusicBrainz: {e}")
        
        # Sistema de caché simple con TTL para optimizar rendimiento
        self._cache = {}
        self._cache_ttl = {}
        
        print(f"📊 Servicio de historial: {self.history_service_name if self.history_service_name else 'No disponible'}")
        print(f"🔍 Servicio de descubrimiento: {'ListenBrainz' if self.discovery_service else 'No disponible'}")
    
    def _get_cache(self, key: str, ttl_seconds: int = 300):
        """Obtener del caché si no ha expirado
        
        Args:
            key: Clave del caché
            ttl_seconds: Tiempo de vida en segundos (default: 5 minutos)
            
        Returns:
            Valor del caché o None si expiró o no existe
        """
        if key in self._cache:
            if key in self._cache_ttl:
                if datetime.now() < self._cache_ttl[key]:
                    print(f"⚡ Cache hit: {key}")
                    return self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: any, ttl_seconds: int = 300):
        """Guardar en caché con TTL
        
        Args:
            key: Clave del caché
            value: Valor a guardar
            ttl_seconds: Tiempo de vida en segundos (default: 5 minutos)
        """
        self._cache[key] = value
        self._cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    async def _get_with_fallback(self, primary_method, fallback_method, *args, **kwargs):
        """Intenta ejecutar un método con fallback automático si falla
        
        Args:
            primary_method: Método principal a ejecutar
            fallback_method: Método de fallback si el principal falla
            *args, **kwargs: Argumentos para los métodos
            
        Returns:
            Resultado del método que funcione
        """
        try:
            if primary_method:
                result = await primary_method(*args, **kwargs)
                if result:  # Si devuelve datos, usarlos
                    return result
        except Exception as e:
            print(f"⚠️ Método principal falló ({e}), usando fallback...")
        
        # Intentar con fallback
        try:
            if fallback_method:
                return await fallback_method(*args, **kwargs)
        except Exception as e:
            print(f"⚠️ Fallback también falló: {e}")
        
        return []  # Devolver lista vacía si ambos fallan
    
    async def query(
        self, 
        user_question: str, 
        user_id: int,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Procesar consulta del usuario usando todas las fuentes disponibles
        CON SOPORTE CONVERSACIONAL
        
        Args:
            user_question: Pregunta o consulta del usuario
            user_id: ID del usuario para mantener contexto conversacional
            context: Contexto adicional (opcional)
            
        Returns:
            Diccionario con la respuesta y datos utilizados
            
        Ejemplos:
            - "¿Qué álbumes de Pink Floyd tengo en mi biblioteca?"
            - "Dame información sobre el último artista que escuché"
            - "¿Cuántas veces he escuchado a Queen?"
            - "Dime álbumes similares a The Dark Side of the Moon"
            - "Ponme algo parecido" (usa contexto de conversación)
        """
        
        print(f"🤖 Agente musical procesando: {user_question}")
        
        # Obtener sesión conversacional del usuario
        session = self.conversation_manager.get_session(user_id)
        session.add_message("user", user_question)
        
        # 1. Recopilar datos de todas las fuentes
        # OPTIMIZACIÓN: Agregar timeout de 20 segundos para evitar esperas muy largas
        try:
            data_context = await asyncio.wait_for(
                self._gather_all_data(user_question, user_id),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            print("⚠️ Timeout obteniendo datos (20s), usando datos parciales")
            data_context = {
                "library": {},
                "listening_history": {},
                "search_results": {},
                "similar_content": [],
                "new_discoveries": []
            }
        
        # Si el usuario pidió "busca más" pero no hay búsqueda anterior
        if data_context.get("no_active_search"):
            return {
                "answer": data_context.get("message"),
                "data_used": {},
                "links": [],
                "success": True,
                "session_id": user_id
            }
        
        # 2. Obtener estadísticas del usuario con contexto adaptativo en 3 niveles
        # NIVEL 1: Contexto mínimo (SIEMPRE, muy rápido con caché largo)
        user_stats = await self._get_minimal_context(user_id)
        
        # NIVEL 2: Contexto enriquecido (cuando hay palabras clave de recomendación)
        needs_user_context = any(phrase in user_question.lower() for phrase in [
            "recomienda", "recomiéndame", "sugerencia", "sugiere",
            "ponme", "parecido", "similar", "nuevo", "descubrir",
            "mis gustos", "mi perfil", "personalizado"
        ])
        
        if needs_user_context:
            print("📊 Enriqueciendo contexto (recomendación detectada)...")
            user_stats = await self._get_enriched_context(user_id, user_stats)
        
        # NIVEL 3: Contexto completo (cuando se pregunta explícitamente)
        needs_full_context = any(phrase in user_question.lower() for phrase in [
            "mi biblioteca", "qué tengo", "mis escuchas", "mis estadísticas",
            "mi perfil musical", "qué he escuchado", "cuánto he escuchado",
            "mis favoritos", "mis stats"
        ])
        
        if needs_full_context:
            print("📚 Obteniendo contexto completo (consulta de perfil)...")
            user_stats = await self._get_full_context(user_id, user_stats)
        
        # 3. Construir prompt inteligente usando SystemPrompts
        conversation_context = session.get_context_for_ai()
        
        # Usar prompt específico para consultas informativas
        if context and context.get("type") == "informational":
            system_prompt = SystemPrompts.get_informational_prompt(
                user_stats=user_stats,
                conversation_context=conversation_context
            )
        else:
            system_prompt = SystemPrompts.get_music_assistant_prompt(
                user_stats=user_stats,
                conversation_context=conversation_context
            )
        
        # 4. Agregar datos específicos de la query
        ai_prompt = f"""{system_prompt}

=== CONSULTA ACTUAL ===
{user_question}

=== DATOS DISPONIBLES ===
{self._format_context_for_ai(data_context)}

REGLAS CRÍTICAS:
1. SIEMPRE consulta PRIMERO la biblioteca (📚) para ver qué tiene el usuario
2. LUEGO complementa con ListenBrainz/MusicBrainz (🌍) para recomendaciones y descubrimientos
3. Si preguntan "mejor disco/álbum de X":
   a) Verifica QUÉ TIENE en biblioteca de ese artista
   b) Combina con información de MusicBrainz
   c) Responde: "En tu biblioteca tienes X, Y, Z. Según MusicBrainz, el mejor es..."
4. Si preguntan "qué tengo de X" → USA SOLO BIBLIOTECA
5. NUNCA digas "no tienes nada" sin VERIFICAR primero en los datos de biblioteca
6. VERIFICA coincidencia exacta de artistas - no mezcles artistas diferentes
7. Sé PROACTIVO: combina siempre biblioteca + descubrimiento

IMPORTANTE - Diferentes tipos de peticiones:

1. "¿Qué álbumes TENGO de [artista]?"
   → Busca SOLO en BIBLIOTECA
   → Si no tiene → "No tienes álbumes de [artista] en tu biblioteca"

2. "Recomiéndame un disco DE [artista]"
   → Busca en BIBLIOTECA primero
   → Si no tiene → Busca en MUSICBRAINZ y recomienda
   → Ejemplo: "No tienes de [artista] en biblioteca, pero en MusicBrainz su mejor álbum es X"

3. "Recomiéndame un disco" (sin artista específico)
   → USA BIBLIOTECA + LISTENBRAINZ/MUSICBRAINZ
   → Combina: algo de su biblioteca + descubrimientos nuevos
   → Ejemplo: "De tu biblioteca: X. También te gustará Y (descubrimiento nuevo)"

4. "Recomiéndame algo nuevo / que no tenga"
   → USA PRINCIPALMENTE LISTENBRAINZ/MUSICBRAINZ
   → Recomienda música que NO está en biblioteca
   → Basado en sus gustos pero nuevo contenido

IMPORTANTE - "Playlist con música DE [artistas]":
- Si piden "playlist de/con [lista de artistas]", busca canciones de ESOS ARTISTAS ESPECÍFICOS
- Ejemplo: "música de mujeres, vera fauna y cala vento" → busca canciones de esos 3 artistas
- VERIFICA que cada canción sea del artista correcto
- Si NO tienes algunos artistas, menciona cuáles SÍ tienes y cuáles NO

IMPORTANTE - CREACIÓN DE PLAYLISTS:
- Cuando el usuario pida crear una playlist, el sistema AUTOMÁTICAMENTE creará la playlist en Navidrome
- Tu respuesta debe incluir las canciones que se van a agregar a la playlist
- Sé específico sobre qué canciones se incluirán y por qué
- Si no hay suficientes canciones, explica por qué y sugiere alternativas

FORMATO DE RESPUESTA:
- Si hay álbumes en biblioteca DEL ARTISTA CORRECTO → Lista y recomienda
- Si hay artistas en biblioteca → Lista los artistas directamente
- Si piden "recomiéndame álbum de X" y NO tienes de X → "No tienes álbumes de X en tu biblioteca"
- Si piden "playlist con X, Y, Z" → Lista qué artistas SÍ tienes y cuáles NO
- NUNCA inventes álbumes o artistas que no aparecen en los datos
- Usa emojis: 📀 para álbumes, 🎤 para artistas, 🎵 para canciones

Responde ahora de forma natural y conversacional:"""
        
        # 5. Generar respuesta con IA
        try:
            response = self.model.generate_content(ai_prompt)
            answer = response.text.strip()
            
            print(f"✅ Agente musical: Respuesta generada ({len(answer)} caracteres)")
            
            # 6. NUEVO: Si es una petición de playlist, crear la playlist en Navidrome
            playlist_created = None
            is_playlist_request = any(phrase in user_question.lower() for phrase in [
                "playlist", "crea una playlist", "crear playlist", "haz una playlist", 
                "hacer playlist", "genera playlist", "generar playlist"
            ])
            
            if is_playlist_request:
                playlist_created = await self._create_playlist_in_navidrome(
                    user_question, data_context, user_id
                )
                
                # Si se creó la playlist, agregar información al mensaje
                if playlist_created:
                    answer += f"\n\n🎵 <b>Playlist creada en Navidrome:</b> {playlist_created['name']}\n"
                    answer += f"📝 <b>Canciones incluidas:</b> {playlist_created['track_count']}\n"
                    answer += f"🆔 <b>ID de playlist:</b> {playlist_created['id']}"
            
            # Guardar respuesta en historial de conversación
            session.add_message("assistant", answer)
            
            return {
                "answer": answer,
                "data_used": data_context,
                "links": self._extract_links(data_context),
                "success": True,
                "session_id": user_id,
                "playlist_created": playlist_created
            }
        
        except Exception as e:
            print(f"❌ Error generando respuesta del agente: {e}")
            return {
                "answer": f"❌ Error procesando tu consulta: {str(e)}",
                "data_used": data_context,
                "links": [],
                "success": False
            }
    
    async def _gather_all_data(self, query: str, user_id: int) -> Dict[str, Any]:
        """Recopilar datos de todas las fuentes disponibles
        
        Args:
            query: Consulta del usuario para determinar qué datos recopilar
            user_id: ID del usuario (para mantener contexto de búsqueda)
            
        Returns:
            Diccionario con todos los datos relevantes
        """
        data = {
            "library": {},
            "listening_history": {},
            "search_results": {},
            "similar_content": [],
            "new_discoveries": []  # NUEVO: Para música que no está en biblioteca
        }
        
        # Detectar palabras clave para optimizar búsquedas
        query_lower = query.lower()
        
        # Detectar comando "busca más"
        is_search_more = any(phrase in query_lower for phrase in [
            "busca más", "buscar más", "busca mas", "buscar mas",
            "más resultados", "más artistas", "continuar", "sigue buscando"
        ])
        
        # Obtener sesión para contexto
        session = self.conversation_manager.get_session(user_id)
        
        if is_search_more:
            print(f"🔍 Comando 'busca más' detectado")
            last_search = session.context.get("last_mb_search", {})
            
            if last_search.get("genre") and last_search.get("has_more"):
                # Continuar búsqueda anterior
                detected_genre = last_search["genre"]
                needs_library_search = True
                is_recommendation_request = False
                search_term = None
                mb_offset = last_search["next_offset"]
                print(f"   Continuando búsqueda de '{detected_genre}' desde artista {mb_offset}")
            else:
                print(f"   ⚠️ No hay búsqueda anterior para continuar")
                # Responder que no hay búsqueda activa
                data["no_active_search"] = True
                data["message"] = "No hay ninguna búsqueda activa que continuar. Primero pregunta por un género, por ejemplo: '¿tengo algo de jazz?'"
                return data
        else:
            mb_offset = 0  # Nueva búsqueda, empezar desde 0
            
            # Detectar si es una petición de RECOMENDACIÓN
            is_recommendation_request = any(word in query_lower for word in [
                "recomienda", "recomiéndame", "sugerencia", "sugiere", "sugiéreme",
                "ponme", "pon", "quiero escuchar", "dame"
            ])
        print(f"🔍 DEBUG - is_recommendation_request: {is_recommendation_request}")
        
        # Detectar géneros musicales comunes
        music_genres = {
            'rock', 'pop', 'jazz', 'blues', 'metal', 'punk', 'indie', 'folk',
            'electrónica', 'electronica', 'house', 'techno', 'hip hop', 'rap',
            'reggae', 'country', 'clásica', 'clasica', 'alternativo', 'alternativa',
            'ska', 'soul', 'funk', 'grunge', 'progressive', 'prog'
        }
        detected_genre = None
        for genre in music_genres:
            if genre in query_lower:
                detected_genre = genre
                break
        
        # IMPORTANTE: "disco" puede ser género (Disco Music) o la palabra española para "álbum"
        # Solo detectar como género si está en contexto específico de género musical
        if 'disco' in query_lower and detected_genre is None:
            # Es género solo si aparece en contextos como:
            # "música disco", "estilo disco", "género disco", "de los 70", etc.
            genre_contexts = ['música disco', 'estilo disco', 'género disco', 'música de disco', 'tipo disco']
            if any(context in query_lower for context in genre_contexts):
                detected_genre = 'disco'
            # Si dice "un disco de X" o "disco de X", NO es género, es álbum
            elif 'disco de' in query_lower or 'un disco' in query_lower or 'el disco' in query_lower:
                detected_genre = None  # Confirmar que no es género
        
        print(f"🔍 DEBUG - detected_genre: '{detected_genre}'")
        
        # Detectar menciones de artistas/álbumes/discos (buscar en biblioteca)
        needs_library_search = any(word in query_lower for word in [
            "tengo", "teengo", "biblioteca", "colección", "poseo", 
            "álbum", "album", "disco", "álbumes", "albums", "discos",
            "mejor disco de", "mejor álbum de", "disco de", "álbum de",
            "discografía", "música de", "canciones de", "temas de", "mi biblioteca",
            "playlist", "crea una playlist", "crear playlist"  # Para playlists SIEMPRE de biblioteca
        ])
        print(f"🔍 DEBUG - needs_library_search: {needs_library_search}")
        
        # Detectar consultas informativas que necesitan biblioteca completa
        is_informational_query = any(phrase in query_lower for phrase in [
            "qué géneros", "qué artistas", "cuántos álbumes", "lista de", "qué tengo de",
            "cuántos artistas", "cuántas canciones", "estadísticas de mi biblioteca",
            "resumen de mi biblioteca", "análisis de mi biblioteca", "que hay de",
            "qué hay de", "tengo de", "tienes de", "en mi biblioteca", "de mi biblioteca",
            "que tengo de", "qué tengo de", "tengo de la", "tengo del", "tengo de los",
            "tengo de las", "tienes de la", "tienes del", "tienes de los", "tienes de las"
        ])
        print(f"🔍 DEBUG - is_informational_query: {is_informational_query}")
        
        needs_listening_history = any(word in query_lower for word in [
            "escuché", "escuchado", "última", "reciente", "top", "favorito", "estadística", "últimos"
        ])
        
        # Detectar cuando el usuario pide descubrir música nueva (que NO tenga)
        needs_new_music = any(word in query_lower for word in [
            "nuevo", "nueva", "nuevos", "nuevas", "no tenga", "no tengo", "descubrir"
        ]) and not any(word in query_lower for word in ["mi biblioteca", "tengo", "teengo"])
        
        # Detectar cuando el usuario pregunta por lanzamientos recientes
        needs_recent_releases = any(word in query_lower for word in [
            "lanzamientos", "releases", "últimos", "recientes", "sacado", "han sacado"
        ]) or any(phrase in query_lower for phrase in [
            "qué hay nuevo", "música nueva", "últimos álbumes", "nuevos lanzamientos"
        ])
        
        # Detectar cuando preguntan por reproducción actual
        needs_now_playing = any(word in query_lower for word in [
            "estoy escuchando", "está sonando", "suena ahora", "está reproduciendo",
            "reproduciendo", "playing", "now playing", "qué suena", "escuchando ahora",
            "sonando ahora", "qué está sonando", "reproduciendo ahora", "play ahora"
        ])
        
        # Extraer término de búsqueda 
        # Si es recomendación + género, no extraer término (usar género)
        if is_recommendation_request and detected_genre:
            search_term = None  # No buscar artista específico
        elif needs_library_search:
            search_term = self._extract_search_term(query)
            # Si el término extraído coincide con el género detectado, priorizar género
            if detected_genre and search_term and detected_genre.lower() in search_term.lower():
                search_term = None  # Es una búsqueda de género, no de artista
        else:
            search_term = None
        
        print(f"🔍 DEBUG - search_term extraído: '{search_term}'")
        
        # Datos de reproducción actual (Navidrome)
        if needs_now_playing:
            try:
                print(f"🎵 Obteniendo reproducción actual...")
                now_playing = await self.navidrome.get_now_playing()
                data["now_playing"] = now_playing
                print(f"✅ Obtenida información de {len(now_playing)} reproducciones activas")
            except Exception as e:
                print(f"⚠️ Error obteniendo now playing: {e}")
                data["now_playing"] = []
        
        # Datos de biblioteca completa para consultas informativas (PRIORIDAD ALTA)
        if is_informational_query:
            try:
                print(f"📊 Obteniendo biblioteca completa para consulta informativa...")
                
                # Obtener TODA la biblioteca
                all_artists = await self.navidrome.get_all_artists()
                all_albums = await self.navidrome.get_all_albums()
                all_tracks = await self.navidrome.get_all_tracks()
                
                # Organizar datos para análisis
                data["library"]["complete_data"] = {
                    "artists": all_artists,
                    "albums": all_albums,
                    "tracks": all_tracks,
                    "total_artists": len(all_artists),
                    "total_albums": len(all_albums),
                    "total_tracks": len(all_tracks)
                }
                
                # Extraer géneros únicos de todos los tracks
                genres = set()
                for track in all_tracks:
                    if track.genre:
                        genres.add(track.genre)
                
                data["library"]["complete_data"]["genres"] = sorted(list(genres))
                data["library"]["complete_data"]["total_genres"] = len(genres)
                
                # Extraer artistas únicos
                unique_artists = set()
                for track in all_tracks:
                    if track.artist:
                        unique_artists.add(track.artist)
                
                data["library"]["complete_data"]["unique_artists"] = sorted(list(unique_artists))
                data["library"]["complete_data"]["unique_artists_count"] = len(unique_artists)
                
                # Si hay un género detectado en la consulta, marcar para análisis inteligente
                if detected_genre:
                    print(f"🎸 Género detectado: '{detected_genre}' - Usando análisis inteligente de IA")
                    
                    # En lugar de filtrar estrictamente, marcar el género para que la IA lo analice
                    data["library"]["complete_data"]["genre_query"] = {
                        "requested_genre": detected_genre,
                        "analysis_mode": "intelligent",  # La IA analizará toda la biblioteca
                        "total_artists": len(all_artists),
                        "total_albums": len(all_albums),
                        "total_tracks": len(all_tracks)
                    }
                    
                    print(f"✅ Marcado para análisis inteligente de '{detected_genre}' en {len(all_artists)} artistas, {len(all_albums)} álbumes, {len(all_tracks)} canciones")
                
                # Si hay un artista específico mencionado en la consulta, filtrar por ese artista
                # PERO solo si NO es una consulta de género
                if not detected_genre:
                    artist_mentioned = self._extract_artist_from_query(query)
                    if artist_mentioned:
                        print(f"🎤 Filtrando biblioteca completa por artista: '{artist_mentioned}'")
                        
                        # Buscar artista por nombre (búsqueda flexible)
                        matching_artists = []
                        for artist in all_artists:
                            if artist_mentioned.lower() in artist.name.lower() or artist.name.lower() in artist_mentioned.lower():
                                matching_artists.append(artist)
                        
                        # Filtrar tracks del artista
                        artist_tracks = [track for track in all_tracks if track.artist and artist_mentioned.lower() in track.artist.lower()]
                        
                        # Filtrar álbumes del artista
                        artist_albums = [album for album in all_albums if album.artist and artist_mentioned.lower() in album.artist.lower()]
                        
                        data["library"]["complete_data"]["filtered_by_artist"] = {
                            "artist": artist_mentioned,
                            "matching_artists": matching_artists,
                            "tracks": artist_tracks,
                            "albums": artist_albums,
                            "total_tracks": len(artist_tracks),
                            "total_albums": len(artist_albums),
                            "total_matching_artists": len(matching_artists)
                        }
                        
                        print(f"✅ Filtrado por '{artist_mentioned}': {len(artist_tracks)} canciones, {len(artist_albums)} álbumes, {len(matching_artists)} artistas coincidentes")
                
                print(f"✅ Biblioteca completa obtenida: {len(all_artists)} artistas, {len(all_albums)} álbumes, {len(all_tracks)} canciones, {len(genres)} géneros")
                
            except Exception as e:
                print(f"❌ Error obteniendo biblioteca completa: {e}")
                data["library"]["complete_data"] = None
        
        # Datos de biblioteca (Navidrome) - búsquedas específicas (solo si NO es consulta informativa)
        elif needs_library_search and not is_informational_query:
            try:
                # Si es recomendación por género, buscar el género
                if is_recommendation_request and detected_genre and not search_term:
                    print(f"🔍 Buscando en biblioteca por GÉNERO: '{detected_genre}' (query: '{query}')")
                    # Buscar por género (Navidrome puede buscar por tags/géneros)
                    search_results = await self.navidrome.search(detected_genre, limit=50)
                    data["library"]["search_results"] = search_results
                    data["library"]["search_term"] = detected_genre
                    data["library"]["is_genre_search"] = True
                    data["library"]["detected_genre"] = detected_genre
                    
                    if any(search_results.values()):
                        data["library"]["has_content"] = True
                        print(f"✅ Encontrado {len(search_results.get('albums', []))} álbumes, {len(search_results.get('artists', []))} artistas de género '{detected_genre}'")
                    else:
                        data["library"]["has_content"] = False
                        print(f"⚠️ No se encontraron resultados para género '{detected_genre}'")
                        
                        # FALLBACK: Usar MusicBrainz para verificar si hay artistas del género
                        if self.musicbrainz:
                            print(f"   🎯 Activando MusicBrainz para verificar género '{detected_genre}'...")
                            mb_results = await self._search_genre_with_musicbrainz(detected_genre, offset=mb_offset)
                            if mb_results and mb_results.get("results"):
                                # Si MusicBrainz encuentra artistas, actualizar los resultados
                                results_data = mb_results["results"]
                                data["library"]["search_results"] = results_data
                                data["library"]["has_content"] = True
                                data["library"]["musicbrainz_verified"] = True
                                print(f"   ✅ MusicBrainz encontró {len(results_data.get('albums', []))} álbumes, {len(results_data.get('artists', []))} artistas de '{detected_genre}'")
                                
                                # Guardar contexto para "busca más"
                                session.context["last_mb_search"] = {
                                    "genre": detected_genre,
                                    "offset": mb_results["offset"],
                                    "next_offset": mb_results["next_offset"],
                                    "has_more": mb_results["has_more"],
                                    "total_artists": mb_results["total_artists"],
                                    "checked_total": mb_results["next_offset"]
                                }
                                
                                # Información para el prompt de la IA
                                if mb_results["has_more"]:
                                    data["library"]["can_search_more"] = True
                                    data["library"]["mb_stats"] = {
                                        "checked": mb_results["next_offset"],
                                        "total": mb_results["total_artists"],
                                        "remaining": mb_results["total_artists"] - mb_results["next_offset"]
                                    }
                
                # Si detectó un género pero NO es recomendación (ej: "tengo algo de jazz?")
                elif detected_genre and not search_term:
                    print(f"🔍 Buscando en biblioteca por GÉNERO (no recomendación): '{detected_genre}' (query: '{query}')")
                    # Buscar por género en Navidrome primero
                    search_results = await self.navidrome.search(detected_genre, limit=50)
                    data["library"]["search_term"] = detected_genre
                    data["library"]["is_genre_search"] = True
                    data["library"]["detected_genre"] = detected_genre
                    
                    local_albums_count = len(search_results.get('albums', []))
                    local_artists_count = len(search_results.get('artists', []))
                    
                    if any(search_results.values()):
                        print(f"✅ Búsqueda local: {local_albums_count} álbumes, {local_artists_count} artistas de '{detected_genre}'")
                    else:
                        print(f"⚠️ Búsqueda local: 0 resultados para '{detected_genre}'")
                    
                    # SIEMPRE usar MusicBrainz para géneros (para complementar y permitir "busca más")
                    if self.musicbrainz:
                        print(f"   🎯 Usando MusicBrainz para verificar más artistas de '{detected_genre}'...")
                        mb_results = await self._search_genre_with_musicbrainz(detected_genre, offset=mb_offset)
                        
                        if mb_results and mb_results.get("results"):
                            # Combinar resultados locales + MusicBrainz (evitando duplicados)
                            results_data = mb_results["results"]
                            
                            # Combinar albums
                            combined_albums = list(search_results.get('albums', []))
                            existing_album_ids = {a.id for a in combined_albums}
                            for album in results_data.get('albums', []):
                                if album.id not in existing_album_ids:
                                    combined_albums.append(album)
                                    existing_album_ids.add(album.id)
                            
                            # Combinar artists
                            combined_artists = list(search_results.get('artists', []))
                            existing_artist_ids = {a.id for a in combined_artists}
                            for artist in results_data.get('artists', []):
                                if artist.id not in existing_artist_ids:
                                    combined_artists.append(artist)
                                    existing_artist_ids.add(artist.id)
                            
                            # Combinar tracks
                            combined_tracks = list(search_results.get('tracks', []))
                            existing_track_ids = {t.id for t in combined_tracks}
                            for track in results_data.get('tracks', []):
                                if track.id not in existing_track_ids:
                                    combined_tracks.append(track)
                                    existing_track_ids.add(track.id)
                            
                            # Usar resultados combinados
                            data["library"]["search_results"] = {
                                "albums": combined_albums,
                                "artists": combined_artists,
                                "tracks": combined_tracks
                            }
                            data["library"]["has_content"] = True
                            data["library"]["musicbrainz_verified"] = True
                            
                            mb_albums = len(results_data.get('albums', []))
                            mb_artists = len(results_data.get('artists', []))
                            print(f"   ✅ MusicBrainz agregó: {mb_albums} álbumes, {mb_artists} artistas")
                            print(f"   📊 Total combinado: {len(combined_albums)} álbumes, {len(combined_artists)} artistas")
                            
                            # Guardar contexto para "busca más" SIEMPRE
                            session.context["last_mb_search"] = {
                                "genre": detected_genre,
                                "offset": mb_results["offset"],
                                "next_offset": mb_results["next_offset"],
                                "has_more": mb_results["has_more"],
                                "total_artists": mb_results["total_artists"],
                                "checked_total": mb_results["next_offset"]
                            }
                            
                            # Información para el prompt de la IA
                            if mb_results["has_more"]:
                                data["library"]["can_search_more"] = True
                                data["library"]["mb_stats"] = {
                                    "checked": mb_results["next_offset"],
                                    "total": mb_results["total_artists"],
                                    "remaining": mb_results["total_artists"] - mb_results["next_offset"]
                                }
                        else:
                            # MusicBrainz no encontró nada adicional, usar solo resultados locales
                            data["library"]["search_results"] = search_results
                            data["library"]["has_content"] = any(search_results.values())
                    else:
                        # MusicBrainz no disponible, usar solo resultados locales
                        data["library"]["search_results"] = search_results
                        data["library"]["has_content"] = any(search_results.values())
                
                # Si hay un artista específico, buscar por artista
                elif search_term:
                    print(f"🔍 Buscando en biblioteca por ARTISTA: '{search_term}' (query: '{query}')")
                    
                    # Generar variaciones del término para búsqueda más flexible
                    # Ej: "kaseo" → ["kaseo", "kase.o", "kase o", "kase. o"]
                    search_variations = self._generate_search_variations(search_term)
                    print(f"🔍 DEBUG - Variaciones de búsqueda: {search_variations}")
                    
                    # Buscar con todas las variaciones y combinar resultados
                    combined_results = {"tracks": [], "albums": [], "artists": []}
                    for variation in search_variations:
                        variation_results = await self.navidrome.search(variation, limit=20)
                        # Combinar resultados evitando duplicados
                        for result_type in ["tracks", "albums", "artists"]:
                            existing_ids = {item.id for item in combined_results[result_type]}
                            for item in variation_results.get(result_type, []):
                                if item.id not in existing_ids:
                                    combined_results[result_type].append(item)
                                    existing_ids.add(item.id)
                    
                    search_results = combined_results
                    
                    # DEBUG: Mostrar resultados crudos antes del filtro
                    print(f"🔍 DEBUG - Resultados ANTES del filtro:")
                    print(f"   Tracks: {len(search_results.get('tracks', []))}")
                    print(f"   Albums: {len(search_results.get('albums', []))}")
                    if search_results.get('albums'):
                        for album in search_results.get('albums', [])[:3]:
                            print(f"     - {album.artist} - {album.name}")
                    print(f"   Artists: {len(search_results.get('artists', []))}")
                    
                    # FILTRAR resultados para mantener solo los que realmente coincidan
                    filtered_results = self._filter_relevant_results(search_results, search_term)
                    
                    # DEBUG: Mostrar resultados después del filtro
                    print(f"🔍 DEBUG - Resultados DESPUÉS del filtro:")
                    print(f"   Tracks: {len(filtered_results.get('tracks', []))}")
                    print(f"   Albums: {len(filtered_results.get('albums', []))}")
                    if filtered_results.get('albums'):
                        for album in filtered_results.get('albums', [])[:3]:
                            print(f"     - {album.artist} - {album.name}")
                    print(f"   Artists: {len(filtered_results.get('artists', []))}")
                    
                    data["library"]["search_results"] = filtered_results
                    data["library"]["search_term"] = search_term
                    data["library"]["is_genre_search"] = False
                    
                    if any(filtered_results.values()):
                        data["library"]["has_content"] = True
                        print(f"✅ Encontrado: {len(filtered_results.get('tracks', []))} tracks, {len(filtered_results.get('albums', []))} álbumes, {len(filtered_results.get('artists', []))} artistas")
                    else:
                        data["library"]["has_content"] = False
                        print(f"⚠️ No se encontraron resultados para '{search_term}'")
                    
            except Exception as e:
                print(f"⚠️ Error obteniendo datos de Navidrome: {e}")
                data["library"]["error"] = str(e)
        
        # Datos de escucha (ListenBrainz)
        if needs_listening_history:
            try:
                print(f"📊 Obteniendo historial de escucha...")
                
                # OPTIMIZACIÓN: Paralelizar todas las llamadas
                tasks = []
                task_names = []
                
                # Recent tracks (siempre)
                if self.listenbrainz:
                    tasks.append(self.listenbrainz.get_recent_tracks(limit=20))
                    task_names.append("recent_tracks")
                
                # Top artists (siempre)
                if self.listenbrainz:
                    tasks.append(self.listenbrainz.get_top_artists(limit=10))
                    task_names.append("top_artists")
                
                # Top tracks (solo si se necesita)
                if "canción" in query_lower or "track" in query_lower or "tema" in query_lower:
                    if self.listenbrainz:
                        tasks.append(self.listenbrainz.get_top_tracks(limit=10))
                        task_names.append("top_tracks")
                
                # Stats (solo si se necesita)
                if "estadística" in query_lower or "stats" in query_lower or "cuánto" in query_lower:
                    if self.listenbrainz and hasattr(self.listenbrainz, 'get_user_stats'):
                        tasks.append(self.listenbrainz.get_user_stats())
                        task_names.append("stats")
                
                # Ejecutar todas las tareas en paralelo
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar resultados
                for i, result in enumerate(results):
                    if not isinstance(result, Exception) and result:
                        data["listening_history"][task_names[i]] = result
                    else:
                        data["listening_history"][task_names[i]] = [] if task_names[i] != "stats" else {}
                
                service_used = "ListenBrainz" if self.listenbrainz and data["listening_history"].get("recent_tracks") else "Ninguno"
                print(f"✅ Historial obtenido desde: {service_used}")
                
            except Exception as e:
                print(f"⚠️ Error obteniendo historial de escucha: {e}")
                data["listening_history"]["error"] = str(e)
        
        # Búsqueda de contenido similar (ListenBrainz CF)
        if self.discovery_service and ("similar" in query_lower or "parecido" in query_lower or "como" in query_lower):
            try:
                print(f"🔍 Buscando contenido similar en ListenBrainz")
                # Extraer nombre de artista/álbum de la query
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() in ["similar", "parecido", "como"] and i + 1 < len(words):
                        potential_artist = " ".join(words[i+1:])
                        similar_artists = await self.discovery_service.get_similar_artists_from_recording(
                            potential_artist, 
                            limit=5,
                            musicbrainz_service=self.musicbrainz
                        )
                        if similar_artists:
                            data["similar_content"] = similar_artists
                        break
            except Exception as e:
                print(f"⚠️ Error buscando contenido similar: {e}")
        
        # Buscar información de MusicBrainz sobre artistas específicos cuando preguntan por "mejor disco/álbum"
        if self.musicbrainz and needs_library_search and search_term and any(word in query_lower for word in ["mejor", "recomend"]):
            try:
                print(f"🌍 Buscando información en MusicBrainz para '{search_term}'...")
                # Obtener top álbumes del artista desde MusicBrainz
                top_albums = await self.musicbrainz.get_artist_top_albums(search_term, limit=10)
                if top_albums:
                    data["musicbrainz_artist_info"] = {
                        "artist": search_term,
                        "top_albums": top_albums
                    }
                    print(f"✅ Encontrados {len(top_albums)} álbumes de '{search_term}' en MusicBrainz")
            except Exception as e:
                print(f"⚠️ Error obteniendo info de MusicBrainz para '{search_term}': {e}")
        
        # Buscar lanzamientos recientes cuando lo pidan
        if needs_recent_releases:
            try:
                print(f"🆕 Buscando lanzamientos recientes...")
                
                # Obtener artistas de la biblioteca (TODOS para lanzamientos recientes)
                library_artists = []
                if self.navidrome:
                    artists = await self.navidrome.get_all_artists()
                    library_artists = [artist.name for artist in artists if artist.name]
                
                if library_artists and self.musicbrainz:
                    print(f"   📚 Artistas en biblioteca: {len(library_artists)}")
                    
                    # Buscar lanzamientos recientes de artistas de la biblioteca
                    recent_releases = await self.musicbrainz.get_recent_releases_for_artists(
                        library_artists, 
                        days=30  # Últimos 30 días
                    )
                    
                    if recent_releases:
                        data["recent_releases"] = recent_releases[:10]  # Máximo 10
                        print(f"✅ Encontrados {len(recent_releases)} lanzamientos recientes")
                    else:
                        print("⚠️ No se encontraron lanzamientos recientes")
                        data["recent_releases"] = []
                else:
                    print("⚠️ No hay artistas en biblioteca o MusicBrainz no disponible")
                    data["recent_releases"] = []
                
            except Exception as e:
                print(f"⚠️ Error buscando lanzamientos recientes: {e}")
                data["recent_releases"] = []
        
        # Buscar música nueva activamente cuando lo pidan
        if needs_new_music:
            try:
                print(f"🌍 Buscando música NUEVA basada en gustos del usuario...")
                
                # Obtener top artistas del historial
                top_artists = []
                if self.listenbrainz:
                    top_artists = await self.listenbrainz.get_top_artists(limit=5)
                
                # Buscar artistas similares usando ListenBrainz para descubrimiento
                if top_artists and self.discovery_service:
                    # OPTIMIZACIÓN: Paralelizar búsqueda de artistas similares
                    similar_tasks = []
                    for top_artist in top_artists[:3]:  # Solo los top 3
                        similar_tasks.append(
                            self.discovery_service.get_similar_artists_from_recording(
                                top_artist.name, 
                                limit=3,
                                musicbrainz_service=self.musicbrainz
                            )
                        )
                    
                    # Ejecutar búsquedas en paralelo
                    similar_results = await asyncio.gather(*similar_tasks, return_exceptions=True)
                    
                    # Procesar resultados
                    new_discoveries = []
                    for i, similar_artists in enumerate(similar_results):
                        if isinstance(similar_artists, Exception):
                            print(f"⚠️ Error obteniendo similares: {similar_artists}")
                            continue
                        
                        top_artist = top_artists[i]
                        
                        # OPTIMIZACIÓN: Paralelizar obtención de álbumes top
                        album_tasks = []
                        valid_artists = []
                        for artist in similar_artists:
                            if artist.name not in [d.get('artist') for d in new_discoveries]:
                                valid_artists.append(artist)
                                album_tasks.append(
                                    self.discovery_service.get_artist_top_albums(artist.name, limit=1)
                                )
                            
                            if len(valid_artists) >= 3:  # Máximo 3 por top artist
                                break
                        
                        # Obtener álbumes en paralelo
                        if album_tasks:
                            album_results = await asyncio.gather(*album_tasks, return_exceptions=True)
                            
                            for j, top_albums in enumerate(album_results):
                                if not isinstance(top_albums, Exception) and j < len(valid_artists):
                                    artist = valid_artists[j]
                                    discovery = {
                                        'artist': artist.name,
                                        'url': artist.url if hasattr(artist, 'url') else None,
                                        'top_album': top_albums[0].get('name') if top_albums else None,
                                        'album_url': top_albums[0].get('url') if top_albums else None,
                                        'similar_to': top_artist.name
                                    }
                                    new_discoveries.append(discovery)
                                    
                                    if len(new_discoveries) >= 8:
                                        break
                        
                        if len(new_discoveries) >= 8:
                            break
                    
                    if new_discoveries:
                        data["new_discoveries"] = new_discoveries[:8]
                        print(f"✅ Encontrados {len(data['new_discoveries'])} descubrimientos con álbums específicos")
                
            except Exception as e:
                print(f"⚠️ Error buscando música nueva: {e}")
        
        return data
    
    def _format_context_for_ai(self, data: Dict[str, Any]) -> str:
        """Formatear contexto para que la IA lo entienda
        
        Args:
            data: Diccionario con todos los datos recopilados
            
        Returns:
            String formateado con toda la información para la IA
        """
        formatted = ""
        
        # Reproducción actual (si se preguntó por ello)
        if data.get("now_playing") is not None:
            formatted += f"\n🎵 === REPRODUCCIÓN ACTUAL ===\n"
            now_playing = data["now_playing"]
            if now_playing:
                formatted += f"✅ Hay {len(now_playing)} reproducción(es) activa(s):\n\n"
                for i, entry in enumerate(now_playing, 1):
                    formatted += f"  {i}. {entry['artist']} - {entry['track']}"
                    if entry.get('album'):
                        formatted += f" (de {entry['album']})"
                    formatted += f"\n     👤 Usuario: {entry['username']}"
                    formatted += f" | 🎧 Reproductor: {entry['player_name']}"
                    if entry.get('minutes_ago') == 0:
                        formatted += f" | ▶️ Reproduciendo ahora mismo"
                    elif entry.get('minutes_ago'):
                        formatted += f" | ⏱️ Comenzó hace {entry['minutes_ago']} minuto(s)"
                    if entry.get('duration'):
                        mins = entry['duration'] // 60
                        secs = entry['duration'] % 60
                        formatted += f" | ⏳ Duración: {mins}:{secs:02d}"
                    formatted += "\n"
                formatted += "\n"
            else:
                formatted += "  ⚠️ No hay nada reproduciéndose en este momento\n"
                formatted += "  💡 Asegúrate de tener reproductores conectados y activos en Navidrome\n\n"
        
        # SIEMPRE mostrar primero la biblioteca (si hay búsqueda o datos completos)
        if data.get("library"):
            lib = data["library"]
            search_term = lib.get("search_term", "")
            is_genre_search = lib.get("is_genre_search", False)
            detected_genre = lib.get("detected_genre", "")
            
            # Si hay datos completos de biblioteca (consultas informativas)
            if lib.get("complete_data"):
                complete_data = lib["complete_data"]
                formatted += f"\n📚 === BIBLIOTECA COMPLETA ===\n"
                formatted += f"📊 <b>ESTADÍSTICAS GENERALES:</b>\n"
                formatted += f"• <b>Total de artistas:</b> {complete_data['total_artists']}\n"
                formatted += f"• <b>Total de álbumes:</b> {complete_data['total_albums']}\n"
                formatted += f"• <b>Total de canciones:</b> {complete_data['total_tracks']}\n"
                formatted += f"• <b>Total de géneros:</b> {complete_data['total_genres']}\n\n"
                
                # Mostrar géneros únicos
                if complete_data.get("genres"):
                    formatted += f"🎸 <b>GÉNEROS EN TU BIBLIOTECA ({complete_data['total_genres']}):</b>\n"
                    for i, genre in enumerate(complete_data["genres"][:20], 1):  # Mostrar primeros 20
                        formatted += f"  {i}. {genre}\n"
                    if complete_data['total_genres'] > 20:
                        formatted += f"  ... y {complete_data['total_genres'] - 20} géneros más\n"
                    formatted += "\n"
                
                # Mostrar artistas únicos (primeros 30)
                if complete_data.get("unique_artists"):
                    formatted += f"🎤 <b>ARTISTAS EN TU BIBLIOTECA ({complete_data['unique_artists_count']}):</b>\n"
                    for i, artist in enumerate(complete_data["unique_artists"][:30], 1):  # Mostrar primeros 30
                        formatted += f"  {i}. {artist}\n"
                    if complete_data['unique_artists_count'] > 30:
                        formatted += f"  ... y {complete_data['unique_artists_count'] - 30} artistas más\n"
                    formatted += "\n"
                
                # Si hay una consulta de género, proporcionar información para análisis inteligente
                if complete_data.get("genre_query"):
                    genre_query = complete_data["genre_query"]
                    requested_genre = genre_query["requested_genre"]
                    
                    formatted += f"\n🎸 <b>CONSULTA DE GÉNERO: {requested_genre.upper()}</b>\n"
                    formatted += f"💡 <b>INSTRUCCIONES PARA LA IA:</b>\n"
                    formatted += f"• El usuario pregunta por música de género '{requested_genre}'\n"
                    formatted += f"• Analiza TODA la biblioteca ({genre_query['total_artists']} artistas, {genre_query['total_albums']} álbumes, {genre_query['total_tracks']} canciones)\n"
                    formatted += f"• Busca artistas que puedan estar relacionados con '{requested_genre}' aunque no estén etiquetados exactamente así\n"
                    formatted += f"• Considera variaciones, subgéneros, estilos relacionados y artistas similares\n"
                    formatted += f"• Usa tu conocimiento musical para identificar conexiones\n\n"
                    
                    # Proporcionar muestra de artistas para que la IA analice
                    if complete_data.get("unique_artists"):
                        formatted += f"🎤 <b>MUESTRA DE ARTISTAS PARA ANÁLISIS (primeros 50):</b>\n"
                        for i, artist in enumerate(complete_data["unique_artists"][:50], 1):
                            formatted += f"  {i}. {artist}\n"
                        if complete_data['unique_artists_count'] > 50:
                            formatted += f"  ... y {complete_data['unique_artists_count'] - 50} artistas más para analizar\n"
                        formatted += "\n"
                    
                    # Proporcionar muestra de géneros para contexto
                    if complete_data.get("genres"):
                        formatted += f"🎵 <b>GÉNEROS DISPONIBLES EN LA BIBLIOTECA:</b>\n"
                        for i, genre in enumerate(complete_data["genres"][:30], 1):
                            formatted += f"  {i}. {genre}\n"
                        if complete_data['total_genres'] > 30:
                            formatted += f"  ... y {complete_data['total_genres'] - 30} géneros más\n"
                        formatted += "\n"
                
                # Si hay datos filtrados por artista, mostrarlos
                if complete_data.get("filtered_by_artist"):
                    filtered = complete_data["filtered_by_artist"]
                    formatted += f"\n🎤 <b>FILTRADO POR ARTISTA: {filtered['artist'].upper()}</b>\n"
                    formatted += f"📊 <b>ESTADÍSTICAS DE {filtered['artist'].upper()}:</b>\n"
                    formatted += f"• <b>Artistas coincidentes:</b> {filtered['total_matching_artists']}\n"
                    formatted += f"• <b>Álbumes:</b> {filtered['total_albums']}\n"
                    formatted += f"• <b>Canciones:</b> {filtered['total_tracks']}\n\n"
                    
                    # Mostrar artistas coincidentes
                    if filtered.get("matching_artists"):
                        formatted += f"🎤 <b>ARTISTAS COINCIDENTES:</b>\n"
                        for i, artist in enumerate(filtered["matching_artists"][:10], 1):
                            formatted += f"  {i}. {artist.name}"
                            if artist.album_count:
                                formatted += f" ({artist.album_count} álbumes)"
                            formatted += "\n"
                        if filtered['total_matching_artists'] > 10:
                            formatted += f"  ... y {filtered['total_matching_artists'] - 10} artistas más\n"
                        formatted += "\n"
                    
                    # Mostrar álbumes del artista
                    if filtered.get("albums"):
                        formatted += f"📀 <b>ÁLBUMES DE {filtered['artist'].upper()}:</b>\n"
                        for i, album in enumerate(filtered["albums"][:15], 1):
                            formatted += f"  {i}. {album.name}"
                            if album.year:
                                formatted += f" ({album.year})"
                            formatted += "\n"
                        if filtered['total_albums'] > 15:
                            formatted += f"  ... y {filtered['total_albums'] - 15} álbumes más\n"
                        formatted += "\n"
                
                formatted += f"💡 <b>NOTA:</b> Esta es información completa de toda tu biblioteca musical\n\n"
            
            if lib.get("search_results"):
                results = lib["search_results"]
                
                # Si es búsqueda por género, indicarlo claramente
                if is_genre_search:
                    formatted += f"\n📚 === BIBLIOTECA LOCAL - BÚSQUEDA POR GÉNERO ===\n"
                    formatted += f"🎸 GÉNERO DETECTADO: {detected_genre.upper()}\n"
                    formatted += f"💡 El usuario pide RECOMENDACIÓN de {detected_genre} de su biblioteca\n\n"
                
                # Priorizar álbumes si existen
                if results.get("albums"):
                    if not is_genre_search:
                        formatted += f"\n📚 === BIBLIOTECA LOCAL === \n"
                        formatted += f"📀 ÁLBUMES ENCONTRADOS PARA '{search_term.upper()}' ({len(results['albums'])}):\n"
                        formatted += f"⚠️ IMPORTANTE: Verifica que el ARTISTA coincida con lo solicitado\n\n"
                    else:
                        formatted += f"📀 ÁLBUMES DE {detected_genre.upper()} EN BIBLIOTECA ({len(results['albums'])}):\n"
                        formatted += f"💡 Recomienda UNO O VARIOS de estos según el gusto del usuario\n\n"
                    
                    for i, album in enumerate(results["albums"][:20], 1):
                        formatted += f"  {i}. {album.artist} - {album.name}"
                        if album.year:
                            formatted += f" ({album.year})"
                        if album.track_count:
                            formatted += f" [{album.track_count} canciones]"
                        formatted += "\n"
                    formatted += "\n"
                
                # Luego artistas
                if results.get("artists"):
                    if not results.get("albums"):  # Solo mostrar si no hay álbumes
                        formatted += f"\n📚 === BIBLIOTECA LOCAL === \n"
                    formatted += f"🎤 ARTISTAS ENCONTRADOS EN BIBLIOTECA ({len(results['artists'])}):\n"
                    formatted += f"⚠️ Verifica que el nombre coincida con lo que pidió el usuario\n\n"
                    for i, artist in enumerate(results["artists"][:10], 1):
                        formatted += f"  {i}. ARTISTA: {artist.name}"
                        if artist.album_count:
                            formatted += f" | {artist.album_count} álbumes disponibles"
                        formatted += "\n"
                    formatted += "\n"
                
                # Luego canciones
                if results.get("tracks"):
                    if not results.get("albums") and not results.get("artists"):
                        formatted += f"\n📚 === BIBLIOTECA LOCAL === \n"
                    formatted += f"🎵 CANCIONES ENCONTRADAS EN BIBLIOTECA ({len(results['tracks'])}):\n"
                    formatted += f"⚠️ Verifica que el ARTISTA coincida\n\n"
                    for i, track in enumerate(results["tracks"][:10], 1):
                        formatted += f"  {i}. ARTISTA: {track.artist} | CANCIÓN: {track.title}"
                        if track.album:
                            formatted += f" | ÁLBUM: {track.album}"
                        if track.year:
                            formatted += f" [{track.year}]"
                        formatted += "\n"
                    formatted += "\n"
            
            # Si no se encontró nada, indicarlo claramente
            if lib.get("has_content") == False:
                formatted += f"\n📚 === BIBLIOTECA LOCAL === \n"
                formatted += f"⚠️ NO TIENES '{search_term.upper()}' EN TU BIBLIOTECA\n\n"
        
        # Historial de escucha (ListenBrainz) - SOLO SI ES RELEVANTE
        if data.get("listening_history"):
            hist = data["listening_history"]
            
            # ESCUCHAS RECIENTES (orden cronológico) - CRÍTICO para consultas de "últimos"
            if hist.get("recent_tracks"):
                recent = hist["recent_tracks"]
                formatted += f"\n🕐 === HISTORIAL RECIENTE (orden cronológico, MÁS RECIENTE PRIMERO) ===\n"
                formatted += f"⚠️ IMPORTANTE: Usa ESTOS datos cuando pregunten por 'últimos/recientes' escuchados\n\n"
                
                # Mostrar últimas escuchas
                formatted += f"📝 ÚLTIMAS ESCUCHAS:\n"
                for i, track in enumerate(recent[:15], 1):
                    formatted += f"  {i}. {track.artist} - {track.name}"
                    if track.date:
                        formatted += f" (escuchado: {track.date.strftime('%Y-%m-%d %H:%M')})"
                    formatted += "\n"
                
                # Extraer artistas únicos en orden cronológico
                from collections import OrderedDict
                unique_artists = OrderedDict()
                for track in recent:
                    if track.artist and track.artist not in unique_artists:
                        unique_artists[track.artist] = True
                
                if unique_artists:
                    formatted += f"\n🎤 ÚLTIMOS ARTISTAS ÚNICOS (en orden cronológico):\n"
                    for i, artist in enumerate(list(unique_artists.keys())[:10], 1):
                        formatted += f"  {i}. {artist}\n"
                
                formatted += f"\n💡 Si preguntan 'últimos 3/5/N artistas' → USA ESTA LISTA (no top artists)\n\n"
            
            # Estadísticas generales
            if hist.get("stats"):
                stats = hist["stats"]
                formatted += f"\n📊 === ESTADÍSTICAS GENERALES ===\n"
                formatted += f"  • Total de escuchas: {stats.get('total_listens', 'N/A')}\n"
                formatted += f"  • Artistas únicos: {stats.get('total_artists', 'N/A')}\n"
                formatted += f"  • Álbumes únicos: {stats.get('total_albums', 'N/A')}\n"
                formatted += f"  • Canciones únicas: {stats.get('total_tracks', 'N/A')}\n\n"
            
            # Top artists (por cantidad, NO por cronología)
            if hist.get("top_artists"):
                formatted += f"\n🏆 TUS TOP ARTISTAS MÁS ESCUCHADOS (por cantidad total):\n"
                formatted += f"⚠️ NOTA: Estos son los MÁS ESCUCHADOS, NO los más recientes\n"
                for i, artist in enumerate(hist["top_artists"][:5], 1):
                    formatted += f"  {i}. {artist.name}"
                    if artist.playcount:
                        formatted += f" ({artist.playcount} escuchas)"
                    formatted += "\n"
                formatted += "\n"
        
        # Información de MusicBrainz sobre artista específico
        if data.get("musicbrainz_artist_info"):
            info = data["musicbrainz_artist_info"]
            formatted += f"\n🌍 === INFORMACIÓN DE MUSICBRAINZ: {info['artist'].upper()} ===\n"
            formatted += f"📊 TOP ÁLBUMES MÁS POPULARES (según MusicBrainz):\n\n"
            for i, album in enumerate(info["top_albums"][:10], 1):
                # Puede ser dict o objeto
                if isinstance(album, dict):
                    album_name = album.get('name', 'Unknown')
                    playcount = album.get('playcount', 0)
                    url = album.get('url', '')
                else:
                    album_name = getattr(album, 'name', 'Unknown')
                    playcount = getattr(album, 'playcount', 0)
                    url = getattr(album, 'url', '')
                
                formatted += f"  {i}. {album_name}"
                if playcount:
                    formatted += f" - {playcount:,} escuchas globales"
                if url:
                    formatted += f" | {url}"
                formatted += "\n"
            formatted += "\n💡 IMPORTANTE: Usa esta info para recomendar el mejor álbum\n"
            formatted += f"💡 Combina lo que tiene en biblioteca + información de MusicBrainz\n\n"
        
        # Contenido similar
        if data.get("similar_content"):
            formatted += f"\n🔗 ARTISTAS SIMILARES:\n"
            for i, artist in enumerate(data["similar_content"][:5], 1):
                url_info = f" - {artist.url}" if hasattr(artist, 'url') and artist.url else ""
                formatted += f"  {i}. {artist.name}{url_info}\n"
        
        # LANZAMIENTOS RECIENTES (música nueva de artistas de la biblioteca)
        if data.get("recent_releases"):
            formatted += f"\n🆕 === LANZAMIENTOS RECIENTES DE TUS ARTISTAS ===\n"
            formatted += f"📅 Últimos 30 días - Música nueva de artistas en tu biblioteca\n\n"
            
            for i, release in enumerate(data["recent_releases"][:10], 1):
                title = release.get('title', 'Unknown')
                artist = release.get('artist', 'Unknown')
                date = release.get('date', '')
                release_type = release.get('type', 'album')
                url = release.get('url', '')
                
                formatted += f"  {i}. **{title}** - {artist}"
                if date:
                    formatted += f" ({date})"
                if release_type:
                    formatted += f" [{release_type}]"
                if url:
                    formatted += f" - {url}"
                formatted += "\n"
            
            formatted += "\n💡 Estos son lanzamientos recientes de artistas que ya tienes en tu biblioteca\n"
        
        # NUEVO: Descubrimientos (música que NO está en biblioteca pero puede recomendar)
        if data.get("new_discoveries"):
            formatted += f"\n🌍 === MÚSICA NUEVA PARA DESCUBRIR (de ListenBrainz) ===\n"
            formatted += f"📌 IMPORTANTE: Estos NO están en tu biblioteca pero PUEDES recomendarlos\n"
            formatted += f"🎯 Basado en tus gustos, te pueden gustar:\n\n"
            
            for i, discovery in enumerate(data["new_discoveries"][:8], 1):
                # Puede ser dict (nuevo formato) o objeto (formato antiguo)
                if isinstance(discovery, dict):
                    artist = discovery.get('artist', 'Unknown')
                    album = discovery.get('top_album')
                    similar_to = discovery.get('similar_to', '')
                    url = discovery.get('url', '')
                    
                    formatted += f"  {i}. **{artist}**"
                    if album:
                        formatted += f" - Álbum recomendado: **{album}**"
                    if similar_to:
                        formatted += f" (similar a {similar_to})"
                    if url:
                        formatted += f" - {url}"
                    formatted += "\n"
                else:
                    # Formato antiguo (compatibilidad)
                    formatted += f"  {i}. {discovery.name}"
                    if hasattr(discovery, 'url') and discovery.url:
                        formatted += f" - {discovery.url}"
                    formatted += "\n"
            
            formatted += "\n💡 Recomienda estos álbumes/artistas libremente - son descubrimientos basados en sus gustos\n"
        
        # Si no hay datos
        if not formatted:
            formatted = "\n⚠️ No hay datos disponibles para responder esta consulta.\n"
        
        # Información sobre búsqueda incremental disponible
        if data.get("library", {}).get("can_search_more"):
            stats = data["library"]["mb_stats"]
            formatted += f"\n💡 === BÚSQUEDA INCREMENTAL DISPONIBLE ===\n"
            formatted += f"✓ Verificados hasta ahora: {stats['checked']}/{stats['total']} artistas\n"
            formatted += f"✓ Quedan por verificar: {stats['remaining']} artistas\n"
            formatted += f"\n💬 IMPORTANTE: Menciona al usuario que puede decir 'busca más' para verificar más artistas.\n"
            formatted += f"Ejemplo: 'He verificado {stats['checked']} artistas de tu biblioteca. Si quieres que busque más a fondo, dime \"busca más\".'\n\n"
        
        return formatted
    
    def _extract_links(self, data: Dict[str, Any]) -> List[str]:
        """Extraer todos los enlaces relevantes del contexto
        
        Args:
            data: Diccionario con todos los datos
            
        Returns:
            Lista de URLs únicas de MusicBrainz/ListenBrainz
        """
        links = []
        
        # Enlaces del historial de escucha
        if hist := data.get("listening_history"):
            # De tracks recientes
            for track in hist.get("recent_tracks", []):
                if hasattr(track, 'url') and track.url:
                    links.append(track.url)
            
            # De top artistas
            for artist in hist.get("top_artists", []):
                if hasattr(artist, 'url') and artist.url:
                    links.append(artist.url)
            
            # De top tracks
            for track in hist.get("top_tracks", []):
                if hasattr(track, 'url') and track.url:
                    links.append(track.url)
        
        # Enlaces de contenido similar
        for item in data.get("similar_content", []):
            if hasattr(item, 'url') and item.url:
                links.append(item.url)
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links
    
    async def get_artist_info(self, artist_name: str) -> Dict[str, Any]:
        """Obtener información completa sobre un artista
        
        Args:
            artist_name: Nombre del artista
            
        Returns:
            Diccionario con información del artista
        """
        info = {
            "name": artist_name,
            "in_library": False,
            "listening_stats": {},
            "similar_artists": [],
            "top_albums": [],
            "top_tracks": []
        }
        
        # Buscar en biblioteca
        try:
            library_results = await self.navidrome.search(artist_name, limit=5)
            if library_results.get("artists"):
                info["in_library"] = True
                info["library_albums"] = library_results.get("albums", [])
                info["library_tracks"] = library_results.get("tracks", [])
        except Exception as e:
            print(f"Error buscando en biblioteca: {e}")
        
        # Información de descubrimiento (ListenBrainz + MusicBrainz)
        if self.discovery_service:
            try:
                # Artistas similares usando ListenBrainz CF o MusicBrainz
                info["similar_artists"] = await self.discovery_service.get_similar_artists_from_recording(
                    artist_name, 
                    limit=5,
                    musicbrainz_service=self.musicbrainz
                )
            except Exception as e:
                print(f"Error obteniendo artistas similares: {e}")
        
        # Información de MusicBrainz
        if self.musicbrainz:
            try:
                # Top álbumes
                info["top_albums"] = await self.musicbrainz.get_artist_top_albums(artist_name, limit=5)
                
                # Top tracks  
                info["top_tracks"] = await self.musicbrainz.get_artist_top_tracks(artist_name, limit=5)
            except Exception as e:
                print(f"Error obteniendo info de MusicBrainz: {e}")
        
        return info
    
    def _filter_relevant_results(self, results: Dict[str, List], search_term: str) -> Dict[str, List]:
        """Filtrar resultados de búsqueda para mantener solo los relevantes
        
        Elimina resultados que claramente NO coincidan con el artista buscado.
        Ej: Si buscas "Tobogán Andaluz", elimina "El Perro Andaluz"
        
        Args:
            results: Resultados de búsqueda de Navidrome
            search_term: Término que el usuario buscó
            
        Returns:
            Resultados filtrados
        """
        from difflib import SequenceMatcher
        import unicodedata
        
        def normalize_text(text: str) -> str:
            """Normalizar texto: eliminar tildes/acentos, puntuación y convertir a minúsculas
            
            Ejemplos:
                "Tobogán Andaluz" -> "tobogan andaluz"
                "Kase.O" -> "kaseo"
                "El Mató a un Policía" -> "el mato a un policia"
            """
            import re
            # Normalizar caracteres Unicode (NFD separa base + diacríticos)
            nfd = unicodedata.normalize('NFD', text)
            # Eliminar diacríticos (categoría 'Mn' = Nonspacing Mark)
            without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
            # Convertir a minúsculas
            lowercased = without_accents.lower()
            # Eliminar puntuación (excepto espacios)
            # Mantener letras, números y espacios; eliminar puntos, comas, guiones, etc.
            no_punctuation = re.sub(r'[^\w\s]', '', lowercased)
            # Normalizar espacios múltiples a uno solo
            normalized_spaces = re.sub(r'\s+', ' ', no_punctuation).strip()
            return normalized_spaces
        
        def similarity_ratio(a: str, b: str) -> float:
            """Calcular similitud entre dos strings (normalizados)"""
            return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()
        
        # Umbral de similitud (0.6 = 60% similar)
        SIMILARITY_THRESHOLD = 0.6
        
        filtered = {
            "tracks": [],
            "albums": [],
            "artists": []
        }
        
        # Normalizar el término de búsqueda
        search_normalized = normalize_text(search_term)
        # También crear versión sin espacios para comparaciones (ej: "kase o" -> "kaseo")
        search_no_spaces = search_normalized.replace(' ', '')
        
        # Filtrar álbumes
        for album in results.get("albums", []):
            artist_similarity = similarity_ratio(album.artist, search_term)
            album_similarity = similarity_ratio(album.name, search_term)
            artist_normalized = normalize_text(album.artist)
            artist_no_spaces = artist_normalized.replace(' ', '')
            album_normalized = normalize_text(album.name)
            
            # MEJORADO: Mantener si (con normalización de texto):
            # 1. El término de búsqueda está CONTENIDO en el nombre del artista
            # 2. El término sin espacios coincide con el artista sin espacios (ej: "kase o" = "kaseo")
            # 3. El artista es similar al término de búsqueda (60%+)
            # 4. El álbum contiene el término de búsqueda
            if (search_normalized in artist_normalized or 
                search_no_spaces == artist_no_spaces or
                artist_normalized.startswith(search_normalized) or
                artist_similarity >= SIMILARITY_THRESHOLD or 
                search_normalized in album_normalized):
                filtered["albums"].append(album)
                print(f"   ✓ Álbum mantenido: {album.artist} - {album.name} (similitud: {artist_similarity:.2f})")
            else:
                print(f"   ✗ Álbum filtrado: {album.artist} - {album.name} (similitud: {artist_similarity:.2f})")
        
        # Filtrar artistas
        for artist in results.get("artists", []):
            artist_similarity = similarity_ratio(artist.name, search_term)
            artist_normalized = normalize_text(artist.name)
            artist_no_spaces = artist_normalized.replace(' ', '')
            
            # MEJORADO: Mantener si el término está contenido, sin espacios coincide, o es similar
            if (search_normalized in artist_normalized or
                search_no_spaces == artist_no_spaces or
                artist_normalized.startswith(search_normalized) or
                artist_similarity >= SIMILARITY_THRESHOLD):
                filtered["artists"].append(artist)
                print(f"   ✓ Artista mantenido: {artist.name} (similitud: {artist_similarity:.2f})")
            else:
                print(f"   ✗ Artista filtrado: {artist.name} (similitud: {artist_similarity:.2f})")
        
        # Filtrar canciones
        for track in results.get("tracks", []):
            artist_similarity = similarity_ratio(track.artist, search_term)
            artist_normalized = normalize_text(track.artist)
            artist_no_spaces = artist_normalized.replace(' ', '')
            
            # MEJORADO: Mantener si el término está contenido en el artista (normalizado)
            if (search_normalized in artist_normalized or
                search_no_spaces == artist_no_spaces or
                artist_normalized.startswith(search_normalized) or
                artist_similarity >= SIMILARITY_THRESHOLD):
                filtered["tracks"].append(track)
            else:
                print(f"   ✗ Canción filtrada: {track.artist} - {track.title}")
        
        return filtered
    
    def _generate_search_variations(self, search_term: str) -> List[str]:
        """Generar variaciones de un término de búsqueda para mayor flexibilidad
        
        Esto ayuda a encontrar artistas como "Kase.O" incluso si el usuario busca "kaseo" o "kase o"
        
        Args:
            search_term: Término de búsqueda original
            
        Returns:
            Lista de variaciones del término
            
        Ejemplos:
            "kaseo" → ["kaseo", "kase.o", "kase o", "kase. o"]
            "kase o" → ["kase o", "kaseo", "kase.o"]
            "el mato" → ["el mato", "elmato", "el.mato"]
        """
        variations = [search_term]  # Siempre incluir el original
        
        # Variación sin espacios
        no_spaces = search_term.replace(' ', '')
        if no_spaces != search_term and no_spaces not in variations:
            variations.append(no_spaces)
        
        # Variación con punto entre palabras (para artistas como "Kase.O")
        if ' ' in search_term:
            with_dot = search_term.replace(' ', '.')
            if with_dot not in variations:
                variations.append(with_dot)
            
            # También probar con punto y espacio
            with_dot_space = search_term.replace(' ', '. ')
            if with_dot_space not in variations:
                variations.append(with_dot_space)
        
        # Si no tiene espacios, probar agregando punto en diferentes posiciones
        # Especialmente útil para "kaseo" → "kase.o", "elmato" → "el.mato"
        if ' ' not in search_term and '.' not in search_term and len(search_term) > 3:
            # Probar punto antes de la última letra
            with_dot_last = search_term[:-1] + '.' + search_term[-1]
            if with_dot_last not in variations:
                variations.append(with_dot_last)
            
            # También probar con espacio antes de la última letra
            with_space_last = search_term[:-1] + ' ' + search_term[-1]
            if with_space_last not in variations:
                variations.append(with_space_last)
        
        print(f"🔍 Generadas {len(variations)} variaciones para '{search_term}'")
        return variations
    
    def _extract_artist_from_query(self, query: str) -> Optional[str]:
        """Extraer nombre de artista de consultas como 'que tengo de X'"""
        import re
        
        # Patrones para extraer artista
        patterns = [
            r'que tengo de (?:la |el |los |las )?([^?]+)',
            r'qué tengo de (?:la |el |los |las )?([^?]+)',
            r'tengo de (?:la |el |los |las )?([^?]+)',
            r'tienes de (?:la |el |los |las )?([^?]+)',
            r'de (?:la |el |los |las )?([^?]+) en mi biblioteca',
            r'de (?:la |el |los |las )?([^?]+) tengo'
        ]
        
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                artist_name = match.group(1).strip()
                # Limpiar caracteres extra
                artist_name = re.sub(r'[?¿!¡.,;:]', '', artist_name).strip()
                if artist_name and len(artist_name) > 1:
                    return artist_name
        
        return None

    def _extract_search_term(self, query: str) -> str:
        """Extraer el término de búsqueda real de una consulta en lenguaje natural
        
        Ejemplos:
            "¿Qué álbumes de Pink Floyd tengo?" -> "Pink Floyd"
            "Busca Queen en mi biblioteca" -> "Queen"
            "Tengo discos de The Beatles?" -> "The Beatles"
        
        Args:
            query: Consulta en lenguaje natural
            
        Returns:
            Término de búsqueda extraído
        """
        import re
        
        # Palabras a ignorar (stop words en español)
        stop_words = {
            'qué', 'que', 'cual', 'cuál', 'cuales', 'cuáles', 'cómo', 'como',
            'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'tengo', 'tienes', 'tiene', 'en', 'mi', 'tu', 'su',
            'biblioteca', 'colección', 'álbum', 'álbumes', 'album', 'albums',
            'disco', 'discos', 'canción', 'canciones', 'cancion',
            'artista', 'artistas', 'por', 'para', 'con', 'sin',
            'hay', 'está', 'esta', 'están', 'estan', 'son', 'es',
            'busca', 'buscar', 'encuentra', 'encontrar', 'dame', 'dime',
            'muestra', 'mostrar', 'ver', 'a', 'e', 'i', 'o', 'u', 'y',
            'mejor', 'peor'
        }
        
        # ESTRATEGIA 1: Buscar patrón "de [artista]" (MÁS CONFIABLE)
        # Esta estrategia debe ir PRIMERA porque es más específica y evita confusiones
        # Ejemplo: "Cual es el mejor disco de el mató?" → extrae "el mató"
        de_patterns = [
            # Patrón específico para "mejor/peor disco/álbum de X"
            r'(?:mejor|peor)\s+(?:disco|álbum|album)\s+de\s+(.+?)(?:\?|$)',
            # Patrón para "disco/álbum de X"
            r'(?:disco|álbum|album)\s+de\s+(.+?)(?:\?|$)',
            # Patrón general "de X" (cuando no hay palabras anteriores conflictivas)
            r'\bde\s+([a-záéíóúñ][a-záéíóúñ\s]+?)(?:\?|$)'
        ]
        
        for de_pattern in de_patterns:
            de_match = re.search(de_pattern, query, re.IGNORECASE)
            if de_match:
                result = de_match.group(1).strip()
                # Limpiar palabras comunes al final
                result = re.sub(r'\s+(tengo|teengo|en|mi|tu|biblioteca|es|son)$', '', result, flags=re.IGNORECASE)
                # Limpiar interrogantes y espacios
                result = result.rstrip('? ').strip()
                # Verificar que no sea solo stop words
                words = result.lower().split()
                if result and len(result) > 2 and not all(w in stop_words for w in words):
                    print(f"🔍 Término extraído (patrón 'de'): '{result}'")
                    return result
        
        # ESTRATEGIA 2: Buscar nombres propios (palabras con mayúsculas)
        # Pero filtrar palabras interrogativas comunes que podrían estar al inicio
        capitalized_pattern = r'\b([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+)*)\b'
        cap_matches = re.findall(capitalized_pattern, query)
        
        if cap_matches:
            # Filtrar palabras interrogativas aunque tengan mayúscula
            question_words = {'cual', 'cuál', 'qué', 'que', 'quién', 'quien', 'cómo', 'como', 'dónde', 'donde', 'cuándo', 'cuando'}
            filtered_matches = [m for m in cap_matches if m.lower() not in question_words and m.lower() not in stop_words]
            
            if filtered_matches:
                result = ' '.join(filtered_matches)
                print(f"🔍 Término extraído (mayúsculas filtradas): '{result}'")
                return result
        
        # ESTRATEGIA 3: Buscar después de palabras clave específicas
        keywords_patterns = [
            r'(?:discos?|álbumes?|albums?)\s+(?:de\s+)?([a-zA-Z][a-zA-Z\s]+?)(?:\s+tengo|\s+teengo|\?|$)',
            r'(?:tengo|teengo)\s+(?:de\s+)?([a-zA-Z][a-zA-Z\s]+?)(?:\s+en|\?|$)',
        ]
        
        for pattern in keywords_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                # Limpiar stop words
                result = re.sub(r'\s+(de|en|mi|tu|la|el|los|las)$', '', result, flags=re.IGNORECASE)
                if result and len(result) > 2:
                    print(f"🔍 Término extraído (keywords): '{result}'")
                    return result
        
        # Limpiar la query de signos de puntuación
        query_clean = re.sub(r'[¿?¡!.,;:]', '', query.lower())
        
        # Dividir en palabras
        words = query_clean.split()
        
        # Filtrar stop words
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Unir las palabras significativas
        result = ' '.join(meaningful_words)
        
        print(f"🔍 Término extraído (filtrado): '{result}'")
        return result if result else query
    
    async def _search_genre_with_musicbrainz(
        self, 
        genre: str, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """Usar MusicBrainz para buscar artistas de un género en la biblioteca
        
        Args:
            genre: Género musical a buscar
            offset: Desde qué artista empezar (para búsquedas incrementales)
            
        Returns:
            Diccionario con resultados y metadata de búsqueda
        """
        try:
            # OPTIMIZACIÓN: Reducir de 500 a 300 tracks para mejorar velocidad
            library_tracks = await self.navidrome.get_tracks(limit=300)
            
            # Extraer artistas únicos
            unique_artists = list(set([track.artist for track in library_tracks if track.artist]))
            print(f"      Total de artistas en biblioteca: {len(unique_artists)}")
            
            # Preparar filtros
            filters = {"genre": genre}
            
            # Verificar artistas usando batch size configurable
            mb_data = await self.musicbrainz.find_matching_artists_in_library(
                unique_artists,
                filters,
                max_artists=None,  # Usará MUSICBRAINZ_BATCH_SIZE
                offset=offset
            )
            
            if not mb_data or not mb_data.get("artists"):
                return {
                    "results": {"tracks": [], "albums": [], "artists": []},
                    "offset": mb_data.get("offset", offset) if mb_data else offset,
                    "next_offset": mb_data.get("next_offset", offset) if mb_data else offset,
                    "has_more": mb_data.get("has_more", False) if mb_data else False,
                    "total_artists": mb_data.get("total_artists", 0) if mb_data else 0,
                    "checked_this_batch": mb_data.get("checked_this_batch", 0) if mb_data else 0
                }
            
            # Extraer nombres de artistas que coinciden
            matching_artist_names = set([a["name"].lower() for a in mb_data["artists"]])
            print(f"      ✅ Artistas coincidentes: {list(matching_artist_names)}")
            
            # Buscar en Navidrome los artistas verificados
            results = {"tracks": [], "albums": [], "artists": []}
            
            for artist_name in list(matching_artist_names)[:10]:  # Limitar a 10 artistas
                artist_results = await self.navidrome.search(artist_name, limit=20)
                
                # Combinar resultados
                for track in artist_results.get("tracks", []):
                    if track not in results["tracks"]:
                        results["tracks"].append(track)
                
                for album in artist_results.get("albums", []):
                    if album not in results["albums"]:
                        results["albums"].append(album)
                
                for artist in artist_results.get("artists", []):
                    if artist not in results["artists"]:
                        results["artists"].append(artist)
            
            return {
                "results": results,
                "offset": mb_data["offset"],
                "next_offset": mb_data["next_offset"],
                "has_more": mb_data["has_more"],
                "total_artists": mb_data["total_artists"],
                "checked_this_batch": mb_data["checked_this_batch"]
            }
            
        except Exception as e:
            print(f"      ❌ Error en búsqueda MusicBrainz: {e}")
            return {
                "results": {"tracks": [], "albums": [], "artists": []},
                "offset": offset,
                "next_offset": offset,
                "has_more": False,
                "total_artists": 0,
                "checked_this_batch": 0
            }
    
    async def _get_minimal_context(self, user_id: int) -> Dict:
        """NIVEL 1: Contexto mínimo y rápido (SIEMPRE se ejecuta)
        
        Obtiene solo la información más básica con caché largo (1 hora).
        Esto hace que el agente siempre tenga una idea general de tu música.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Diccionario con contexto mínimo
        """
        cache_key = f"minimal_context_{user_id}"
        cached = self._get_cache(cache_key, ttl_seconds=3600)  # 1 hora
        
        if cached:
            print("⚡ Usando contexto mínimo en caché (1h)")
            return cached
        
        context = {}
        
        try:
            # Solo obtener top 3 artistas (muy rápido)
            if self.listenbrainz:
                top_artists = await self.listenbrainz.get_top_artists(limit=3)
                if top_artists:
                    context['top_artists'] = [a.name for a in top_artists]
                    print(f"✅ Contexto mínimo obtenido: {len(top_artists)} top artistas")
        except Exception as e:
            print(f"⚠️ Error obteniendo contexto mínimo: {e}")
        
        # Guardar en caché por 1 hora
        self._set_cache(cache_key, context, ttl_seconds=3600)
        return context
    
    async def _get_enriched_context(self, user_id: int, base_context: Dict) -> Dict:
        """NIVEL 2: Contexto enriquecido para recomendaciones
        
        Agrega información más detallada cuando se detectan palabras de recomendación.
        Usa caché de 10 minutos.
        
        Args:
            user_id: ID del usuario
            base_context: Contexto mínimo ya obtenido
            
        Returns:
            Diccionario con contexto enriquecido
        """
        cache_key = f"enriched_context_{user_id}"
        cached = self._get_cache(cache_key, ttl_seconds=600)  # 10 minutos
        
        if cached:
            print("⚡ Usando contexto enriquecido en caché (10min)")
            return {**base_context, **cached}
        
        enriched = dict(base_context)  # Copiar contexto base
        
        try:
            if self.listenbrainz:
                # Paralelizar obtención de datos
                tasks = []
                
                # Top 10 artistas (si no están en el base)
                if 'top_artists' not in enriched or len(enriched['top_artists']) < 10:
                    tasks.append(self.listenbrainz.get_top_artists(limit=10))
                else:
                    tasks.append(asyncio.sleep(0))
                
                # Últimas 5 escuchas
                tasks.append(self.listenbrainz.get_recent_tracks(limit=5))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar resultados
                if not isinstance(results[0], Exception) and results[0]:
                    enriched['top_artists'] = [a.name for a in results[0]]
                
                if len(results) > 1 and not isinstance(results[1], Exception) and results[1]:
                    enriched['last_track'] = f"{results[1][0].artist} - {results[1][0].name}"
                    enriched['recent_tracks'] = [
                        f"{t.artist} - {t.name}" for t in results[1][:5]
                    ]
                
                print(f"✅ Contexto enriquecido obtenido: {len(enriched.get('top_artists', []))} top artistas, {len(enriched.get('recent_tracks', []))} tracks recientes")
        except Exception as e:
            print(f"⚠️ Error obteniendo contexto enriquecido: {e}")
        
        # Guardar en caché por 10 minutos
        cache_data = {k: v for k, v in enriched.items() if k not in base_context}
        self._set_cache(cache_key, cache_data, ttl_seconds=600)
        
        return enriched
    
    async def _get_full_context(self, user_id: int, base_context: Dict) -> Dict:
        """NIVEL 3: Contexto completo para consultas de perfil
        
        Obtiene toda la información disponible cuando el usuario pregunta
        específicamente por su biblioteca o estadísticas.
        Usa caché de 5 minutos.
        
        Args:
            user_id: ID del usuario
            base_context: Contexto ya obtenido (mínimo o enriquecido)
            
        Returns:
            Diccionario con contexto completo
        """
        cache_key = f"full_context_{user_id}"
        cached = self._get_cache(cache_key, ttl_seconds=300)  # 5 minutos
        
        if cached:
            print("⚡ Usando contexto completo en caché (5min)")
            return {**base_context, **cached}
        
        full = dict(base_context)  # Copiar contexto base
        
        try:
            if self.listenbrainz:
                # Obtener estadísticas completas
                tasks = [
                    self.listenbrainz.get_top_artists(limit=15),
                    self.listenbrainz.get_recent_tracks(limit=20),
                ]
                
                # Si tiene método de estadísticas, agregarlo
                if hasattr(self.listenbrainz, 'get_user_stats'):
                    tasks.append(self.listenbrainz.get_user_stats())
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar top artists
                if not isinstance(results[0], Exception) and results[0]:
                    full['top_artists'] = [a.name for a in results[0]]
                    full['favorite_genres'] = list(set([
                        getattr(a, 'genre', None) for a in results[0] 
                        if getattr(a, 'genre', None)
                    ]))[:5]
                
                # Procesar tracks recientes
                if len(results) > 1 and not isinstance(results[1], Exception) and results[1]:
                    recent = results[1]
                    full['last_track'] = f"{recent[0].artist} - {recent[0].name}"
                    full['recent_tracks'] = [f"{t.artist} - {t.name}" for t in recent[:10]]
                    
                    # Extraer artistas únicos recientes
                    full['recent_artists'] = []
                    seen = set()
                    for t in recent:
                        if t.artist not in seen:
                            full['recent_artists'].append(t.artist)
                            seen.add(t.artist)
                
                # Procesar estadísticas (si existen)
                if len(results) > 2 and not isinstance(results[2], Exception) and results[2]:
                    full['stats'] = results[2]
                
                print(f"✅ Contexto completo obtenido: {len(full.get('top_artists', []))} top artistas, {len(full.get('recent_tracks', []))} tracks recientes")
        except Exception as e:
            print(f"⚠️ Error obteniendo contexto completo: {e}")
        
        # Guardar en caché por 5 minutos
        cache_data = {k: v for k, v in full.items() if k not in base_context}
        self._set_cache(cache_key, cache_data, ttl_seconds=300)
        
        return full
    
    async def _create_playlist_in_navidrome(
        self, 
        user_question: str, 
        data_context: Dict[str, Any], 
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Crear playlist en Navidrome basada en la consulta del usuario
        
        Args:
            user_question: Pregunta original del usuario
            data_context: Datos recopilados de la consulta
            user_id: ID del usuario
            
        Returns:
            Diccionario con información de la playlist creada o None si falla
        """
        try:
            print(f"🎵 Creando playlist en Navidrome para: {user_question}")
            
            # Extraer nombre de la playlist de la consulta
            playlist_name = self._extract_playlist_name(user_question)
            
            # Obtener canciones de los datos de contexto
            song_ids = await self._extract_song_ids_from_context(data_context)
            
            if not song_ids:
                print("⚠️ No se encontraron canciones para la playlist")
                return None
            
            # Limitar a 50 canciones máximo (límite de Navidrome)
            if len(song_ids) > 50:
                song_ids = song_ids[:50]
                print(f"⚠️ Limitando playlist a 50 canciones (tenías {len(song_ids)})")
            
            # Crear playlist en Navidrome
            playlist_id = await self.navidrome.create_playlist(playlist_name, song_ids)
            
            if playlist_id:
                print(f"✅ Playlist creada exitosamente: {playlist_name} (ID: {playlist_id})")
                return {
                    "id": playlist_id,
                    "name": playlist_name,
                    "track_count": len(song_ids),
                    "song_ids": song_ids
                }
            else:
                print("❌ No se pudo crear la playlist en Navidrome")
                return None
                
        except Exception as e:
            print(f"❌ Error creando playlist en Navidrome: {e}")
            return None
    
    def _extract_playlist_name(self, user_question: str) -> str:
        """Extraer nombre de playlist de la consulta del usuario
        
        Args:
            user_question: Consulta original del usuario
            
        Returns:
            Nombre de la playlist
        """
        import re
        
        # Patrones para extraer nombre de playlist
        patterns = [
            r'playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$',
            r'crea\s+(?:una\s+)?playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$',
            r'crear\s+(?:una\s+)?playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$',
            r'haz\s+(?:una\s+)?playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$',
            r'hacer\s+(?:una\s+)?playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$',
            r'genera\s+(?:una\s+)?playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$',
            r'generar\s+(?:una\s+)?playlist\s+(?:de\s+|con\s+|para\s+)?(.+?)(?:\s+\d+\s+canciones?)?$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_question.lower())
            if match:
                name = match.group(1).strip()
                # Limpiar caracteres extra
                name = re.sub(r'[?¿!¡.,;:]', '', name).strip()
                if name and len(name) > 2:
                    return name.title()
        
        # Fallback: usar parte de la consulta
        words = user_question.split()
        if len(words) > 2:
            # Tomar las últimas palabras como nombre
            return ' '.join(words[-3:]).title()
        
        return "Playlist Musicalo"
    
    async def _extract_song_ids_from_context(self, data_context: Dict[str, Any]) -> List[str]:
        """Extraer IDs de canciones de los datos de contexto
        
        Args:
            data_context: Datos recopilados de la consulta
            
        Returns:
            Lista de IDs de canciones
        """
        song_ids = []
        
        # Buscar en resultados de biblioteca
        if data_context.get("library", {}).get("search_results"):
            results = data_context["library"]["search_results"]
            
            # Priorizar tracks si están disponibles
            if results.get("tracks"):
                for track in results["tracks"]:
                    if hasattr(track, 'id') and track.id:
                        song_ids.append(track.id)
            
            # Si no hay tracks, buscar en álbumes y obtener sus tracks
            elif results.get("albums"):
                print(f"🎵 Obteniendo tracks de {len(results['albums'])} álbumes...")
                for album in results["albums"][:5]:  # Limitar a 5 álbumes para evitar demasiadas canciones
                    try:
                        album_tracks = await self.navidrome.get_album_tracks(album.id)
                        for track in album_tracks:
                            if hasattr(track, 'id') and track.id:
                                song_ids.append(track.id)
                    except Exception as e:
                        print(f"⚠️ Error obteniendo tracks del álbum {album.name}: {e}")
                        continue
        
        # Buscar en datos completos de biblioteca (solo si no hay resultados específicos)
        if not song_ids and data_context.get("library", {}).get("complete_data"):
            complete_data = data_context["library"]["complete_data"]
            
            # Si hay datos filtrados por artista
            if complete_data.get("filtered_by_artist"):
                filtered = complete_data["filtered_by_artist"]
                for track in filtered.get("tracks", []):
                    if hasattr(track, 'id') and track.id:
                        song_ids.append(track.id)
            
            # Si hay tracks en los datos completos (solo como último recurso)
            elif complete_data.get("tracks"):
                print("⚠️ Usando datos generales de biblioteca como último recurso")
                for track in complete_data["tracks"][:20]:  # Limitar a 20
                    if hasattr(track, 'id') and track.id:
                        song_ids.append(track.id)
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_song_ids = []
        for song_id in song_ids:
            if song_id not in seen:
                seen.add(song_id)
                unique_song_ids.append(song_id)
        
        print(f"🎵 Extraídos {len(unique_song_ids)} IDs de canciones para la playlist")
        return unique_song_ids

    async def close(self):
        """Cerrar todas las conexiones"""
        try:
            await self.navidrome.close()
            if self.listenbrainz:
                await self.listenbrainz.close()
            if self.musicbrainz:
                await self.musicbrainz.close()
        except Exception as e:
            print(f"Error cerrando conexiones: {e}")

