"""
Motor de recomendaciones híbridas que combina múltiples estrategias
para generar recomendaciones más precisas y personalizadas
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict

from models.schemas import UserProfile, Recommendation, Track
from services.adaptive_learning_system import adaptive_learning_system
from services.cache_manager import cached
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ai_service import MusicRecommendationService

logger = logging.getLogger(__name__)


class RecommendationStrategy(Enum):
    """Estrategias de recomendación disponibles"""
    COLLABORATIVE = "collaborative"  # Basada en usuarios similares
    CONTENT_BASED = "content_based"  # Basada en contenido musical
    HYBRID = "hybrid"  # Combinación de múltiples estrategias
    POPULARITY = "popularity"  # Basada en popularidad
    RECENCY = "recency"  # Basada en novedad
    DIVERSITY = "diversity"  # Basada en diversidad


@dataclass
class RecommendationScore:
    """Puntuación de una recomendación con metadatos"""
    track: Track
    score: float
    strategy: RecommendationStrategy
    confidence: float
    reasoning: str
    metadata: Dict[str, Any] = None


@dataclass
class UserSimilarity:
    """Similitud entre usuarios"""
    user_id: int
    similarity_score: float
    common_artists: List[str]
    common_genres: List[str]
    shared_tracks: int


class CollaborativeFiltering:
    """Filtrado colaborativo para encontrar usuarios similares"""
    
    def __init__(self):
        self.user_profiles: Dict[int, Dict[str, Any]] = {}
        self.user_similarities: Dict[Tuple[int, int], float] = {}
    
    def update_user_profile(self, user_id: int, profile_data: Dict[str, Any]):
        """Actualizar perfil de usuario para filtrado colaborativo"""
        self.user_profiles[user_id] = {
            'artists': profile_data.get('artists', []),
            'genres': profile_data.get('genres', []),
            'tracks': profile_data.get('tracks', []),
            'last_updated': datetime.now()
        }
    
    def calculate_user_similarity(self, user1_id: int, user2_id: int) -> Optional[UserSimilarity]:
        """Calcular similitud entre dos usuarios"""
        if user1_id not in self.user_profiles or user2_id not in self.user_profiles:
            return None
        
        profile1 = self.user_profiles[user1_id]
        profile2 = self.user_profiles[user2_id]
        
        # Calcular similitud de artistas (Jaccard)
        artists1 = set(profile1.get('artists', []))
        artists2 = set(profile2.get('artists', []))
        artist_intersection = artists1.intersection(artists2)
        artist_union = artists1.union(artists2)
        artist_similarity = len(artist_intersection) / len(artist_union) if artist_union else 0
        
        # Calcular similitud de géneros
        genres1 = set(profile1.get('genres', []))
        genres2 = set(profile2.get('genres', []))
        genre_intersection = genres1.intersection(genres2)
        genre_union = genres1.union(genres2)
        genre_similarity = len(genre_intersection) / len(genre_union) if genre_union else 0
        
        # Calcular similitud de tracks
        tracks1 = set(profile1.get('tracks', []))
        tracks2 = set(profile2.get('tracks', []))
        track_intersection = tracks1.intersection(tracks2)
        track_union = tracks1.union(tracks2)
        track_similarity = len(track_intersection) / len(track_union) if track_union else 0
        
        # Similitud combinada (peso: artistas 50%, géneros 30%, tracks 20%)
        combined_similarity = (
            artist_similarity * 0.5 + 
            genre_similarity * 0.3 + 
            track_similarity * 0.2
        )
        
        return UserSimilarity(
            user_id=user2_id,
            similarity_score=combined_similarity,
            common_artists=list(artist_intersection),
            common_genres=list(genre_intersection),
            shared_tracks=len(track_intersection)
        )
    
    def find_similar_users(self, user_id: int, min_similarity: float = 0.3) -> List[UserSimilarity]:
        """Encontrar usuarios similares"""
        similar_users = []
        
        for other_user_id in self.user_profiles:
            if other_user_id == user_id:
                continue
            
            similarity = self.calculate_user_similarity(user_id, other_user_id)
            if similarity and similarity.similarity_score >= min_similarity:
                similar_users.append(similarity)
        
        # Ordenar por similitud descendente
        similar_users.sort(key=lambda x: x.similarity_score, reverse=True)
        return similar_users[:10]  # Top 10 usuarios similares


class ContentBasedFiltering:
    """Filtrado basado en contenido musical"""
    
    def __init__(self):
        self.track_features: Dict[str, Dict[str, Any]] = {}
        self.genre_weights: Dict[str, float] = {}
        self.artist_weights: Dict[str, float] = {}
    
    def extract_track_features(self, track: Track) -> Dict[str, Any]:
        """Extraer características de una canción"""
        features = {
            'artist': track.artist.lower() if track.artist else '',
            'title': track.title.lower() if track.title else '',
            'genre': getattr(track, 'genre', '').lower(),
            'year': getattr(track, 'year', 0),
            'duration': getattr(track, 'duration', 0),
            'album': getattr(track, 'album', '').lower()
        }
        return features
    
    def calculate_content_similarity(self, track1: Track, track2: Track) -> float:
        """Calcular similitud basada en contenido"""
        features1 = self.extract_track_features(track1)
        features2 = self.extract_track_features(track2)
        
        similarity_score = 0.0
        
        # Similitud de artista (peso: 40%)
        if features1['artist'] and features2['artist']:
            if features1['artist'] == features2['artist']:
                similarity_score += 0.4
            elif features1['artist'] in features2['artist'] or features2['artist'] in features1['artist']:
                similarity_score += 0.2
        
        # Similitud de género (peso: 30%)
        if features1['genre'] and features2['genre']:
            if features1['genre'] == features2['genre']:
                similarity_score += 0.3
            elif features1['genre'] in features2['genre'] or features2['genre'] in features1['genre']:
                similarity_score += 0.15
        
        # Similitud de año (peso: 20%)
        if features1['year'] and features2['year']:
            year_diff = abs(features1['year'] - features2['year'])
            if year_diff <= 2:
                similarity_score += 0.2
            elif year_diff <= 5:
                similarity_score += 0.1
        
        # Similitud de duración (peso: 10%)
        if features1['duration'] and features2['duration']:
            duration_diff = abs(features1['duration'] - features2['duration'])
            max_duration = max(features1['duration'], features2['duration'])
            if max_duration > 0:
                duration_similarity = 1 - (duration_diff / max_duration)
                similarity_score += duration_similarity * 0.1
        
        return min(similarity_score, 1.0)
    
    def find_similar_tracks(self, reference_track: Track, candidate_tracks: List[Track], 
                          top_k: int = 10) -> List[Tuple[Track, float]]:
        """Encontrar tracks similares basados en contenido"""
        similarities = []
        
        for track in candidate_tracks:
            similarity = self.calculate_content_similarity(reference_track, track)
            if similarity > 0.1:  # Umbral mínimo de similitud
                similarities.append((track, similarity))
        
        # Ordenar por similitud descendente
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


class DiversityEngine:
    """Motor de diversidad para evitar recomendaciones repetitivas"""
    
    def __init__(self):
        self.diversity_weights = {
            'artist_diversity': 0.4,
            'genre_diversity': 0.3,
            'year_diversity': 0.2,
            'album_diversity': 0.1
        }
    
    def calculate_diversity_score(self, recommendations: List[RecommendationScore]) -> float:
        """Calcular score de diversidad de un conjunto de recomendaciones"""
        if len(recommendations) <= 1:
            return 1.0
        
        diversity_scores = {}
        
        # Diversidad de artistas
        artists = [rec.track.artist for rec in recommendations if rec.track.artist]
        unique_artists = len(set(artists))
        diversity_scores['artist_diversity'] = unique_artists / len(artists) if artists else 0
        
        # Diversidad de géneros
        genres = [getattr(rec.track, 'genre', '') for rec in recommendations]
        genres = [g for g in genres if g]
        unique_genres = len(set(genres))
        diversity_scores['genre_diversity'] = unique_genres / len(genres) if genres else 0
        
        # Diversidad de años
        years = [getattr(rec.track, 'year', 0) for rec in recommendations]
        years = [y for y in years if y > 0]
        if years:
            year_range = max(years) - min(years)
            diversity_scores['year_diversity'] = min(year_range / 50, 1.0)  # Normalizar a 50 años
        else:
            diversity_scores['year_diversity'] = 0
        
        # Diversidad de álbumes
        albums = [getattr(rec.track, 'album', '') for rec in recommendations]
        albums = [a for a in albums if a]
        unique_albums = len(set(albums))
        diversity_scores['album_diversity'] = unique_albums / len(albums) if albums else 0
        
        # Calcular score combinado
        total_score = sum(
            diversity_scores[key] * weight 
            for key, weight in self.diversity_weights.items()
        )
        
        return total_score
    
    def optimize_diversity(self, recommendations: List[RecommendationScore], 
                          target_count: int = 10) -> List[RecommendationScore]:
        """Optimizar diversidad seleccionando el mejor conjunto de recomendaciones"""
        if len(recommendations) <= target_count:
            return recommendations
        
        # Algoritmo greedy para maximizar diversidad
        selected = []
        remaining = recommendations.copy()
        
        # Seleccionar la primera recomendación (la mejor)
        if remaining:
            selected.append(remaining.pop(0))
        
        # Iterativamente seleccionar la que maximice diversidad
        while len(selected) < target_count and remaining:
            best_candidate = None
            best_diversity = -1
            
            for candidate in remaining:
                temp_selected = selected + [candidate]
                diversity = self.calculate_diversity_score(temp_selected)
                
                if diversity > best_diversity:
                    best_diversity = diversity
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break
        
        return selected


class HybridRecommendationEngine:
    """Motor principal de recomendaciones híbridas"""
    
    def __init__(self, ai_service: "MusicRecommendationService"):
        self.ai_service = ai_service
        self.collaborative_filtering = CollaborativeFiltering()
        self.content_based_filtering = ContentBasedFiltering()
        self.diversity_engine = DiversityEngine()
        
        # Configuración de pesos por estrategia
        self.strategy_weights = {
            RecommendationStrategy.COLLABORATIVE: 0.3,
            RecommendationStrategy.CONTENT_BASED: 0.25,
            RecommendationStrategy.POPULARITY: 0.2,
            RecommendationStrategy.RECENCY: 0.15,
            RecommendationStrategy.DIVERSITY: 0.1
        }
        
        logger.info("✅ HybridRecommendationEngine inicializado")
    
    async def generate_hybrid_recommendations(
        self, 
        user_profile: UserProfile,
        user_id: int,
        max_recommendations: int = 20,
        strategy_preferences: Optional[Dict[RecommendationStrategy, float]] = None
    ) -> List[RecommendationScore]:
        """Generar recomendaciones híbridas combinando múltiples estrategias"""
        
        try:
            logger.info(f"🎯 Generando recomendaciones híbridas para usuario {user_id}")
            
            # Obtener preferencias de estrategia personalizadas
            effective_weights = strategy_preferences or self.strategy_weights
            
            # Generar recomendaciones con cada estrategia
            all_recommendations = []
            
            # 1. Recomendaciones colaborativas
            if effective_weights.get(RecommendationStrategy.COLLABORATIVE, 0) > 0:
                collab_recs = await self._generate_collaborative_recommendations(
                    user_profile, user_id, max_recommendations
                )
                all_recommendations.extend(collab_recs)
            
            # 2. Recomendaciones basadas en contenido
            if effective_weights.get(RecommendationStrategy.CONTENT_BASED, 0) > 0:
                content_recs = await self._generate_content_based_recommendations(
                    user_profile, user_id, max_recommendations
                )
                all_recommendations.extend(content_recs)
            
            # 3. Recomendaciones de popularidad
            if effective_weights.get(RecommendationStrategy.POPULARITY, 0) > 0:
                popularity_recs = await self._generate_popularity_recommendations(
                    user_profile, user_id, max_recommendations
                )
                all_recommendations.extend(popularity_recs)
            
            # 4. Recomendaciones de novedad
            if effective_weights.get(RecommendationStrategy.RECENCY, 0) > 0:
                recency_recs = await self._generate_recency_recommendations(
                    user_profile, user_id, max_recommendations
                )
                all_recommendations.extend(recency_recs)
            
            # 5. Aplicar pesos de estrategia
            weighted_recommendations = self._apply_strategy_weights(
                all_recommendations, effective_weights
            )
            
            # 6. Aplicar pesos de aprendizaje adaptativo
            personalized_recommendations = await self._apply_adaptive_weights(
                weighted_recommendations, user_id
            )
            
            # 7. Optimizar diversidad
            diverse_recommendations = self.diversity_engine.optimize_diversity(
                personalized_recommendations, max_recommendations
            )
            
            # 8. Ordenar por score final
            diverse_recommendations.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"✅ Generadas {len(diverse_recommendations)} recomendaciones híbridas")
            return diverse_recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones híbridas: {e}")
            # Fallback a recomendaciones básicas
            return await self._generate_fallback_recommendations(user_profile, user_id, max_recommendations)
    
    async def _generate_collaborative_recommendations(
        self, user_profile: UserProfile, user_id: int, max_recommendations: int
    ) -> List[RecommendationScore]:
        """Generar recomendaciones colaborativas"""
        try:
            # Actualizar perfil para filtrado colaborativo
            profile_data = {
                'artists': [artist.name for artist in user_profile.top_artists],
                'genres': list(user_profile.preferred_genres),
                'tracks': [track.title for track in user_profile.recent_tracks]
            }
            self.collaborative_filtering.update_user_profile(user_id, profile_data)
            
            # Encontrar usuarios similares
            similar_users = self.collaborative_filtering.find_similar_users(user_id)
            
            if not similar_users:
                return []
            
            # Obtener tracks de usuarios similares (simulado)
            # En un caso real, esto vendría de una base de datos
            collaborative_tracks = []
            
            for similar_user in similar_users[:3]:  # Top 3 usuarios similares
                # Simular obtención de tracks del usuario similar
                # En implementación real, esto vendría de la base de datos
                pass
            
            return collaborative_tracks
            
        except Exception as e:
            logger.warning(f"⚠️ Error en recomendaciones colaborativas: {e}")
            return []
    
    async def _generate_content_based_recommendations(
        self, user_profile: UserProfile, user_id: int, max_recommendations: int
    ) -> List[RecommendationScore]:
        """Generar recomendaciones basadas en contenido"""
        try:
            # Obtener tracks de referencia del usuario
            reference_tracks = user_profile.recent_tracks[:5]  # Top 5 tracks recientes
            
            if not reference_tracks:
                return []
            
            # Obtener candidatos de la biblioteca (simulado)
            # En implementación real, esto vendría de Navidrome
            candidate_tracks = []
            
            content_recommendations = []
            for ref_track in reference_tracks:
                similar_tracks = self.content_based_filtering.find_similar_tracks(
                    ref_track, candidate_tracks, top_k=5
                )
                
                for track, similarity in similar_tracks:
                    content_recommendations.append(RecommendationScore(
                        track=track,
                        score=similarity,
                        strategy=RecommendationStrategy.CONTENT_BASED,
                        confidence=similarity,
                        reasoning=f"Similar a '{ref_track.title}' por contenido",
                        metadata={'reference_track': ref_track.title}
                    ))
            
            return content_recommendations
            
        except Exception as e:
            logger.warning(f"⚠️ Error en recomendaciones basadas en contenido: {e}")
            return []
    
    async def _generate_popularity_recommendations(
        self, user_profile: UserProfile, user_id: int, max_recommendations: int
    ) -> List[RecommendationScore]:
        """Generar recomendaciones basadas en popularidad"""
        try:
            # Simular tracks populares
            # En implementación real, esto vendría de estadísticas globales
            popular_tracks = []
            
            popularity_recommendations = []
            for track in popular_tracks:
                popularity_recommendations.append(RecommendationScore(
                    track=track,
                    score=0.7,  # Score base de popularidad
                    strategy=RecommendationStrategy.POPULARITY,
                    confidence=0.6,
                    reasoning="Track popular en la comunidad",
                    metadata={'popularity_rank': 1}
                ))
            
            return popularity_recommendations
            
        except Exception as e:
            logger.warning(f"⚠️ Error en recomendaciones de popularidad: {e}")
            return []
    
    async def _generate_recency_recommendations(
        self, user_profile: UserProfile, user_id: int, max_recommendations: int
    ) -> List[RecommendationScore]:
        """Generar recomendaciones basadas en novedad"""
        try:
            # Simular tracks recientes
            # En implementación real, esto vendría de lanzamientos recientes
            recent_tracks = []
            
            recency_recommendations = []
            for track in recent_tracks:
                recency_recommendations.append(RecommendationScore(
                    track=track,
                    score=0.8,  # Score base de novedad
                    strategy=RecommendationStrategy.RECENCY,
                    confidence=0.7,
                    reasoning="Lanzamiento reciente",
                    metadata={'release_date': '2024'}
                ))
            
            return recency_recommendations
            
        except Exception as e:
            logger.warning(f"⚠️ Error en recomendaciones de novedad: {e}")
            return []
    
    def _apply_strategy_weights(
        self, 
        recommendations: List[RecommendationScore], 
        weights: Dict[RecommendationStrategy, float]
    ) -> List[RecommendationScore]:
        """Aplicar pesos de estrategia a las recomendaciones"""
        for rec in recommendations:
            strategy_weight = weights.get(rec.strategy, 1.0)
            rec.score *= strategy_weight
            rec.metadata = rec.metadata or {}
            rec.metadata['strategy_weight'] = strategy_weight
        
        return recommendations
    
    async def _apply_adaptive_weights(
        self, 
        recommendations: List[RecommendationScore], 
        user_id: int
    ) -> List[RecommendationScore]:
        """Aplicar pesos de aprendizaje adaptativo"""
        try:
            # Obtener pesos personalizados del sistema de aprendizaje
            adaptive_weights = adaptive_learning_system.get_recommendation_weights(user_id, {})
            
            if not adaptive_weights:
                return recommendations
            
            for rec in recommendations:
                # Aplicar pesos adaptativos basados en características de la track
                adaptive_score = 0.0
                
                if rec.track.artist and 'artist' in adaptive_weights:
                    adaptive_score += adaptive_weights['artist']
                
                if hasattr(rec.track, 'genre') and 'genre' in adaptive_weights:
                    adaptive_score += adaptive_weights['genre']
                
                # Ajustar score con peso adaptativo
                if adaptive_score > 0:
                    rec.score *= (1 + adaptive_score * 0.3)  # Boost del 30% máximo
                    rec.metadata = rec.metadata or {}
                    rec.metadata['adaptive_boost'] = adaptive_score
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"⚠️ Error aplicando pesos adaptativos: {e}")
            return recommendations
    
    async def _generate_fallback_recommendations(
        self, user_profile: UserProfile, user_id: int, max_recommendations: int
    ) -> List[RecommendationScore]:
        """Generar recomendaciones de fallback usando el servicio AI existente"""
        try:
            # Usar el servicio AI existente como fallback
            ai_recommendations = await self.ai_service.generate_recommendations(user_profile)
            
            fallback_scores = []
            for rec in ai_recommendations:
                fallback_scores.append(RecommendationScore(
                    track=rec.track,
                    score=rec.confidence,
                    strategy=RecommendationStrategy.HYBRID,
                    confidence=rec.confidence,
                    reasoning="Recomendación de fallback",
                    metadata={'fallback': True}
                ))
            
            return fallback_scores[:max_recommendations]
            
        except Exception as e:
            logger.error(f"❌ Error en recomendaciones de fallback: {e}")
            return []
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del motor híbrido"""
        return {
            'collaborative_users': len(self.collaborative_filtering.user_profiles),
            'content_features': len(self.content_based_filtering.track_features),
            'strategy_weights': self.strategy_weights,
            'diversity_weights': self.diversity_engine.diversity_weights
        }
