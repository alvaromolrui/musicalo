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
