import google.generativeai as genai
import os
from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter
import re
from models.schemas import UserProfile, Recommendation, Track, LastFMTrack, LastFMArtist, MusicAnalysis
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.lastfm_service import LastFMService

class MusicRecommendationService:
    def __init__(self):
        # Configurar Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
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
    
    async def generate_recommendations(self, user_profile: UserProfile, limit: int = 10, include_new_music: bool = True) -> List[Recommendation]:
        """Generar recomendaciones basadas en el perfil del usuario
        
        Args:
            user_profile: Perfil del usuario con sus gustos
            limit: Número de recomendaciones a generar
            include_new_music: Si True, incluye música que no está en la biblioteca (usando Last.fm)
        """
        try:
            print(f"🎯 Generando {limit} recomendaciones...")
            
            # Analizar perfil del usuario
            analysis = await self.analyze_user_profile(user_profile)
            
            recommendations = []
            
            # Si Last.fm está habilitado y se solicita música nueva, usarlo
            if include_new_music and self.lastfm and len(user_profile.top_artists) > 0:
                print("🌍 Buscando música nueva usando Last.fm...")
                new_music_recs = await self._generate_lastfm_recommendations(user_profile, limit)
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
    
    async def _generate_lastfm_recommendations(self, user_profile: UserProfile, limit: int) -> List[Recommendation]:
        """Generar recomendaciones usando Last.fm (música nueva que no tienes)"""
        try:
            recommendations = []
            processed_artists = set()
            
            print(f"🔍 Generando recomendaciones de Last.fm para {len(user_profile.top_artists[:5])} artistas")
            
            # Obtener artistas similares basados en los top artistas del usuario
            for top_artist in user_profile.top_artists[:5]:  # Usar los top 5 artistas
                if len(recommendations) >= limit:
                    break
                
                print(f"🎤 Buscando artistas similares a: {top_artist.name}")
                # Obtener artistas similares
                similar_artists = await self.lastfm.get_similar_artists(top_artist.name, limit=5)
                print(f"   Encontrados {len(similar_artists)} artistas similares")
                
                for similar_artist in similar_artists:
                    if len(recommendations) >= limit:
                        break
                    
                    if similar_artist.name in processed_artists:
                        continue
                    
                    processed_artists.add(similar_artist.name)
                    
                    # Crear recomendación del artista similar
                    print(f"   ➕ Agregando recomendación: {similar_artist.name}")
                    recommendation = Recommendation(
                        track_id=f"lastfm_artist_{similar_artist.name.replace(' ', '_')}",
                        title=f"Descubre música de {similar_artist.name}",
                        artist=similar_artist.name,
                        album="",
                        score=0.85,  # Score alto para música nueva
                        reason=f"🌟 Artista similar a {top_artist.name} que te puede gustar",
                        source="Last.fm",
                        genre="",
                        year=None
                    )
                    recommendations.append(recommendation)
            
            print(f"✅ Total de recomendaciones de Last.fm: {len(recommendations)}")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generando recomendaciones de Last.fm: {e}")
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
