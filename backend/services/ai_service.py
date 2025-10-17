import google.generativeai as genai
import os
from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter
import re
import random
from models.schemas import UserProfile, Recommendation, Track, LastFMTrack, LastFMArtist, MusicAnalysis
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.lastfm_service import LastFMService

class MusicRecommendationService:
    def __init__(self):
        # Configurar Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.navidrome = NavidromeService()
        self.listenbrainz = ListenBrainzService()
        
        # Inicializar Last.fm si está configurado
        self.lastfm = None
        if os.getenv("LASTFM_API_KEY") and os.getenv("LASTFM_USERNAME"):
            self.lastfm = LastFMService()
            print("✅ Servicio de recomendaciones con Last.fm habilitado")
    
    async def analyze_user_profile(self, user_profile: UserProfile) -> MusicAnalysis:
        """Analizar el perfil musical del usuario"""
        try:
            # Análisis de géneros
            genres = []
            for track in user_profile.recent_tracks:
                # Simular extracción de género (en un caso real, usarías APIs de música)
                genre = await self._extract_genre(track.artist, track.name)
                if genre:
                    genres.append(genre)
            
            genre_distribution = dict(Counter(genres))
            total_tracks = len(genres)
            if total_tracks > 0:
                genre_distribution = {k: v/total_tracks for k, v in genre_distribution.items()}
            
            # Análisis de patrones temporales
            time_patterns = self._analyze_time_patterns(user_profile.recent_tracks)
            
            # Análisis de diversidad de artistas
            unique_artists = set()
            for track in user_profile.recent_tracks:
                unique_artists.add(track.artist)
            
            artist_diversity = len(unique_artists) / max(len(user_profile.recent_tracks), 1)
            
            # Análisis de humor basado en patrones de escucha
            mood_analysis = await self._analyze_mood_patterns(user_profile.recent_tracks)
            
            return MusicAnalysis(
                genre_distribution=genre_distribution,
                tempo_preferences={},  # Se podría implementar con análisis de audio
                mood_analysis=mood_analysis,
                time_patterns=time_patterns,
                artist_diversity=artist_diversity,
                discovery_rate=self._calculate_discovery_rate(user_profile)
            )
            
        except Exception as e:
            print(f"Error analizando perfil: {e}")
            return MusicAnalysis(
                genre_distribution={},
                tempo_preferences={},
                mood_analysis={},
                time_patterns={},
                artist_diversity=0.0,
                discovery_rate=0.0
            )
    
    async def generate_recommendations(
        self, 
        user_profile: UserProfile, 
        limit: int = 10, 
        include_new_music: bool = True,
        recommendation_type: str = "general",
        genre_filter: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en el perfil del usuario
        
        Args:
            user_profile: Perfil del usuario con sus gustos
            limit: Número de recomendaciones a generar
            include_new_music: Si True, incluye música que no está en la biblioteca (usando Last.fm)
            recommendation_type: 'general', 'album', 'artist', 'track'
            genre_filter: Género o estilo específico para filtrar
            custom_prompt: Descripción libre y específica del usuario sobre lo que busca
        """
        try:
            # Mensaje de log con información del prompt personalizado
            if custom_prompt:
                print(f"🎯 Generando {limit} recomendaciones con criterios específicos: {custom_prompt[:100]}...")
            else:
                print(f"🎯 Generando {limit} recomendaciones...")
            
            # Analizar perfil del usuario
            analysis = await self.analyze_user_profile(user_profile)
            
            recommendations = []
            
            # Si hay un custom_prompt, usar la IA para generar recomendaciones más específicas
            if custom_prompt:
                print(f"🎨 Usando descripción personalizada para recomendaciones...")
                custom_recs = await self._generate_custom_prompt_recommendations(
                    user_profile,
                    analysis,
                    custom_prompt,
                    limit,
                    recommendation_type
                )
                recommendations.extend(custom_recs)
                print(f"✅ Encontradas {len(custom_recs)} recomendaciones personalizadas")
            
            # Si Last.fm está habilitado y se solicita música nueva (y no hay suficientes recomendaciones), usarlo
            if len(recommendations) < limit and include_new_music and self.lastfm and len(user_profile.top_artists) > 0:
                remaining_limit = limit - len(recommendations)
                print(f"🌍 Buscando música nueva usando Last.fm (tipo: {recommendation_type}, género: {genre_filter})...")
                new_music_recs = await self._generate_lastfm_recommendations(
                    user_profile, 
                    remaining_limit, 
                    recommendation_type=recommendation_type,
                    genre_filter=genre_filter,
                    custom_prompt=custom_prompt
                )
                recommendations.extend(new_music_recs)
                print(f"✅ Encontradas {len(new_music_recs)} recomendaciones de música nueva")
            
            # Si no hay suficientes, buscar en la biblioteca
            if len(recommendations) < limit:
                print("📚 Buscando en tu biblioteca de Navidrome...")
                library_tracks = await self.navidrome.get_tracks(limit=200)
                
                # Filtrar canciones ya conocidas
                known_tracks = {track.name.lower() for track in user_profile.recent_tracks}
                unknown_tracks = [
                    track for track in library_tracks 
                    if track.title.lower() not in known_tracks
                ]
                
                # Generar recomendaciones usando IA
                library_recs = await self._generate_ai_recommendations(
                    user_profile, analysis, unknown_tracks, limit - len(recommendations)
                )
                recommendations.extend(library_recs)
                print(f"✅ Encontradas {len(library_recs)} recomendaciones de tu biblioteca")
            
            print(f"🎵 Total de recomendaciones: {len(recommendations)}")
            return recommendations[:limit]
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones: {e}")
            return []
    
    async def _generate_lastfm_recommendations(
        self, 
        user_profile: UserProfile, 
        limit: int,
        recommendation_type: str = "general",
        genre_filter: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> List[Recommendation]:
        """Generar recomendaciones usando Last.fm (música nueva que no tienes)
        
        Args:
            user_profile: Perfil del usuario
            limit: Número de recomendaciones
            recommendation_type: 'general', 'album', 'artist', 'track'
            genre_filter: Filtro de género/estilo
            custom_prompt: Descripción específica del usuario sobre lo que busca
        """
        try:
            recommendations = []
            processed_artists = set()
            
            # Seleccionar aleatoriamente algunos top artistas para variar las recomendaciones
            available_top_artists = user_profile.top_artists[:10]  # Considerar top 10
            num_artists_to_use = min(5, len(available_top_artists))
            selected_artists = random.sample(available_top_artists, num_artists_to_use) if len(available_top_artists) > num_artists_to_use else available_top_artists
            
            print(f"🔍 Generando recomendaciones de Last.fm para {len(selected_artists)} artistas (seleccionados aleatoriamente)")
            
            # Para asegurar diversidad, tomar 1 recomendación por artista
            # Obtener artistas similares basados en los artistas seleccionados
            for top_artist in selected_artists:
                if len(recommendations) >= limit:
                    break
                
                print(f"🎤 Buscando artistas similares a: {top_artist.name}")
                # Obtener más artistas similares y seleccionar aleatoriamente
                similar_artists = await self.lastfm.get_similar_artists(top_artist.name, limit=10)
                print(f"   Encontrados {len(similar_artists)} artistas similares")
                
                # Aleatorizar el orden de artistas similares
                if similar_artists:
                    random.shuffle(similar_artists)
                
                # IMPORTANTE: Solo tomar 1 artista similar por cada top_artist para diversidad
                similar_artist = None
                for candidate in similar_artists:
                    if candidate.name not in processed_artists:
                        similar_artist = candidate
                        break
                
                if not similar_artist:
                    continue
                    
                processed_artists.add(similar_artist.name)
                
                # Aplicar filtro de género si existe
                if genre_filter:
                    # Por ahora, incluir todos los artistas similares
                    # En una implementación futura se podría consultar tags del artista
                    pass
                
                # Crear recomendación del artista similar
                print(f"   ➕ Agregando recomendación: {similar_artist.name}")
                
                # Personalizar según el tipo de recomendación
                title = ""
                reason = ""
                album_name = ""
                artist_url = similar_artist.url if hasattr(similar_artist, 'url') and similar_artist.url else ""
                
                if recommendation_type == "album":
                    # Obtener el álbum top del artista similar
                    top_albums = await self.lastfm.get_artist_top_albums(similar_artist.name, limit=1)
                    if top_albums:
                        album_data = top_albums[0]
                        title = album_data.get("name", f"Álbum de {similar_artist.name}")
                        album_name = album_data.get("name", "")
                        artist_url = album_data.get("url", artist_url)
                        reason = f"📀 Álbum top de artista similar a {top_artist.name}"
                    else:
                        title = f"Discografía de {similar_artist.name}"
                        reason = f"📀 Similar a {top_artist.name}"
                
                elif recommendation_type == "track":
                    # Obtener la canción top del artista similar
                    top_tracks = await self.lastfm.get_artist_top_tracks(similar_artist.name, limit=1)
                    if top_tracks:
                        track_data = top_tracks[0]
                        title = track_data.name
                        artist_url = track_data.url if track_data.url else artist_url
                        reason = f"🎵 Canción top de artista similar a {top_artist.name}"
                    else:
                        title = f"Música de {similar_artist.name}"
                        reason = f"🎵 Similar a {top_artist.name}"
                
                elif recommendation_type == "artist":
                    title = similar_artist.name
                    reason = f"🌟 Similar a {top_artist.name}"
                
                else:
                    title = f"Descubre {similar_artist.name}"
                    reason = f"🌟 Artista similar a {top_artist.name} que te puede gustar"
                
                # Crear el objeto Track primero
                track = Track(
                    id=f"lastfm_{recommendation_type}_{similar_artist.name.replace(' ', '_')}_{title.replace(' ', '_')[:30]}",
                    title=title,
                    artist=similar_artist.name,
                    album=album_name,
                    duration=None,
                    year=None,
                    genre=genre_filter if genre_filter else "",
                    play_count=None,
                    path=artist_url if artist_url else "",  # Usar URL en el campo path
                    cover_url=None
                )
                
                # Crear la recomendación
                recommendation = Recommendation(
                    track=track,
                    reason=reason,
                    confidence=0.85,  # Score alto para música nueva
                    source="Last.fm",
                    tags=[genre_filter] if genre_filter else []
                )
                recommendations.append(recommendation)
            
            print(f"✅ Total de recomendaciones de Last.fm: {len(recommendations)}")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones de Last.fm: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_custom_prompt_recommendations(
        self,
        user_profile: UserProfile,
        analysis: MusicAnalysis,
        custom_prompt: str,
        limit: int,
        recommendation_type: str = "general"
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en una descripción específica del usuario usando IA
        
        Args:
            user_profile: Perfil del usuario
            analysis: Análisis del perfil musical
            custom_prompt: Descripción específica de lo que el usuario busca
            limit: Número de recomendaciones
            recommendation_type: Tipo de recomendación
        """
        try:
            print(f"🎨 Generando recomendaciones con prompt personalizado: {custom_prompt}")
            
            # Preparar contexto del usuario
            recent_artists = [track.artist for track in user_profile.recent_tracks[:15]]
            top_artists = [artist.name for artist in user_profile.top_artists[:10]]
            
            # Crear un prompt inteligente para la IA que entienda las especificaciones
            ai_prompt = f"""Eres un experto curador musical con conocimiento profundo de música de todos los géneros, épocas y estilos.

PERFIL DEL USUARIO:
- Top artistas favoritos: {', '.join(top_artists[:5]) if top_artists else 'Desconocidos'}
- Artistas que escucha recientemente: {', '.join(set(recent_artists[:10])) if recent_artists else 'Desconocidos'}
- Géneros que le gustan: {', '.join(list(analysis.genre_distribution.keys())[:5]) if analysis.genre_distribution else 'Variados'}
- Diversidad musical: {analysis.artist_diversity:.2f} (0 = muy específico, 1 = muy diverso)

PETICIÓN DEL USUARIO:
"{custom_prompt}"

TIPO DE RECOMENDACIÓN:
{recommendation_type} (album = álbumes, artist = artistas, track = canciones, general = cualquiera)

TU TAREA:
1. Analiza cuidadosamente la petición del usuario y todos sus detalles específicos
2. Ten en cuenta sus gustos actuales pero prioriza lo que está pidiendo específicamente
3. Si menciona características específicas (época, estilo, instrumentos, mood, energía, etc.), enfócate en eso
4. Si menciona un artista/banda como referencia, busca similitudes pero también piensa en otros que cumplan los criterios
5. Genera exactamente {limit} recomendaciones que cumplan con TODOS los criterios mencionados

IMPORTANTE:
- Sé ESPECÍFICO con nombres de artistas, álbumes y canciones reales
- Si pide características específicas (ej: "rock progresivo de los 70s"), busca artistas que cumplan exactamente eso
- Si pide algo "similar a X", piensa en qué hace especial a X y busca otros con esas cualidades
- Si menciona múltiples criterios (ej: "rock energético con buenos solos de guitarra"), TODOS deben cumplirse
- Las recomendaciones deben ser variadas entre sí pero todas cumplir los criterios

FORMATO DE RESPUESTA:
Proporciona EXACTAMENTE {limit} recomendaciones en este formato:
[ARTISTA] - [NOMBRE] | [RAZÓN DETALLADA]

Ejemplo:
Pink Floyd - The Dark Side of the Moon | Álbum conceptual de rock progresivo de 1973 con sintetizadores atmosféricos
Led Zeppelin - Physical Graffiti | Rock épico de los 70s con solos de guitarra legendarios de Jimmy Page

Genera las {limit} recomendaciones ahora:"""

            # Generar con Gemini
            response = self.model.generate_content(ai_prompt)
            ai_response = response.text.strip()
            
            print(f"📝 Respuesta de IA recibida (longitud: {len(ai_response)})")
            
            # Procesar las recomendaciones de la IA
            recommendations = []
            lines = [line.strip() for line in ai_response.split('\n') if line.strip()]
            
            for line in lines:
                if len(recommendations) >= limit:
                    break
                
                # Buscar el formato: [ARTISTA] - [NOMBRE] | [RAZÓN]
                # o formatos alternativos comunes
                try:
                    # Intentar parsear formato con |
                    if '|' in line and '-' in line:
                        parts = line.split('|', 1)
                        artist_and_name = parts[0].strip()
                        reason = parts[1].strip() if len(parts) > 1 else "Recomendado según tus criterios"
                        
                        # Remover números y puntos del inicio (ej: "1. ", "1) ")
                        artist_and_name = re.sub(r'^\d+[\.\)]\s*', '', artist_and_name)
                        
                        # Dividir artista y nombre
                        if ' - ' in artist_and_name:
                            artist, name = artist_and_name.split(' - ', 1)
                        elif '-' in artist_and_name:
                            artist, name = artist_and_name.split('-', 1)
                        else:
                            # Si no hay separador, asumir que es el nombre del artista
                            artist = artist_and_name
                            name = artist_and_name
                        
                        artist = artist.strip()
                        name = name.strip()
                        
                        # Crear objeto Track
                        track = Track(
                            id=f"ai_custom_{artist.replace(' ', '_')}_{name.replace(' ', '_')[:30]}",
                            title=name,
                            artist=artist,
                            album=name if recommendation_type == "album" else "",
                            duration=None,
                            year=None,
                            genre=genre_filter if 'genre_filter' in locals() else "",
                            play_count=None,
                            path="",
                            cover_url=None
                        )
                        
                        # Crear recomendación con contexto del prompt
                        recommendation = Recommendation(
                            track=track,
                            reason=f"{reason} (según: {custom_prompt[:50]}...)",
                            confidence=0.95,  # Alta confianza porque es específico
                            source="AI (Gemini)",
                            tags=["custom", "specific"]
                        )
                        recommendations.append(recommendation)
                        print(f"   ✅ Agregada: {artist} - {name}")
                        
                except Exception as e:
                    print(f"   ⚠️ Error parseando línea: {line} | {e}")
                    continue
            
            print(f"🎨 Total recomendaciones personalizadas generadas: {len(recommendations)}")
            
            # Si se generaron recomendaciones usando IA, intentar buscar en Last.fm
            # para agregar URLs y más información
            if self.lastfm and recommendations:
                print("🔍 Enriqueciendo recomendaciones con datos de Last.fm...")
                for rec in recommendations[:limit]:
                    try:
                        # Si es artista, buscar info del artista
                        if recommendation_type == "artist":
                            similar_artists = await self.lastfm.get_similar_artists(rec.track.artist, limit=1)
                            if similar_artists and similar_artists[0].url:
                                rec.track.path = similar_artists[0].url
                        # Si es álbum, buscar álbumes del artista
                        elif recommendation_type == "album":
                            top_albums = await self.lastfm.get_artist_top_albums(rec.track.artist, limit=5)
                            if top_albums:
                                # Buscar el álbum específico o usar el primero
                                for album_data in top_albums:
                                    if rec.track.title.lower() in album_data.get("name", "").lower():
                                        rec.track.path = album_data.get("url", "")
                                        break
                    except Exception as e:
                        print(f"   ⚠️ No se pudo enriquecer {rec.track.artist}: {e}")
                        continue
            
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones personalizadas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_ai_recommendations(
        self, 
        user_profile: UserProfile, 
        analysis: MusicAnalysis, 
        candidate_tracks: List[Track], 
        limit: int
    ) -> List[Recommendation]:
        """Generar recomendaciones usando OpenAI"""
        try:
            # Preparar contexto para la IA
            recent_artists = [track.artist for track in user_profile.recent_tracks[:10]]
            top_artists = [artist.name for artist in user_profile.top_artists[:5]]
            
            # Crear prompt para la IA
            prompt = f"""
            Eres un experto en música que analiza los gustos de los usuarios y hace recomendaciones.
            
            Perfil del usuario:
            - Artistas recientes: {', '.join(recent_artists)}
            - Top artistas: {', '.join(top_artists)}
            - Géneros favoritos: {list(analysis.genre_distribution.keys())}
            - Diversidad de artistas: {analysis.artist_diversity:.2f}
            
            Tareas:
            1. Analiza los patrones musicales del usuario
            2. Identifica qué tipos de música podría disfrutar
            3. Sugiere artistas/canciones similares pero que expandan sus horizontes
            
            Proporciona recomendaciones que sean:
            - Musicalmente coherentes con sus gustos
            - Ligeramente exploratorias para descubrir nueva música
            - Basadas en similitudes de género, estilo o época
            
            Formato de respuesta: Artista - Canción (razón de recomendación)
            """
            
            # Generar con Gemini
            response = self.model.generate_content(prompt)
            ai_suggestions = response.text
            
            # Procesar sugerencias de IA y buscar en la biblioteca
            recommendations = []
            for line in ai_suggestions.split('\n'):
                if '-' in line and len(recommendations) < limit:
                    try:
                        parts = line.split('-', 1)
                        if len(parts) == 2:
                            artist_song = parts[0].strip()
                            reason = parts[1].strip()
                            
                            # Buscar en la biblioteca
                            matches = await self._find_track_matches(artist_song, candidate_tracks)
                            
                            for track in matches[:1]:  # Tomar solo la primera coincidencia
                                recommendation = Recommendation(
                                    track=track,
                                    reason=reason,
                                    confidence=0.8,
                                    source="ai",
                                    tags=["ai-recommendation"]
                                )
                                recommendations.append(recommendation)
                    except:
                        continue
            
            return recommendations
            
        except Exception as e:
            print(f"Error generando recomendaciones con IA: {e}")
            return []
    
    async def _generate_similarity_recommendations(
        self, 
        user_profile: UserProfile, 
        candidate_tracks: List[Track], 
        limit: int
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en similitud"""
        try:
            # Obtener artistas favoritos
            favorite_artists = set()
            for track in user_profile.recent_tracks:
                favorite_artists.add(track.artist.lower())
            
            for artist in user_profile.top_artists:
                favorite_artists.add(artist.name.lower())
            
            # Buscar canciones de artistas similares o del mismo género
            recommendations = []
            
            for track in candidate_tracks:
                if len(recommendations) >= limit:
                    break
                
                # Similitud por artista
                if track.artist.lower() in favorite_artists:
                    recommendation = Recommendation(
                        track=track,
                        reason=f"Artista favorito: {track.artist}",
                        confidence=0.9,
                        source="similarity",
                        tags=["favorite-artist"]
                    )
                    recommendations.append(recommendation)
                
                # Similitud por género (simulado)
                elif await self._is_similar_genre(track, user_profile):
                    recommendation = Recommendation(
                        track=track,
                        reason=f"Género similar a tus gustos",
                        confidence=0.7,
                        source="similarity",
                        tags=["similar-genre"]
                    )
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            print(f"Error generando recomendaciones por similitud: {e}")
            return []
    
    async def _extract_genre(self, artist: str, track: str) -> Optional[str]:
        """Extraer género de una canción (simulado)"""
        # En un caso real, usarías APIs como Spotify, MusicBrainz, etc.
        genre_mapping = {
            "rock": ["rock", "metal", "punk", "grunge"],
            "pop": ["pop", "indie pop", "synthpop"],
            "electronic": ["electronic", "techno", "house", "ambient"],
            "jazz": ["jazz", "blues", "soul"],
            "classical": ["classical", "orchestral", "chamber"],
            "hip-hop": ["hip-hop", "rap", "trap"]
        }
        
        # Búsqueda simple por palabras clave
        text = f"{artist} {track}".lower()
        for genre, keywords in genre_mapping.items():
            if any(keyword in text for keyword in keywords):
                return genre
        
        return "unknown"
    
    def _analyze_time_patterns(self, tracks: List[LastFMTrack]) -> Dict[str, int]:
        """Analizar patrones temporales de escucha"""
        time_patterns = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
        
        for track in tracks:
            if track.date:
                hour = track.date.hour
                if 6 <= hour < 12:
                    time_patterns["morning"] += 1
                elif 12 <= hour < 17:
                    time_patterns["afternoon"] += 1
                elif 17 <= hour < 22:
                    time_patterns["evening"] += 1
                else:
                    time_patterns["night"] += 1
        
        return time_patterns
    
    async def _analyze_mood_patterns(self, tracks: List[LastFMTrack]) -> Dict[str, float]:
        """Analizar patrones de humor musical"""
        # Simulación de análisis de humor
        return {
            "energetic": 0.4,
            "melancholic": 0.3,
            "peaceful": 0.2,
            "aggressive": 0.1
        }
    
    def _calculate_discovery_rate(self, user_profile: UserProfile) -> float:
        """Calcular tasa de descubrimiento de nueva música"""
        if not user_profile.recent_tracks:
            return 0.0
        
        # Contar artistas únicos en las últimas 50 canciones
        recent_artists = set()
        for track in user_profile.recent_tracks[:50]:
            recent_artists.add(track.artist)
        
        # Comparar con artistas conocidos
        known_artists = set()
        for artist in user_profile.top_artists:
            known_artists.add(artist.name)
        
        new_artists = recent_artists - known_artists
        return len(new_artists) / len(recent_artists) if recent_artists else 0.0
    
    async def _find_track_matches(self, artist_song: str, tracks: List[Track]) -> List[Track]:
        """Buscar coincidencias de canciones en la biblioteca"""
        matches = []
        search_terms = artist_song.lower().split()
        
        for track in tracks:
            track_text = f"{track.artist} {track.title}".lower()
            if any(term in track_text for term in search_terms):
                matches.append(track)
        
        return matches[:3]  # Máximo 3 coincidencias
    
    async def _is_similar_genre(self, track: Track, user_profile: UserProfile) -> bool:
        """Determinar si una canción es de un género similar"""
        # Simulación simple
        user_genres = set()
        for track_data in user_profile.recent_tracks:
            genre = await self._extract_genre(track_data.artist, track_data.name)
            if genre:
                user_genres.add(genre)
        
        track_genre = await self._extract_genre(track.artist, track.title)
        return track_genre in user_genres
    
    async def generate_library_playlist(
        self,
        description: str,
        limit: int = 15
    ) -> List[Recommendation]:
        """Generar playlist SOLO de la biblioteca local
        
        Args:
            description: Descripción de lo que busca el usuario
            limit: Número de canciones (puede ser sobrescrito si se detecta en la descripción)
            
        Returns:
            Lista de recomendaciones de la biblioteca
        """
        try:
            print(f"📚 Generando playlist de biblioteca: {description}")
            
            # PASO 0: Detectar cantidad solicitada en la descripción (si existe)
            detected_count = self._extract_song_count(description)
            if detected_count:
                limit = detected_count
                print(f"✨ Usando cantidad detectada de la descripción: {limit} canciones")
            
            # PASO 1: Intentar detectar nombres de artistas específicos
            artist_names = self._extract_artist_names(description)
            all_tracks = []
            seen_ids = set()
            
            if artist_names:
                print(f"🎤 Artistas detectados: {artist_names}")
                # Buscar canciones específicas de esos artistas
                for artist_name in artist_names:
                    print(f"   🔍 Buscando canciones de '{artist_name}'...")
                    results = await self.navidrome.search(artist_name, limit=50)
                    
                    # Priorizar tracks del artista exacto
                    for track in results.get('tracks', []):
                        if track.id not in seen_ids:
                            # Verificar si es del artista (coincidencia flexible)
                            if artist_name.lower() in track.artist.lower():
                                all_tracks.append(track)
                                seen_ids.add(track.id)
                    
                    # También agregar de álbumes
                    for album in results.get('albums', []):
                        if artist_name.lower() in album.artist.lower():
                            # Buscar tracks del álbum
                            album_tracks = await self.navidrome.search(f"{album.artist} {album.name}", limit=20)
                            for track in album_tracks.get('tracks', []):
                                if track.id not in seen_ids:
                                    all_tracks.append(track)
                                    seen_ids.add(track.id)
                
                print(f"✅ Encontradas {len(all_tracks)} canciones de los artistas especificados")
            
            # PASO 2: Si no hay artistas específicos o no se encontraron suficientes, buscar por género/keywords
            if len(all_tracks) < limit:
                # Intentar detectar género musical
                genres_detected = self._extract_genres(description)
                if genres_detected:
                    print(f"🎸 Géneros detectados: {genres_detected}")
                    for genre in genres_detected:
                        # Buscar por género en Navidrome
                        genre_tracks = await self.navidrome.get_tracks(limit=100, genre=genre)
                        for track in genre_tracks:
                            if track.id not in seen_ids:
                                all_tracks.append(track)
                                seen_ids.add(track.id)
                        print(f"   ✓ Género '{genre}': {len(genre_tracks)} canciones")
                
                # También buscar por keywords generales
                keywords = self._extract_keywords(description)
                print(f"🔑 Palabras clave extraídas: {keywords}")
                
                for keyword in keywords[:3]:  # Usar hasta 3 keywords
                    results = await self.navidrome.search(keyword, limit=50)
                    for track in results.get('tracks', []):
                        if track.id not in seen_ids:
                            all_tracks.append(track)
                            seen_ids.add(track.id)
            
            # PASO 3: Si no hay artistas específicos, obtener una muestra grande de la biblioteca
            # para que el algoritmo de selección tenga suficiente material
            if not artist_names:
                # Sin artistas específicos, necesitamos una muestra grande para seleccionar
                target_pool_size = max(200, limit * 5)  # Al menos 5x el límite solicitado
                print(f"🎲 Sin artistas específicos: obteniendo {target_pool_size} canciones aleatorias de biblioteca...")
                random_tracks = await self.navidrome.get_tracks(limit=target_pool_size)
                for track in random_tracks:
                    if track.id not in seen_ids:
                        all_tracks.append(track)
                        seen_ids.add(track.id)
                print(f"✅ Agregadas {len(random_tracks)} canciones aleatorias")
            
            # PASO 4: Si aún no hay suficientes (caso con artistas específicos), completar
            elif len(all_tracks) < limit * 2:
                print(f"⚠️ Solo {len(all_tracks)} canciones de artistas específicos, complementando...")
                additional = max(100, limit * 2)
                random_tracks = await self.navidrome.get_tracks(limit=additional)
                for track in random_tracks:
                    if track.id not in seen_ids:
                        all_tracks.append(track)
                        seen_ids.add(track.id)
            
            print(f"📊 Total de canciones disponibles: {len(all_tracks)}")
            
            if not all_tracks:
                print("❌ No se encontraron canciones en la biblioteca")
                return []
            
            # NUEVO ALGORITMO: Selección con diversidad garantizada de artistas
            selected_tracks = self._smart_track_selection(
                all_tracks,
                artist_names,
                limit,
                description
            )
            
            # Crear recomendaciones
            recommendations = []
            for track in selected_tracks:
                rec = Recommendation(
                    track=track,
                    reason=f"De tu biblioteca: coincide con '{description}'",
                    confidence=0.90,  # Alta confianza porque es de la biblioteca
                    source="biblioteca",
                    tags=["local", "biblioteca"]
                )
                recommendations.append(rec)
            
            print(f"🎵 Generadas {len(recommendations)} recomendaciones de biblioteca")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando playlist de biblioteca: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _smart_track_selection(
        self,
        all_tracks: List[Track],
        artist_names: List[str],
        limit: int,
        description: str
    ) -> List[Track]:
        """Selección inteligente de canciones con garantía de diversidad de artistas
        
        Args:
            all_tracks: Lista completa de canciones disponibles
            artist_names: Lista de artistas detectados en la descripción
            limit: Número de canciones a seleccionar
            description: Descripción original de la playlist
            
        Returns:
            Lista de tracks seleccionadas con buena diversidad
        """
        import random
        from collections import defaultdict
        
        print(f"🎯 Seleccionando {limit} canciones con diversidad de artistas...")
        
        # Si no hay artistas específicos y hay muchas canciones, pre-filtrar con IA
        if not artist_names and len(all_tracks) > limit * 3:
            print(f"🤖 Usando IA para pre-filtrar canciones relevantes...")
            all_tracks = self._ai_filter_tracks(all_tracks, description, limit * 3)
            print(f"✅ Pre-filtradas a {len(all_tracks)} canciones más relevantes")
        
        # Agrupar canciones por artista
        tracks_by_artist = defaultdict(list)
        for track in all_tracks:
            artist_key = track.artist.lower() if track.artist else "unknown"
            tracks_by_artist[artist_key].append(track)
        
        print(f"📊 Canciones agrupadas en {len(tracks_by_artist)} artistas diferentes")
        
        # Si hay artistas específicos solicitados, dar prioridad equitativa
        if artist_names:
            print(f"🎤 Distribuyendo equitativamente entre {len(artist_names)} artistas: {artist_names}")
            
            # Calcular cuántas canciones por artista
            songs_per_artist = max(1, limit // len(artist_names))
            remaining = limit % len(artist_names)
            
            selected = []
            artist_count = defaultdict(int)
            
            # Primera pasada: asignar songs_per_artist a cada artista
            for artist_name in artist_names:
                artist_lower = artist_name.lower()
                
                # Buscar el grupo de canciones que coincida con este artista
                matching_tracks = []
                for artist_key, tracks in tracks_by_artist.items():
                    if artist_lower in artist_key or artist_key in artist_lower:
                        matching_tracks.extend(tracks)
                
                if matching_tracks:
                    # Aleatorizar y tomar songs_per_artist
                    random.shuffle(matching_tracks)
                    to_take = min(songs_per_artist, len(matching_tracks))
                    selected.extend(matching_tracks[:to_take])
                    artist_count[artist_lower] = to_take
                    print(f"   ✓ {artist_name}: {to_take} canciones")
                else:
                    print(f"   ✗ {artist_name}: no se encontraron canciones")
            
            # Segunda pasada: rellenar con canciones adicionales si hay espacio
            if len(selected) < limit and remaining > 0:
                # Tomar más canciones de los artistas que tienen más disponibles
                for artist_name in artist_names:
                    if len(selected) >= limit:
                        break
                    
                    artist_lower = artist_name.lower()
                    matching_tracks = []
                    for artist_key, tracks in tracks_by_artist.items():
                        if artist_lower in artist_key or artist_key in artist_lower:
                            # Excluir canciones ya seleccionadas
                            for track in tracks:
                                if track not in selected:
                                    matching_tracks.append(track)
                    
                    if matching_tracks:
                        random.shuffle(matching_tracks)
                        additional = min(1, len(matching_tracks), limit - len(selected))
                        selected.extend(matching_tracks[:additional])
                        print(f"   + {artist_name}: +{additional} adicional(es)")
            
            # Aleatorizar el orden final para mezclar mejor
            random.shuffle(selected)
            
            print(f"✅ Seleccionadas {len(selected)} canciones con distribución equitativa")
            return selected[:limit]
        
        else:
            # No hay artistas específicos: selección por diversidad general
            print(f"🎲 Selección diversificada sin artistas específicos")
            
            # Calcular máximo de canciones por artista (evitar que un artista domine)
            max_per_artist = max(2, limit // max(5, len(tracks_by_artist) // 3))
            
            selected = []
            artist_usage = defaultdict(int)
            
            # Crear lista de todos los artistas disponibles
            available_artists = list(tracks_by_artist.keys())
            random.shuffle(available_artists)
            
            # Iterar round-robin por los artistas
            round_num = 0
            while len(selected) < limit and round_num < 10:  # Max 10 rondas para evitar loop infinito
                added_this_round = False
                
                for artist_key in available_artists:
                    if len(selected) >= limit:
                        break
                    
                    # Verificar si este artista aún puede aportar canciones
                    if artist_usage[artist_key] < max_per_artist:
                        artist_tracks = tracks_by_artist[artist_key]
                        
                        # Buscar una canción que no hayamos usado
                        for track in artist_tracks:
                            if track not in selected:
                                selected.append(track)
                                artist_usage[artist_key] += 1
                                added_this_round = True
                                break
                
                if not added_this_round:
                    # No se agregó nada en esta ronda, salir del loop
                    break
                
                round_num += 1
            
            # Aleatorizar el orden final
            random.shuffle(selected)
            
            # Mostrar estadísticas
            artists_used = len([count for count in artist_usage.values() if count > 0])
            print(f"✅ Seleccionadas {len(selected)} canciones de {artists_used} artistas diferentes")
            print(f"   Promedio: {len(selected)/artists_used:.1f} canciones por artista")
            
            return selected[:limit]
    
    def _ai_filter_tracks(
        self,
        tracks: List[Track],
        description: str,
        target_count: int
    ) -> List[Track]:
        """Usar IA para filtrar canciones relevantes basándose en la descripción
        
        Args:
            tracks: Lista completa de canciones
            description: Descripción de lo que se busca
            target_count: Número aproximado de canciones a mantener
            
        Returns:
            Lista filtrada de canciones más relevantes
        """
        import random
        
        try:
            # Limitar a un máximo razonable para la IA
            sample_size = min(len(tracks), 100)
            sampled_tracks = random.sample(tracks, sample_size) if len(tracks) > sample_size else tracks
            
            # Formatear para la IA
            tracks_text = ""
            for i, track in enumerate(sampled_tracks):
                genre_text = f" [{track.genre}]" if track.genre else ""
                year_text = f" ({track.year})" if track.year else ""
                tracks_text += f"{i}. {track.artist} - {track.title}{genre_text}{year_text}\n"
            
            prompt = f"""Analiza esta lista de canciones y selecciona las que mejor coincidan con: "{description}"

Canciones disponibles:
{tracks_text}

INSTRUCCIONES:
1. Selecciona las {min(target_count, sample_size)} canciones que MEJOR se ajusten a la descripción
2. Considera género, estilo, idioma, época según la descripción
3. Prioriza DIVERSIDAD de artistas (máximo 2-3 canciones por artista)
4. Responde SOLO con los números separados por comas
5. Ejemplo: 1,5,8,12,15,20,23,27,30,35,40,42,45,48,50

Selecciona ahora (máximo {min(target_count, sample_size)} canciones):"""

            response = self.model.generate_content(prompt)
            selected_indices = self._parse_selection(response.text)
            
            # Construir lista de canciones seleccionadas
            filtered = []
            for idx in selected_indices:
                if idx < len(sampled_tracks):
                    filtered.append(sampled_tracks[idx])
            
            # Si quedaron muy pocas, agregar más aleatorias
            if len(filtered) < target_count // 2:
                remaining = [t for t in tracks if t not in filtered]
                additional_needed = min(target_count - len(filtered), len(remaining))
                filtered.extend(random.sample(remaining, additional_needed))
            
            return filtered
            
        except Exception as e:
            print(f"⚠️ Error en filtrado por IA: {e}")
            # Fallback: devolver muestra aleatoria
            return random.sample(tracks, min(target_count, len(tracks)))
    
    def _extract_artist_names(self, text: str) -> List[str]:
        """Extraer nombres de artistas de una descripción
        
        Detecta nombres de artistas en formatos como:
        - "música de mujeres, vera fauna y cala vento"
        - "playlist con Pink Floyd, Queen y The Beatles"
        - "canciones de Extremoduro"
        
        Args:
            text: Texto con posibles nombres de artistas
            
        Returns:
            Lista de nombres de artistas detectados
        """
        import re
        
        artists = []
        
        # Palabras que indican que lo siguiente es un artista
        artist_indicators = ['de', 'con', 'música de', 'canciones de', 'temas de']
        
        # ESTRATEGIA 1: Detectar listas separadas por comas
        # "mujeres, vera fauna y cala vento" → ["mujeres", "vera fauna", "cala vento"]
        # Buscar patrones después de palabras indicadoras
        for indicator in artist_indicators:
            pattern = rf'{indicator}\s+(.+?)(?:\s+para|\s+de\s+los|\.|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                artists_text = match.group(1)
                # Dividir por comas, "y", "&"
                parts = re.split(r',|\s+y\s+|\s+&\s+', artists_text)
                for part in parts:
                    # Limpiar espacios
                    part = part.strip()
                    # Remover palabras comunes al inicio/final
                    part = re.sub(r'^(la|el|los|las|un|una)\s+', '', part, flags=re.IGNORECASE)
                    part = re.sub(r'\s+(para|con|de)$', '', part, flags=re.IGNORECASE)
                    if part and len(part) > 2:
                        artists.append(part)
        
        # ESTRATEGIA 2: Detectar nombres propios (palabras con mayúscula)
        # Solo si no se encontraron artistas por la estrategia 1
        if not artists:
            # Buscar secuencias de palabras que empiezan con mayúscula
            capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            cap_matches = re.findall(capitalized_pattern, text)
            
            # Filtrar palabras comunes que suelen ir con mayúscula
            common_words = {'Playlist', 'Lista', 'Música', 'Canciones', 'Album', 'Disco'}
            for match in cap_matches:
                if match not in common_words and len(match) > 2:
                    artists.append(match)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_artists = []
        for artist in artists:
            artist_lower = artist.lower()
            if artist_lower not in seen:
                seen.add(artist_lower)
                unique_artists.append(artist)
        
        if unique_artists:
            print(f"🎤 Nombres de artistas extraídos: {unique_artists}")
        
        return unique_artists
    
    def _extract_song_count(self, text: str) -> Optional[int]:
        """Extraer cantidad de canciones solicitada en la descripción
        
        Detecta formatos como:
        - "20 canciones"
        - "15 temas"
        - "10 tracks"
        - "playlist de 25 canciones"
        
        Args:
            text: Texto de la descripción
            
        Returns:
            Número de canciones solicitadas, o None si no se especifica
        """
        import re
        
        # Patrones para detectar cantidad de canciones
        patterns = [
            r'(\d+)\s*(?:canciones|cancion|temas|tema|tracks|track|songs|song)',
            r'(?:de|con)\s*(\d+)\s*(?:canciones|cancion|temas|tema|tracks|track)',
            r'playlist\s*(?:de|con)?\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                # Validar que sea un número razonable (entre 5 y 200)
                if 5 <= count <= 200:
                    print(f"🔢 Cantidad detectada: {count} canciones")
                    return count
        
        return None
    
    def _extract_genres(self, text: str) -> List[str]:
        """Extraer géneros musicales de la descripción
        
        Args:
            text: Texto de la descripción
            
        Returns:
            Lista de géneros musicales detectados
        """
        text_lower = text.lower()
        
        # Diccionario de géneros comunes y sus variaciones
        genre_patterns = {
            'rock': ['rock', 'rocanrol'],
            'indie': ['indie', 'independiente'],
            'pop': ['pop'],
            'jazz': ['jazz'],
            'blues': ['blues'],
            'metal': ['metal', 'heavy metal'],
            'punk': ['punk'],
            'folk': ['folk', 'folclore'],
            'electronic': ['electronica', 'electrónica', 'electronic', 'electro'],
            'hip hop': ['hip hop', 'hiphop', 'rap'],
            'reggae': ['reggae'],
            'country': ['country'],
            'classical': ['clasica', 'clásica', 'classical'],
            'alternative': ['alternativo', 'alternativa', 'alternative'],
            'ska': ['ska'],
            'soul': ['soul'],
            'funk': ['funk'],
            'disco': ['disco'],
            'grunge': ['grunge'],
            'progressive': ['progresivo', 'progresiva', 'progressive', 'prog'],
            'flamenco': ['flamenco'],
            'latin': ['latina', 'latino', 'latin'],
            'salsa': ['salsa'],
            'rumba': ['rumba'],
            'indie rock': ['indie rock'],
            'indie pop': ['indie pop'],
        }
        
        detected_genres = []
        
        for genre, patterns in genre_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    detected_genres.append(genre)
                    break  # Solo agregar una vez por género
        
        # Eliminar duplicados manteniendo orden
        unique_genres = []
        seen = set()
        for genre in detected_genres:
            if genre not in seen:
                unique_genres.append(genre)
                seen.add(genre)
        
        return unique_genres
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extraer palabras clave de una descripción
        
        Args:
            text: Texto del que extraer keywords
            
        Returns:
            Lista de palabras clave
        """
        import re
        
        # Remover palabras comunes (stop words en español)
        stop_words = {
            'de', 'la', 'el', 'para', 'con', 'los', 'las', 'un', 'una',
            'del', 'al', 'y', 'o', 'en', 'a', 'por', 'que', 'es', 'su',
            'música', 'canciones', 'canción', 'playlist', 'lista', 'haz', 'hacer'
        }
        
        # Extraer palabras
        words = re.findall(r'\w+', text.lower())
        
        # Filtrar stop words y palabras muy cortas
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Limitar a las primeras 5 palabras clave más relevantes
        return keywords[:5]
    
    def _format_tracks_for_ai(self, tracks: List[Track]) -> str:
        """Formatear tracks para que la IA los pueda leer y seleccionar
        
        Args:
            tracks: Lista de tracks
            
        Returns:
            String formateado con la lista de tracks
        """
        formatted = ""
        for i, track in enumerate(tracks):
            formatted += f"{i}. {track.artist} - {track.title}"
            if track.album:
                formatted += f" (Álbum: {track.album})"
            if track.genre:
                formatted += f" [Género: {track.genre}]"
            if track.year:
                formatted += f" ({track.year})"
            formatted += "\n"
        return formatted
    
    def _parse_selection(self, text: str) -> List[int]:
        """Parsear la selección de índices de la IA
        
        Args:
            text: Texto de respuesta de la IA
            
        Returns:
            Lista de índices seleccionados
        """
        import re
        
        # Buscar todos los números en el texto
        numbers = re.findall(r'\d+', text)
        
        # Convertir a enteros
        indices = [int(n) for n in numbers if int(n) < 1000]  # Filtrar números muy grandes
        
        return indices