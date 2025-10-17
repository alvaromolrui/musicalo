import google.generativeai as genai
import os
from typing import Dict, Any, List, Optional
from services.lastfm_service import LastFMService
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
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
        self.lastfm = None
        if os.getenv("LASTFM_API_KEY") and os.getenv("LASTFM_USERNAME"):
            try:
                self.lastfm = LastFMService()
                print("✅ Agente musical: Last.fm habilitado")
            except Exception as e:
                print(f"⚠️ Agente musical: Error inicializando Last.fm: {e}")
        
        self.navidrome = NavidromeService()
        
        self.listenbrainz = None
        if os.getenv("LISTENBRAINZ_USERNAME"):
            try:
                self.listenbrainz = ListenBrainzService()
                print("✅ Agente musical: ListenBrainz habilitado")
            except Exception as e:
                print(f"⚠️ Agente musical: Error inicializando ListenBrainz: {e}")
        
        # Determinar servicio de scrobbling principal
        self.music_service = self.lastfm or self.listenbrainz
        self.music_service_name = "Last.fm" if self.lastfm else "ListenBrainz" if self.listenbrainz else None
    
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
        data_context = await self._gather_all_data(user_question)
        
        # 2. Obtener estadísticas del usuario para personalización
        user_stats = {}
        if self.music_service:
            try:
                top_artists_data = await self.music_service.get_top_artists(limit=5)
                user_stats['top_artists'] = [a.name for a in top_artists_data]
                
                recent_tracks = await self.music_service.get_recent_tracks(limit=1)
                if recent_tracks:
                    user_stats['last_track'] = f"{recent_tracks[0].artist} - {recent_tracks[0].name}"
            except Exception as e:
                print(f"⚠️ Error obteniendo stats para contexto: {e}")
        
        # 3. Construir prompt inteligente usando SystemPrompts
        conversation_context = session.get_context_for_ai()
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
2. LUEGO complementa con Last.fm (🌍) para recomendaciones y descubrimientos
3. Si preguntan "mejor disco/álbum de X":
   a) Verifica QUÉ TIENE en biblioteca de ese artista
   b) Combina con recomendaciones de Last.fm
   c) Responde: "En tu biblioteca tienes X, Y, Z. Según Last.fm, el mejor es..."
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
   → Si no tiene → Busca en LAST.FM y recomienda
   → Ejemplo: "No tienes de [artista] en biblioteca, pero en Last.fm su mejor álbum es X"

3. "Recomiéndame un disco" (sin artista específico)
   → USA BIBLIOTECA + LAST.FM
   → Combina: algo de su biblioteca + descubrimientos nuevos
   → Ejemplo: "De tu biblioteca: X. También te gustará Y (nuevo en Last.fm)"

4. "Recomiéndame algo nuevo / que no tenga"
   → USA PRINCIPALMENTE LAST.FM
   → Recomienda música que NO está en biblioteca
   → Basado en sus gustos pero nuevo contenido

IMPORTANTE - "Playlist con música DE [artistas]":
- Si piden "playlist de/con [lista de artistas]", busca canciones de ESOS ARTISTAS ESPECÍFICOS
- Ejemplo: "música de mujeres, vera fauna y cala vento" → busca canciones de esos 3 artistas
- VERIFICA que cada canción sea del artista correcto
- Si NO tienes algunos artistas, menciona cuáles SÍ tienes y cuáles NO

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
            
            # Guardar respuesta en historial de conversación
            session.add_message("assistant", answer)
            
            return {
                "answer": answer,
                "data_used": data_context,
                "links": self._extract_lastfm_links(data_context),
                "success": True,
                "session_id": user_id
            }
        
        except Exception as e:
            print(f"❌ Error generando respuesta del agente: {e}")
            return {
                "answer": f"❌ Error procesando tu consulta: {str(e)}",
                "data_used": data_context,
                "links": [],
                "success": False
            }
    
    async def _gather_all_data(self, query: str) -> Dict[str, Any]:
        """Recopilar datos de todas las fuentes disponibles
        
        Args:
            query: Consulta del usuario para determinar qué datos recopilar
            
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
        
        # Detectar menciones de artistas/álbumes/discos (buscar en biblioteca)
        # MEJORADO: También buscar cuando preguntan por "mejor disco de", "álbum de", etc.
        needs_library_search = any(word in query_lower for word in [
            "tengo", "teengo", "biblioteca", "colección", "poseo", 
            "álbum", "album", "disco", "álbumes", "albums", "discos",
            "mejor disco de", "mejor álbum de", "disco de", "álbum de",
            "discografía", "música de", "canciones de", "temas de"
        ])
        
        needs_listening_history = any(word in query_lower for word in [
            "escuché", "escuchado", "última", "reciente", "top", "favorito", "estadística", "últimos"
        ])
        
        # NUEVO: Detectar cuando el usuario pide descubrir música nueva
        needs_new_music = any(word in query_lower for word in [
            "nuevo", "nueva", "nuevos", "nuevas", "no tenga", "descubrir", 
            "recomienda", "recomiéndame", "sugerencia", "otra cosa", "mejor"
        ])
        
        # Extraer término de búsqueda real (eliminar palabras comunes)
        search_term = self._extract_search_term(query) if needs_library_search else query
        
        # Datos de biblioteca (Navidrome)
        if needs_library_search and search_term:
            try:
                print(f"🔍 Buscando en biblioteca: '{search_term}' (query original: '{query}')")
                # Búsqueda en biblioteca con el término extraído
                search_results = await self.navidrome.search(search_term, limit=20)
                
                # FILTRAR resultados para mantener solo los que realmente coincidan con el artista
                filtered_results = self._filter_relevant_results(search_results, search_term)
                
                data["library"]["search_results"] = filtered_results
                data["library"]["search_term"] = search_term
                
                # Si la búsqueda devuelve resultados, agregar más contexto
                if any(filtered_results.values()):
                    data["library"]["has_content"] = True
                    print(f"✅ Encontrado en biblioteca (después de filtrar): {len(filtered_results.get('tracks', []))} tracks, {len(filtered_results.get('albums', []))} álbumes, {len(filtered_results.get('artists', []))} artistas")
                else:
                    data["library"]["has_content"] = False
                    print(f"⚠️ No se encontraron resultados relevantes en biblioteca para '{search_term}'")
                    
            except Exception as e:
                print(f"⚠️ Error obteniendo datos de Navidrome: {e}")
                data["library"]["error"] = str(e)
        
        # Datos de escucha (Last.fm o ListenBrainz)
        if self.music_service and needs_listening_history:
            try:
                print(f"📊 Obteniendo historial de escucha de {self.music_service_name}")
                
                # Obtener datos básicos
                data["listening_history"]["recent_tracks"] = await self.music_service.get_recent_tracks(limit=20)
                data["listening_history"]["top_artists"] = await self.music_service.get_top_artists(limit=10)
                
                # Si preguntan por tracks específicos
                if "canción" in query_lower or "track" in query_lower or "tema" in query_lower:
                    data["listening_history"]["top_tracks"] = await self.music_service.get_top_tracks(limit=10)
                
                # Si preguntan por estadísticas
                if "estadística" in query_lower or "stats" in query_lower or "cuánto" in query_lower:
                    if hasattr(self.music_service, 'get_user_stats'):
                        data["listening_history"]["stats"] = await self.music_service.get_user_stats()
                
            except Exception as e:
                print(f"⚠️ Error obteniendo historial de escucha: {e}")
                data["listening_history"]["error"] = str(e)
        
        # Búsqueda de contenido similar (usando Last.fm)
        if self.lastfm and ("similar" in query_lower or "parecido" in query_lower or "como" in query_lower):
            try:
                print(f"🔍 Buscando contenido similar")
                # Extraer nombre de artista/álbum de la query
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() in ["similar", "parecido", "como"] and i + 1 < len(words):
                        potential_artist = " ".join(words[i+1:])
                        similar_artists = await self.lastfm.get_similar_artists(potential_artist, limit=5)
                        if similar_artists:
                            data["similar_content"] = similar_artists
                        break
            except Exception as e:
                print(f"⚠️ Error buscando contenido similar: {e}")
        
        # NUEVO: Buscar información de Last.fm sobre artistas específicos cuando preguntan por "mejor disco/álbum"
        if self.lastfm and needs_library_search and search_term and any(word in query_lower for word in ["mejor", "recomend"]):
            try:
                print(f"🌍 Buscando información de Last.fm sobre '{search_term}'...")
                # Obtener top álbumes del artista desde Last.fm
                top_albums = await self.lastfm.get_artist_top_albums(search_term, limit=10)
                if top_albums:
                    data["lastfm_artist_info"] = {
                        "artist": search_term,
                        "top_albums": top_albums
                    }
                    print(f"✅ Encontrados {len(top_albums)} álbumes de '{search_term}' en Last.fm")
            except Exception as e:
                print(f"⚠️ Error obteniendo info de Last.fm para '{search_term}': {e}")
        
        # NUEVO: Buscar música nueva activamente cuando lo pidan
        if needs_new_music and self.music_service:
            try:
                print(f"🌍 Buscando música NUEVA basada en gustos del usuario...")
                
                # Obtener top artistas del usuario
                top_artists = await self.music_service.get_top_artists(limit=5)
                
                if top_artists and self.lastfm:
                    # Buscar artistas similares a sus favoritos
                    new_discoveries = []
                    for top_artist in top_artists[:3]:  # Solo los top 3
                        similar = await self.lastfm.get_similar_artists(top_artist.name, limit=3)
                        for artist in similar:
                            # Agregar solo si no está duplicado
                            if artist.name not in [d.get('artist') for d in new_discoveries]:
                                # Obtener el álbum top del artista para dar recomendación concreta
                                top_albums = await self.lastfm.get_artist_top_albums(artist.name, limit=1)
                                
                                discovery = {
                                    'artist': artist.name,
                                    'url': artist.url if hasattr(artist, 'url') else None,
                                    'top_album': top_albums[0].get('name') if top_albums else None,
                                    'album_url': top_albums[0].get('url') if top_albums else None,
                                    'similar_to': top_artist.name  # Para contexto
                                }
                                new_discoveries.append(discovery)
                        
                        # Limitar a 8 descubrimientos total
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
        
        # SIEMPRE mostrar primero la biblioteca (si hay búsqueda)
        if data.get("library"):
            lib = data["library"]
            search_term = lib.get("search_term", "")
            
            if lib.get("search_results"):
                results = lib["search_results"]
                
                # Priorizar álbumes si existen
                if results.get("albums"):
                    formatted += f"\n📚 === BIBLIOTECA LOCAL === \n"
                    formatted += f"📀 ÁLBUMES ENCONTRADOS PARA '{search_term.upper()}' ({len(results['albums'])}):\n"
                    formatted += f"⚠️ IMPORTANTE: Verifica que el ARTISTA coincida con lo solicitado\n\n"
                    for i, album in enumerate(results["albums"][:15], 1):
                        formatted += f"  {i}. ARTISTA: {album.artist} | ÁLBUM: {album.name}"
                        if album.year:
                            formatted += f" ({album.year})"
                        if album.track_count:
                            formatted += f" - {album.track_count} canciones"
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
        
        # Historial de escucha (Last.fm o ListenBrainz) - SOLO SI ES RELEVANTE
        if data.get("listening_history"):
            hist = data["listening_history"]
            
            # Solo mostrar estadísticas de Last.fm si NO hay datos de biblioteca
            # o si específicamente pidieron estadísticas
            if hist.get("stats"):
                stats = hist["stats"]
                formatted += f"\n📊 === ESTADÍSTICAS DE LAST.FM (NO ES TU BIBLIOTECA) ===\n"
                formatted += f"  • Total de escuchas: {stats.get('total_listens', 'N/A')}\n"
                formatted += f"  • Artistas únicos: {stats.get('total_artists', 'N/A')}\n"
                formatted += f"  • Álbumes únicos: {stats.get('total_albums', 'N/A')}\n"
                formatted += f"  • Canciones únicas: {stats.get('total_tracks', 'N/A')}\n\n"
            
            if hist.get("top_artists"):
                formatted += f"\n🏆 TUS TOP ARTISTAS MÁS ESCUCHADOS (Last.fm):\n"
                for i, artist in enumerate(hist["top_artists"][:5], 1):  # Reducido a 5
                    formatted += f"  {i}. {artist.name}"
                    if artist.playcount:
                        formatted += f" ({artist.playcount} escuchas)"
                    formatted += "\n"
        
        # Información de Last.fm sobre artista específico
        if data.get("lastfm_artist_info"):
            info = data["lastfm_artist_info"]
            formatted += f"\n🌍 === INFORMACIÓN DE LAST.FM: {info['artist'].upper()} ===\n"
            formatted += f"📊 TOP ÁLBUMES MÁS POPULARES (según Last.fm):\n\n"
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
            formatted += f"💡 Combina lo que tiene en biblioteca + popularidad en Last.fm\n\n"
        
        # Contenido similar
        if data.get("similar_content"):
            formatted += f"\n🔗 ARTISTAS SIMILARES:\n"
            for i, artist in enumerate(data["similar_content"][:5], 1):
                url_info = f" - {artist.url}" if hasattr(artist, 'url') and artist.url else ""
                formatted += f"  {i}. {artist.name}{url_info}\n"
        
        # NUEVO: Descubrimientos (música que NO está en biblioteca pero puede recomendar)
        if data.get("new_discoveries"):
            formatted += f"\n🌍 === MÚSICA NUEVA PARA DESCUBRIR (de Last.fm) ===\n"
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
        
        return formatted
    
    def _extract_lastfm_links(self, data: Dict[str, Any]) -> List[str]:
        """Extraer todos los enlaces de Last.fm del contexto
        
        Args:
            data: Diccionario con todos los datos
            
        Returns:
            Lista de URLs únicas de Last.fm
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
        
        # Información de Last.fm
        if self.lastfm:
            try:
                # Artistas similares
                info["similar_artists"] = await self.lastfm.get_similar_artists(artist_name, limit=5)
                
                # Top álbumes
                info["top_albums"] = await self.lastfm.get_artist_top_albums(artist_name, limit=5)
                
                # Top tracks
                info["top_tracks"] = await self.lastfm.get_artist_top_tracks(artist_name, limit=5)
            except Exception as e:
                print(f"Error obteniendo info de Last.fm: {e}")
        
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
        
        def similarity_ratio(a: str, b: str) -> float:
            """Calcular similitud entre dos strings"""
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # Umbral de similitud (0.6 = 60% similar)
        SIMILARITY_THRESHOLD = 0.6
        
        filtered = {
            "tracks": [],
            "albums": [],
            "artists": []
        }
        
        search_lower = search_term.lower()
        
        # Filtrar álbumes
        for album in results.get("albums", []):
            artist_similarity = similarity_ratio(album.artist, search_term)
            album_similarity = similarity_ratio(album.name, search_term)
            artist_lower = album.artist.lower()
            
            # MEJORADO: Mantener si:
            # 1. El término de búsqueda está CONTENIDO en el nombre del artista
            # 2. El artista es similar al término de búsqueda (60%+)
            # 3. El álbum contiene el término de búsqueda
            if (search_lower in artist_lower or 
                artist_lower.startswith(search_lower) or
                artist_similarity >= SIMILARITY_THRESHOLD or 
                search_lower in album.name.lower()):
                filtered["albums"].append(album)
                print(f"   ✓ Álbum mantenido: {album.artist} - {album.name} (similitud: {artist_similarity:.2f})")
            else:
                print(f"   ✗ Álbum filtrado: {album.artist} - {album.name} (similitud: {artist_similarity:.2f})")
        
        # Filtrar artistas
        for artist in results.get("artists", []):
            artist_similarity = similarity_ratio(artist.name, search_term)
            artist_lower = artist.name.lower()
            
            # MEJORADO: Mantener si el término está contenido o el nombre comienza con él
            if (search_lower in artist_lower or 
                artist_lower.startswith(search_lower) or
                artist_similarity >= SIMILARITY_THRESHOLD):
                filtered["artists"].append(artist)
                print(f"   ✓ Artista mantenido: {artist.name} (similitud: {artist_similarity:.2f})")
            else:
                print(f"   ✗ Artista filtrado: {artist.name} (similitud: {artist_similarity:.2f})")
        
        # Filtrar canciones
        for track in results.get("tracks", []):
            artist_similarity = similarity_ratio(track.artist, search_term)
            artist_lower = track.artist.lower()
            
            # MEJORADO: Mantener si el término está contenido en el artista
            if (search_lower in artist_lower or 
                artist_lower.startswith(search_lower) or
                artist_similarity >= SIMILARITY_THRESHOLD):
                filtered["tracks"].append(track)
            else:
                print(f"   ✗ Canción filtrada: {track.artist} - {track.title}")
        
        return filtered
    
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
    
    async def close(self):
        """Cerrar todas las conexiones"""
        try:
            await self.navidrome.close()
            if self.lastfm:
                await self.lastfm.close()
            if self.listenbrainz:
                await self.listenbrainz.close()
        except Exception as e:
            print(f"Error cerrando conexiones: {e}")

