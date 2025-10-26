"""
Sistema de personalización avanzada que combina múltiples fuentes
de datos para crear perfiles de usuario detallados
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import numpy as np
from collections import defaultdict, Counter
import math

from models.schemas import UserProfile, Track, ScrobbleTrack, ScrobbleArtist
from services.adaptive_learning_system import adaptive_learning_system
from services.cache_manager import cached
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ai_service import MusicRecommendationService

logger = logging.getLogger(__name__)


class PersonalityTrait(Enum):
    """Rasgos de personalidad musical"""
    EXPLORER = "explorer"  # Disfruta descubrir música nueva
    MAINSTREAM = "mainstream"  # Prefiere música popular
    NOSTALGIC = "nostalgic"  # Prefiere música clásica/retro
    DIVERSE = "diverse"  # Escucha una gran variedad de géneros
    FOCUSED = "focused"  # Se enfoca en pocos géneros/artistas
    SOCIAL = "social"  # Influenciado por tendencias sociales
    INDEPENDENT = "independent"  # Prefiere música independiente/underground


class ListeningPattern(Enum):
    """Patrones de escucha"""
    MORNING_PERSON = "morning_person"  # Escucha más en la mañana
    NIGHT_OWL = "night_owl"  # Escucha más en la noche
    WEEKEND_WARRIOR = "weekend_warrior"  # Escucha más los fines de semana
    CONSISTENT = "consistent"  # Patrón de escucha consistente
    BURST = "burst"  # Escucha en ráfagas intensas
    STEADY = "steady"  # Escucha constante y moderada


@dataclass
class UserPersonality:
    """Perfil de personalidad musical del usuario"""
    user_id: int
    traits: Dict[PersonalityTrait, float]  # Rasgos con scores 0-1
    listening_patterns: Dict[ListeningPattern, float]
    music_preferences: Dict[str, Any]
    discovery_rate: float  # Qué tan abierto está a nueva música
    social_influence: float  # Qué tan influenciado por tendencias
    last_updated: datetime


@dataclass
class ContextualPreference:
    """Preferencia contextual del usuario"""
    user_id: int
    context: str  # 'work', 'exercise', 'relax', 'party', etc.
    preferred_genres: List[str]
    preferred_artists: List[str]
    preferred_moods: List[str]
    confidence: float
    sample_size: int


class PersonalityAnalyzer:
    """Analizador de personalidad musical"""
    
    def __init__(self):
        self.trait_indicators = {
            PersonalityTrait.EXPLORER: {
                'genres': ['experimental', 'indie', 'alternative', 'electronic'],
                'artists': ['unknown', 'new', 'emerging'],
                'patterns': ['high_discovery_rate', 'genre_diversity']
            },
            PersonalityTrait.MAINSTREAM: {
                'genres': ['pop', 'hip hop', 'rock', 'country'],
                'artists': ['popular', 'chart_topping'],
                'patterns': ['low_discovery_rate', 'high_popularity']
            },
            PersonalityTrait.NOSTALGIC: {
                'genres': ['classic rock', 'jazz', 'blues', 'oldies'],
                'artists': ['vintage', 'classic'],
                'patterns': ['older_music_preference', 'low_recency']
            },
            PersonalityTrait.DIVERSE: {
                'genres': ['multiple_genres'],
                'artists': ['varied'],
                'patterns': ['high_genre_diversity', 'low_artist_concentration']
            },
            PersonalityTrait.FOCUSED: {
                'genres': ['few_genres'],
                'artists': ['concentrated'],
                'patterns': ['low_genre_diversity', 'high_artist_concentration']
            },
            PersonalityTrait.SOCIAL: {
                'genres': ['trending'],
                'artists': ['viral', 'trending'],
                'patterns': ['high_recency', 'trend_following']
            },
            PersonalityTrait.INDEPENDENT: {
                'genres': ['indie', 'alternative', 'underground'],
                'artists': ['independent', 'unsigned'],
                'patterns': ['low_mainstream', 'high_indie_content']
            }
        }
    
    def analyze_personality(self, user_profile: UserProfile, user_id: int) -> UserPersonality:
        """Analizar personalidad musical del usuario"""
        traits = {}
        
        # Analizar cada rasgo
        for trait, indicators in self.trait_indicators.items():
            trait_score = self._calculate_trait_score(user_profile, indicators)
            traits[trait] = trait_score
        
        # Analizar patrones de escucha
        listening_patterns = self._analyze_listening_patterns(user_profile)
        
        # Calcular preferencias musicales
        music_preferences = self._extract_music_preferences(user_profile)
        
        # Calcular tasa de descubrimiento
        discovery_rate = self._calculate_discovery_rate(user_profile)
        
        # Calcular influencia social
        social_influence = self._calculate_social_influence(user_profile)
        
        return UserPersonality(
            user_id=user_id,
            traits=traits,
            listening_patterns=listening_patterns,
            music_preferences=music_preferences,
            discovery_rate=discovery_rate,
            social_influence=social_influence,
            last_updated=datetime.now()
        )
    
    def _calculate_trait_score(self, user_profile: UserProfile, indicators: Dict[str, List[str]]) -> float:
        """Calcular score para un rasgo específico"""
        score = 0.0
        total_indicators = 0
        
        # Analizar géneros
        if 'genres' in indicators:
            user_genres = [g.lower() for g in user_profile.preferred_genres]
            matching_genres = sum(1 for indicator in indicators['genres'] 
                                if any(indicator in genre for genre in user_genres))
            score += matching_genres / len(indicators['genres'])
            total_indicators += 1
        
        # Analizar patrones
        if 'patterns' in indicators:
            pattern_score = self._analyze_patterns(user_profile, indicators['patterns'])
            score += pattern_score
            total_indicators += 1
        
        return score / total_indicators if total_indicators > 0 else 0.0
    
    def _analyze_patterns(self, user_profile: UserProfile, patterns: List[str]) -> float:
        """Analizar patrones específicos"""
        score = 0.0
        
        for pattern in patterns:
            if pattern == 'high_discovery_rate':
                discovery_rate = self._calculate_discovery_rate(user_profile)
                score += discovery_rate
            elif pattern == 'genre_diversity':
                diversity = len(user_profile.preferred_genres) / 10  # Normalizar
                score += min(diversity, 1.0)
            elif pattern == 'low_discovery_rate':
                discovery_rate = self._calculate_discovery_rate(user_profile)
                score += 1 - discovery_rate
            elif pattern == 'high_popularity':
                # Simular análisis de popularidad
                score += 0.5  # Placeholder
            elif pattern == 'older_music_preference':
                # Analizar edad promedio de la música escuchada
                score += 0.3  # Placeholder
            elif pattern == 'high_recency':
                # Analizar qué tan reciente es la música escuchada
                score += 0.4  # Placeholder
        
        return score / len(patterns) if patterns else 0.0
    
    def _analyze_listening_patterns(self, user_profile: UserProfile) -> Dict[ListeningPattern, float]:
        """Analizar patrones temporales de escucha"""
        patterns = {}
        
        # Analizar patrones de tiempo (simulado)
        # En implementación real, esto vendría de datos de escucha temporal
        patterns[ListeningPattern.MORNING_PERSON] = 0.3
        patterns[ListeningPattern.NIGHT_OWL] = 0.7
        patterns[ListeningPattern.WEEKEND_WARRIOR] = 0.4
        patterns[ListeningPattern.CONSISTENT] = 0.6
        patterns[ListeningPattern.BURST] = 0.2
        patterns[ListeningPattern.STEADY] = 0.8
        
        return patterns
    
    def _extract_music_preferences(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Extraer preferencias musicales detalladas"""
        return {
            'top_genres': list(user_profile.preferred_genres),
            'top_artists': [artist.name for artist in user_profile.top_artists],
            'genre_diversity': len(user_profile.preferred_genres),
            'artist_diversity': len(user_profile.top_artists),
            'avg_track_duration': self._calculate_avg_duration(user_profile),
            'preferred_languages': self._extract_languages(user_profile)
        }
    
    def _calculate_discovery_rate(self, user_profile: UserProfile) -> float:
        """Calcular tasa de descubrimiento de nueva música"""
        if not user_profile.recent_tracks:
            return 0.0
        
        # Simular cálculo de tasa de descubrimiento
        # En implementación real, esto analizaría la novedad de las tracks
        return 0.4  # Placeholder
    
    def _calculate_social_influence(self, user_profile: UserProfile) -> float:
        """Calcular influencia social en las preferencias"""
        # Simular análisis de influencia social
        # En implementación real, esto analizaría tendencias y popularidad
        return 0.3  # Placeholder
    
    def _calculate_avg_duration(self, user_profile: UserProfile) -> float:
        """Calcular duración promedio de tracks escuchadas"""
        if not user_profile.recent_tracks:
            return 0.0
        
        durations = [getattr(track, 'duration', 0) for track in user_profile.recent_tracks]
        durations = [d for d in durations if d > 0]
        
        return sum(durations) / len(durations) if durations else 0.0
    
    def _extract_languages(self, user_profile: UserProfile) -> List[str]:
        """Extraer idiomas preferidos de la música"""
        # Simular extracción de idiomas
        # En implementación real, esto analizaría los metadatos de las tracks
        return ['español', 'inglés']


class ContextualPreferenceEngine:
    """Motor de preferencias contextuales"""
    
    def __init__(self):
        self.contextual_preferences: Dict[int, List[ContextualPreference]] = {}
        self.context_patterns = {
            'work': ['instrumental', 'ambient', 'classical', 'jazz'],
            'exercise': ['electronic', 'rock', 'hip hop', 'pop'],
            'relax': ['ambient', 'classical', 'jazz', 'acoustic'],
            'party': ['electronic', 'pop', 'hip hop', 'dance'],
            'study': ['instrumental', 'ambient', 'classical'],
            'drive': ['rock', 'pop', 'country', 'classic rock'],
            'sleep': ['ambient', 'classical', 'instrumental']
        }
    
    def analyze_contextual_preferences(
        self, 
        user_profile: UserProfile, 
        user_id: int,
        context_data: Optional[Dict[str, Any]] = None
    ) -> List[ContextualPreference]:
        """Analizar preferencias contextuales del usuario"""
        
        if user_id not in self.contextual_preferences:
            self.contextual_preferences[user_id] = []
        
        # Analizar cada contexto
        contextual_prefs = []
        
        for context, typical_genres in self.context_patterns.items():
            # Simular análisis de preferencias por contexto
            # En implementación real, esto analizaría datos de escucha por contexto
            
            # Obtener géneros preferidos del usuario para este contexto
            user_genres = self._get_user_genres_for_context(user_profile, context)
            
            if user_genres:
                contextual_prefs.append(ContextualPreference(
                    user_id=user_id,
                    context=context,
                    preferred_genres=user_genres,
                    preferred_artists=[],  # Placeholder
                    preferred_moods=[],  # Placeholder
                    confidence=0.6,  # Placeholder
                    sample_size=10  # Placeholder
                ))
        
        # Actualizar preferencias del usuario
        self.contextual_preferences[user_id] = contextual_prefs
        
        return contextual_prefs
    
    def _get_user_genres_for_context(
        self, 
        user_profile: UserProfile, 
        context: str
    ) -> List[str]:
        """Obtener géneros preferidos del usuario para un contexto específico"""
        # Simular selección de géneros basada en contexto
        # En implementación real, esto analizaría patrones de escucha contextual
        
        user_genres = list(user_profile.preferred_genres)
        context_genres = self.context_patterns.get(context, [])
        
        # Encontrar intersección entre géneros del usuario y típicos del contexto
        matching_genres = [g for g in user_genres if g.lower() in [cg.lower() for cg in context_genres]]
        
        return matching_genres[:3]  # Top 3 géneros para el contexto
    
    def get_contextual_recommendations(
        self, 
        user_id: int, 
        context: str,
        available_tracks: List[Track]
    ) -> List[Track]:
        """Obtener recomendaciones contextuales"""
        
        if user_id not in self.contextual_preferences:
            return []
        
        # Encontrar preferencias para el contexto
        context_prefs = None
        for pref in self.contextual_preferences[user_id]:
            if pref.context == context:
                context_prefs = pref
                break
        
        if not context_prefs:
            return []
        
        # Filtrar tracks por géneros preferidos del contexto
        recommended_tracks = []
        for track in available_tracks:
            track_genre = getattr(track, 'genre', '').lower()
            if any(pref_genre.lower() in track_genre for pref_genre in context_prefs.preferred_genres):
                recommended_tracks.append(track)
        
        return recommended_tracks[:10]  # Top 10 recomendaciones contextuales


class AdvancedPersonalizationSystem:
    """Sistema principal de personalización avanzada"""
    
    def __init__(self):
        self.personality_analyzer = PersonalityAnalyzer()
        self.contextual_engine = ContextualPreferenceEngine()
        self.user_personalities: Dict[int, UserPersonality] = {}
        
        logger.info("✅ AdvancedPersonalizationSystem inicializado")
    
    async def analyze_user_profile(
        self, 
        user_profile: UserProfile, 
        user_id: int,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analizar perfil completo del usuario"""
        
        try:
            logger.info(f"🧠 Analizando perfil avanzado para usuario {user_id}")
            
            # 1. Análisis de personalidad
            personality = self.personality_analyzer.analyze_personality(user_profile, user_id)
            self.user_personalities[user_id] = personality
            
            # 2. Análisis contextual
            contextual_prefs = self.contextual_engine.analyze_contextual_preferences(
                user_profile, user_id, context_data
            )
            
            # 3. Obtener insights de aprendizaje adaptativo
            learning_insights = adaptive_learning_system.get_user_insights(user_id)
            
            # 4. Combinar todos los análisis
            advanced_profile = {
                'user_id': user_id,
                'personality': {
                    'traits': {trait.value: score for trait, score in personality.traits.items()},
                    'listening_patterns': {pattern.value: score for pattern, score in personality.listening_patterns.items()},
                    'discovery_rate': personality.discovery_rate,
                    'social_influence': personality.social_influence
                },
                'contextual_preferences': [
                    {
                        'context': pref.context,
                        'preferred_genres': pref.preferred_genres,
                        'confidence': pref.confidence
                    }
                    for pref in contextual_prefs
                ],
                'learning_insights': learning_insights,
                'music_preferences': personality.music_preferences,
                'last_updated': personality.last_updated.isoformat()
            }
            
            logger.info(f"✅ Perfil avanzado analizado para usuario {user_id}")
            return advanced_profile
            
        except Exception as e:
            logger.error(f"❌ Error analizando perfil avanzado: {e}")
            return {'error': str(e)}
    
    def get_personality_traits(self, user_id: int) -> Dict[str, float]:
        """Obtener rasgos de personalidad del usuario"""
        if user_id not in self.user_personalities:
            return {}
        
        personality = self.user_personalities[user_id]
        return {trait.value: score for trait, score in personality.traits.items()}
    
    def get_contextual_recommendations(
        self, 
        user_id: int, 
        context: str,
        available_tracks: List[Track]
    ) -> List[Track]:
        """Obtener recomendaciones contextuales"""
        return self.contextual_engine.get_contextual_recommendations(
            user_id, context, available_tracks
        )
    
    def get_personalization_score(self, user_id: int) -> float:
        """Calcular score de personalización del usuario"""
        if user_id not in self.user_personalities:
            return 0.0
        
        personality = self.user_personalities[user_id]
        
        # Calcular score basado en:
        # 1. Diversidad de rasgos de personalidad
        trait_diversity = len([t for t in personality.traits.values() if t > 0.3])
        
        # 2. Fuerza de patrones de escucha
        pattern_strength = max(personality.listening_patterns.values()) if personality.listening_patterns else 0
        
        # 3. Tasa de descubrimiento
        discovery_score = personality.discovery_rate
        
        # 4. Preferencias contextuales
        contextual_score = len(self.contextual_engine.contextual_preferences.get(user_id, [])) / 7  # 7 contextos posibles
        
        # Combinar scores
        personalization_score = (
            trait_diversity * 0.3 +
            pattern_strength * 0.3 +
            discovery_score * 0.2 +
            contextual_score * 0.2
        )
        
        return min(personalization_score, 1.0)
    
    def get_recommendation_weights(self, user_id: int, context: Optional[str] = None) -> Dict[str, float]:
        """Obtener pesos de recomendación basados en personalización avanzada"""
        
        if user_id not in self.user_personalities:
            return {}
        
        personality = self.user_personalities[user_id]
        weights = {}
        
        # Pesos basados en rasgos de personalidad
        if personality.traits.get(PersonalityTrait.EXPLORER, 0) > 0.5:
            weights['novelty'] = 0.8
            weights['diversity'] = 0.7
        
        if personality.traits.get(PersonalityTrait.MAINSTREAM, 0) > 0.5:
            weights['popularity'] = 0.8
            weights['trending'] = 0.6
        
        if personality.traits.get(PersonalityTrait.NOSTALGIC, 0) > 0.5:
            weights['classic'] = 0.8
            weights['vintage'] = 0.7
        
        if personality.traits.get(PersonalityTrait.DIVERSE, 0) > 0.5:
            weights['genre_diversity'] = 0.9
            weights['artist_diversity'] = 0.8
        
        # Pesos basados en contexto
        if context:
            contextual_prefs = self.contextual_engine.contextual_preferences.get(user_id, [])
            for pref in contextual_prefs:
                if pref.context == context:
                    weights['contextual_match'] = pref.confidence
                    break
        
        # Pesos basados en patrones de escucha
        if personality.listening_patterns.get(ListeningPattern.MORNING_PERSON, 0) > 0.5:
            weights['morning_energy'] = 0.6
        
        if personality.listening_patterns.get(ListeningPattern.NIGHT_OWL, 0) > 0.5:
            weights['evening_mood'] = 0.6
        
        return weights
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema de personalización"""
        return {
            'total_users_analyzed': len(self.user_personalities),
            'contextual_preferences': sum(len(prefs) for prefs in self.contextual_engine.contextual_preferences.values()),
            'avg_personalization_score': np.mean([
                self.get_personalization_score(user_id) 
                for user_id in self.user_personalities.keys()
            ]) if self.user_personalities else 0.0
        }


# Instancia global del sistema de personalización avanzada
advanced_personalization_system = AdvancedPersonalizationSystem()
