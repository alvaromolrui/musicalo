import google.generativeai as genai
import os
from typing import Dict, Any, List, Optional
from services.lastfm_service import LastFMService
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService

class MusicAgentService:
    """
    Agente musical inteligente que combina todas las fuentes de datos
    para responder consultas conversacionales sobre música
    """
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
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
    
    async def query(self, user_question: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Procesar consulta del usuario usando todas las fuentes disponibles
        
        Args:
            user_question: Pregunta o consulta del usuario
            context: Contexto adicional (opcional)
            
        Returns:
            Diccionario con la respuesta y datos utilizados
            
        Ejemplos:
            - "¿Qué álbumes de Pink Floyd tengo en mi biblioteca?"
            - "Dame información sobre el último artista que escuché"
            - "¿Cuántas veces he escuchado a Queen?"
            - "Dime álbumes similares a The Dark Side of the Moon"
        """
        
        print(f"🤖 Agente musical procesando: {user_question}")
        
        # 1. Recopilar datos de todas las fuentes
        data_context = await self._gather_all_data(user_question)
        
        # 2. Construir prompt inteligente para la IA
        ai_prompt = f"""Eres un asistente musical experto con acceso a múltiples fuentes de datos del usuario.

PREGUNTA DEL USUARIO: {user_question}

DATOS DISPONIBLES:
{self._format_context_for_ai(data_context)}

INSTRUCCIONES:
1. Analiza la pregunta y los datos disponibles
2. Proporciona una respuesta precisa, útil y conversacional
3. Si hay enlaces a Last.fm disponibles, inclúyelos en formato Markdown: [texto](url)
4. Si la pregunta implica crear una playlist, sugiere canciones específicas de los datos disponibles
5. Sé conversacional pero informativo
6. Usa emojis apropiados para música (🎵, 🎤, 📀, 🎸, etc.)
7. Si preguntan por estadísticas, proporciona números específicos de los datos
8. Si preguntan por algo que no está en los datos, dilo claramente y sugiere alternativas

IMPORTANTE:
- Responde SOLO con información de los datos proporcionados
- Si algo no está disponible en los datos, dilo honestamente
- Sé específico con nombres de artistas, álbumes y canciones
- Si hay múltiples resultados, lista los más relevantes

Respuesta:"""
        
        # 3. Generar respuesta con IA
        try:
            response = self.model.generate_content(ai_prompt)
            answer = response.text.strip()
            
            print(f"✅ Agente musical: Respuesta generada ({len(answer)} caracteres)")
            
            return {
                "answer": answer,
                "data_used": data_context,
                "links": self._extract_lastfm_links(data_context),
                "success": True
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
            "similar_content": []
        }
        
        # Detectar palabras clave para optimizar búsquedas
        query_lower = query.lower()
        needs_library_search = any(word in query_lower for word in [
            "tengo", "biblioteca", "colección", "poseo", "álbum", "disco", "álbumes", "discos"
        ])
        needs_listening_history = any(word in query_lower for word in [
            "escuché", "escuchado", "última", "reciente", "top", "favorito", "estadística"
        ])
        
        # Extraer término de búsqueda real (eliminar palabras comunes)
        search_term = self._extract_search_term(query) if needs_library_search else query
        
        # Datos de biblioteca (Navidrome)
        if needs_library_search and search_term:
            try:
                print(f"🔍 Buscando en biblioteca: '{search_term}' (query original: '{query}')")
                # Búsqueda en biblioteca con el término extraído
                search_results = await self.navidrome.search(search_term, limit=20)
                data["library"]["search_results"] = search_results
                data["library"]["search_term"] = search_term
                
                # Si la búsqueda devuelve resultados, agregar más contexto
                if any(search_results.values()):
                    data["library"]["has_content"] = True
                    print(f"✅ Encontrado en biblioteca: {len(search_results.get('tracks', []))} tracks, {len(search_results.get('albums', []))} álbumes, {len(search_results.get('artists', []))} artistas")
                else:
                    data["library"]["has_content"] = False
                    print(f"⚠️ No se encontraron resultados en biblioteca para '{search_term}'")
                    
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
                # (Esto es simplificado, en una implementación real sería más sofisticado)
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
        
        return data
    
    def _format_context_for_ai(self, data: Dict[str, Any]) -> str:
        """Formatear contexto para que la IA lo entienda
        
        Args:
            data: Diccionario con todos los datos recopilados
            
        Returns:
            String formateado con toda la información para la IA
        """
        formatted = ""
        
        # Biblioteca (Navidrome)
        if data.get("library"):
            lib = data["library"]
            
            if lib.get("search_results"):
                results = lib["search_results"]
                
                if results.get("tracks"):
                    formatted += f"\n📚 CANCIONES EN BIBLIOTECA ({len(results['tracks'])}):\n"
                    for i, track in enumerate(results["tracks"][:10], 1):
                        formatted += f"  {i}. {track.artist} - {track.title}"
                        if track.album:
                            formatted += f" (Álbum: {track.album})"
                        if track.year:
                            formatted += f" [{track.year}]"
                        formatted += "\n"
                
                if results.get("albums"):
                    formatted += f"\n📀 ÁLBUMES EN BIBLIOTECA ({len(results['albums'])}):\n"
                    for i, album in enumerate(results["albums"][:10], 1):
                        formatted += f"  {i}. {album.artist} - {album.name}"
                        if album.year:
                            formatted += f" ({album.year})"
                        if album.track_count:
                            formatted += f" - {album.track_count} canciones"
                        formatted += "\n"
                
                if results.get("artists"):
                    formatted += f"\n🎤 ARTISTAS EN BIBLIOTECA ({len(results['artists'])}):\n"
                    for i, artist in enumerate(results["artists"][:10], 1):
                        formatted += f"  {i}. {artist.name}"
                        if artist.album_count:
                            formatted += f" ({artist.album_count} álbumes)"
                        formatted += "\n"
            
            if lib.get("has_content") == False:
                formatted += "\n⚠️ No se encontraron resultados en la biblioteca de Navidrome\n"
        
        # Historial de escucha (Last.fm o ListenBrainz)
        if data.get("listening_history"):
            hist = data["listening_history"]
            
            if hist.get("stats"):
                stats = hist["stats"]
                formatted += f"\n📊 ESTADÍSTICAS DE ESCUCHA:\n"
                formatted += f"  • Total de escuchas: {stats.get('total_listens', 'N/A')}\n"
                formatted += f"  • Artistas únicos: {stats.get('total_artists', 'N/A')}\n"
                formatted += f"  • Álbumes únicos: {stats.get('total_albums', 'N/A')}\n"
                formatted += f"  • Canciones únicas: {stats.get('total_tracks', 'N/A')}\n"
            
            if hist.get("recent_tracks"):
                formatted += f"\n⏰ ÚLTIMAS ESCUCHAS:\n"
                for i, track in enumerate(hist["recent_tracks"][:10], 1):
                    url_info = f" - {track.url}" if track.url else ""
                    formatted += f"  {i}. {track.artist} - {track.name}"
                    if track.album:
                        formatted += f" ({track.album})"
                    formatted += url_info + "\n"
            
            if hist.get("top_artists"):
                formatted += f"\n🏆 TOP ARTISTAS:\n"
                for i, artist in enumerate(hist["top_artists"][:10], 1):
                    url_info = f" - {artist.url}" if artist.url else ""
                    formatted += f"  {i}. {artist.name}"
                    if artist.playcount:
                        formatted += f" ({artist.playcount} escuchas)"
                    formatted += url_info + "\n"
            
            if hist.get("top_tracks"):
                formatted += f"\n🎵 TOP CANCIONES:\n"
                for i, track in enumerate(hist["top_tracks"][:10], 1):
                    url_info = f" - {track.url}" if track.url else ""
                    formatted += f"  {i}. {track.artist} - {track.name}"
                    if track.playcount:
                        formatted += f" ({track.playcount} escuchas)"
                    formatted += url_info + "\n"
        
        # Contenido similar
        if data.get("similar_content"):
            formatted += f"\n🔗 ARTISTAS SIMILARES:\n"
            for i, artist in enumerate(data["similar_content"][:5], 1):
                url_info = f" - {artist.url}" if hasattr(artist, 'url') and artist.url else ""
                formatted += f"  {i}. {artist.name}{url_info}\n"
        
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
            'muestra', 'mostrar', 'ver', 'a', 'e', 'i', 'o', 'u', 'y'
        }
        
        # Primero, intentar encontrar nombres propios (palabras con mayúsculas)
        # Patrón: buscar palabras que empiecen con mayúscula
        capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        cap_matches = re.findall(capitalized_pattern, query)
        
        if cap_matches:
            # Unir todas las palabras capitalizadas encontradas
            result = ' '.join(cap_matches)
            print(f"🔍 Término extraído (mayúsculas): '{result}'")
            return result
        
        # Si no hay mayúsculas, buscar patrón "de [artista]"
        de_pattern = r'de\s+([a-zA-Z][a-zA-Z\s]+?)(?:\s+tengo|\s+en|\?|$)'
        de_match = re.search(de_pattern, query, re.IGNORECASE)
        if de_match:
            result = de_match.group(1).strip()
            print(f"🔍 Término extraído (patrón 'de'): '{result}'")
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

