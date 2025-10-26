"""
Sistema de aprendizaje adaptativo para mejorar recomendaciones
basado en feedback del usuario
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Tipos de feedback del usuario"""
    LIKE = "like"
    DISLIKE = "dislike"
    SKIP = "skip"
    PLAY = "play"
    SHARE = "share"
    SAVE = "save"


class InteractionOutcome(Enum):
    """Resultados de interacciones"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class UserFeedback:
    """Feedback del usuario sobre una recomendación"""
    user_id: int
    recommendation_id: str
    feedback_type: str
    timestamp: datetime
    context: Dict[str, Any]  # Contexto de la recomendación
    rating: Optional[float] = None  # Rating numérico opcional (1-5)
    comment: Optional[str] = None  # Comentario opcional del usuario


@dataclass
class UserPreference:
    """Preferencia aprendida del usuario"""
    user_id: int
    feature: str  # Género, artista, mood, etc.
    value: str    # Valor específico de la característica
    weight: float  # Peso de la preferencia (0-1)
    confidence: float  # Confianza en la preferencia (0-1)
    last_updated: datetime
    interaction_count: int = 0


@dataclass
class LearningPattern:
    """Patrón de aprendizaje detectado"""
    user_id: int
    pattern_type: str  # 'genre_preference', 'time_preference', 'mood_preference', etc.
    pattern_data: Dict[str, Any]
    confidence: float
    last_seen: datetime
    frequency: int = 1


class PreferenceLearner:
    """Aprendiz de preferencias del usuario"""
    
    def __init__(self):
        self.preferences_file = Path("/app/logs/user_preferences.json")
        self.preferences: Dict[int, List[UserPreference]] = {}
        self.learning_rate = 0.1
        self.decay_rate = 0.01  # Decaimiento de preferencias no utilizadas
        
        # Cargar preferencias existentes
        self._load_preferences()
    
    def _load_preferences(self):
        """Cargar preferencias desde archivo"""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id_str, prefs_data in data.items():
                        user_id = int(user_id_str)
                        self.preferences[user_id] = []
                        for pref_data in prefs_data:
                            pref = UserPreference(
                                user_id=pref_data['user_id'],
                                feature=pref_data['feature'],
                                value=pref_data['value'],
                                weight=pref_data['weight'],
                                confidence=pref_data['confidence'],
                                last_updated=datetime.fromisoformat(pref_data['last_updated']),
                                interaction_count=pref_data.get('interaction_count', 0)
                            )
                            self.preferences[user_id].append(pref)
                logger.info(f"✅ Cargadas preferencias para {len(self.preferences)} usuarios")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando preferencias: {e}")
            self.preferences = {}
    
    def _save_preferences(self):
        """Guardar preferencias en archivo"""
        try:
            # Crear directorio si no existe
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convertir a formato serializable
            data = {}
            for user_id, prefs in self.preferences.items():
                data[str(user_id)] = [asdict(pref) for pref in prefs]
            
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"💾 Preferencias guardadas para {len(self.preferences)} usuarios")
        except Exception as e:
            logger.error(f"❌ Error guardando preferencias: {e}")
    
    def update_preference(
        self, 
        user_id: int, 
        feature: str, 
        value: str, 
        feedback_type: str,
        context: Dict[str, Any] = None
    ):
        """Actualizar preferencia del usuario basada en feedback"""
        
        if user_id not in self.preferences:
            self.preferences[user_id] = []
        
        # Buscar preferencia existente
        existing_pref = None
        for pref in self.preferences[user_id]:
            if pref.feature == feature and pref.value == value:
                existing_pref = pref
                break
        
        # Calcular ajuste de peso basado en feedback
        if feedback_type == FeedbackType.LIKE.value:
            weight_adjustment = self.learning_rate
            confidence_adjustment = 0.05
        elif feedback_type == FeedbackType.DISLIKE.value:
            weight_adjustment = -self.learning_rate
            confidence_adjustment = 0.05
        elif feedback_type == FeedbackType.SKIP.value:
            weight_adjustment = -self.learning_rate * 0.5
            confidence_adjustment = 0.02
        else:
            weight_adjustment = 0
            confidence_adjustment = 0
        
        if existing_pref:
            # Actualizar preferencia existente
            existing_pref.weight = max(0, min(1, existing_pref.weight + weight_adjustment))
            existing_pref.confidence = max(0, min(1, existing_pref.confidence + confidence_adjustment))
            existing_pref.last_updated = datetime.now()
            existing_pref.interaction_count += 1
        else:
            # Crear nueva preferencia
            initial_weight = 0.5 + weight_adjustment
            initial_confidence = 0.3 + confidence_adjustment
            
            new_pref = UserPreference(
                user_id=user_id,
                feature=feature,
                value=value,
                weight=max(0, min(1, initial_weight)),
                confidence=max(0, min(1, initial_confidence)),
                last_updated=datetime.now(),
                interaction_count=1
            )
            self.preferences[user_id].append(new_pref)
        
        # Aplicar decaimiento a preferencias no utilizadas
        self._apply_decay(user_id)
        
        # Guardar cambios
        self._save_preferences()
        
        logger.debug(f"📚 Preferencia actualizada: {user_id} - {feature}:{value} = {weight_adjustment:+.3f}")
    
    def _apply_decay(self, user_id: int):
        """Aplicar decaimiento a preferencias no utilizadas"""
        current_time = datetime.now()
        
        for pref in self.preferences.get(user_id, []):
            days_since_update = (current_time - pref.last_updated).days
            
            if days_since_update > 7:  # Solo aplicar decaimiento después de una semana
                decay_factor = 1 - (self.decay_rate * days_since_update / 30)
                pref.weight = max(0, pref.weight * decay_factor)
                pref.confidence = max(0, pref.confidence * decay_factor)
    
    def get_user_preferences(self, user_id: int) -> Dict[str, List[Tuple[str, float]]]:
        """Obtener preferencias del usuario agrupadas por característica"""
        if user_id not in self.preferences:
            return {}
        
        grouped_prefs = {}
        for pref in self.preferences[user_id]:
            if pref.feature not in grouped_prefs:
                grouped_prefs[pref.feature] = []
            
            # Solo incluir preferencias con peso significativo
            if pref.weight > 0.1:
                grouped_prefs[pref.feature].append((pref.value, pref.weight))
        
        # Ordenar por peso descendente
        for feature in grouped_prefs:
            grouped_prefs[feature].sort(key=lambda x: x[1], reverse=True)
        
        return grouped_prefs
    
    def get_preference_score(self, user_id: int, feature: str, value: str) -> float:
        """Obtener puntuación de preferencia para una característica específica"""
        if user_id not in self.preferences:
            return 0.0
        
        for pref in self.preferences[user_id]:
            if pref.feature == feature and pref.value == value:
                return pref.weight * pref.confidence
        
        return 0.0


class PatternDetector:
    """Detector de patrones de comportamiento del usuario"""
    
    def __init__(self):
        self.patterns_file = Path("/app/logs/learning_patterns.json")
        self.patterns: Dict[int, List[LearningPattern]] = {}
        self._load_patterns()
    
    def _load_patterns(self):
        """Cargar patrones desde archivo"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id_str, patterns_data in data.items():
                        user_id = int(user_id_str)
                        self.patterns[user_id] = []
                        for pattern_data in patterns_data:
                            pattern = LearningPattern(
                                user_id=pattern_data['user_id'],
                                pattern_type=pattern_data['pattern_type'],
                                pattern_data=pattern_data['pattern_data'],
                                confidence=pattern_data['confidence'],
                                last_seen=datetime.fromisoformat(pattern_data['last_seen']),
                                frequency=pattern_data.get('frequency', 1)
                            )
                            self.patterns[user_id].append(pattern)
                logger.info(f"✅ Cargados patrones para {len(self.patterns)} usuarios")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando patrones: {e}")
            self.patterns = {}
    
    def _save_patterns(self):
        """Guardar patrones en archivo"""
        try:
            self.patterns_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for user_id, patterns in self.patterns.items():
                data[str(user_id)] = [asdict(pattern) for pattern in patterns]
            
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ Error guardando patrones: {e}")
    
    def detect_patterns(self, user_id: int, interactions: List[Dict[str, Any]]) -> List[LearningPattern]:
        """Detectar patrones en las interacciones del usuario"""
        if user_id not in self.patterns:
            self.patterns[user_id] = []
        
        new_patterns = []
        
        # Detectar patrón de preferencias de género
        genre_pattern = self._detect_genre_preference_pattern(user_id, interactions)
        if genre_pattern:
            new_patterns.append(genre_pattern)
        
        # Detectar patrón de horarios de escucha
        time_pattern = self._detect_time_preference_pattern(user_id, interactions)
        if time_pattern:
            new_patterns.append(time_pattern)
        
        # Detectar patrón de estados de ánimo
        mood_pattern = self._detect_mood_preference_pattern(user_id, interactions)
        if mood_pattern:
            new_patterns.append(mood_pattern)
        
        # Actualizar patrones existentes o agregar nuevos
        for pattern in new_patterns:
            self._update_or_add_pattern(user_id, pattern)
        
        self._save_patterns()
        return new_patterns
    
    def _detect_genre_preference_pattern(self, user_id: int, interactions: List[Dict[str, Any]]) -> Optional[LearningPattern]:
        """Detectar patrón de preferencias de género"""
        genre_feedback = {}
        
        for interaction in interactions:
            if interaction.get('feedback_type') in [FeedbackType.LIKE.value, FeedbackType.DISLIKE.value]:
                context = interaction.get('context', {})
                genres = context.get('genres', [])
                
                for genre in genres:
                    if genre not in genre_feedback:
                        genre_feedback[genre] = {'likes': 0, 'dislikes': 0}
                    
                    if interaction['feedback_type'] == FeedbackType.LIKE.value:
                        genre_feedback[genre]['likes'] += 1
                    else:
                        genre_feedback[genre]['dislikes'] += 1
        
        # Calcular preferencias de género
        genre_preferences = {}
        for genre, feedback in genre_feedback.items():
            total = feedback['likes'] + feedback['dislikes']
            if total >= 3:  # Mínimo de interacciones para detectar patrón
                preference_score = feedback['likes'] / total
                if preference_score > 0.7 or preference_score < 0.3:
                    genre_preferences[genre] = preference_score
        
        if genre_preferences:
            return LearningPattern(
                user_id=user_id,
                pattern_type='genre_preference',
                pattern_data=genre_preferences,
                confidence=min(len(genre_preferences) / 5, 1.0),
                last_seen=datetime.now(),
                frequency=1
            )
        
        return None
    
    def _detect_time_preference_pattern(self, user_id: int, interactions: List[Dict[str, Any]]) -> Optional[LearningPattern]:
        """Detectar patrón de horarios de escucha"""
        hour_feedback = {}
        
        for interaction in interactions:
            timestamp = datetime.fromisoformat(interaction.get('timestamp', datetime.now().isoformat()))
            hour = timestamp.hour
            
            if hour not in hour_feedback:
                hour_feedback[hour] = {'likes': 0, 'dislikes': 0}
            
            if interaction.get('feedback_type') == FeedbackType.LIKE.value:
                hour_feedback[hour]['likes'] += 1
            elif interaction.get('feedback_type') == FeedbackType.DISLIKE.value:
                hour_feedback[hour]['dislikes'] += 1
        
        # Encontrar horas con mayor actividad positiva
        active_hours = []
        for hour, feedback in hour_feedback.items():
            total = feedback['likes'] + feedback['dislikes']
            if total >= 2:
                positive_ratio = feedback['likes'] / total
                if positive_ratio > 0.6:
                    active_hours.append(hour)
        
        if len(active_hours) >= 2:
            return LearningPattern(
                user_id=user_id,
                pattern_type='time_preference',
                pattern_data={'active_hours': sorted(active_hours)},
                confidence=min(len(active_hours) / 8, 1.0),
                last_seen=datetime.now(),
                frequency=1
            )
        
        return None
    
    def _detect_mood_preference_pattern(self, user_id: int, interactions: List[Dict[str, Any]]) -> Optional[LearningPattern]:
        """Detectar patrón de preferencias de estado de ánimo"""
        mood_feedback = {}
        
        for interaction in interactions:
            context = interaction.get('context', {})
            mood = context.get('mood')
            
            if mood:
                if mood not in mood_feedback:
                    mood_feedback[mood] = {'likes': 0, 'dislikes': 0}
                
                if interaction.get('feedback_type') == FeedbackType.LIKE.value:
                    mood_feedback[mood]['likes'] += 1
                elif interaction.get('feedback_type') == FeedbackType.DISLIKE.value:
                    mood_feedback[mood]['dislikes'] += 1
        
        # Calcular preferencias de mood
        mood_preferences = {}
        for mood, feedback in mood_feedback.items():
            total = feedback['likes'] + feedback['dislikes']
            if total >= 2:
                preference_score = feedback['likes'] / total
                if preference_score > 0.7 or preference_score < 0.3:
                    mood_preferences[mood] = preference_score
        
        if mood_preferences:
            return LearningPattern(
                user_id=user_id,
                pattern_type='mood_preference',
                pattern_data=mood_preferences,
                confidence=min(len(mood_preferences) / 3, 1.0),
                last_seen=datetime.now(),
                frequency=1
            )
        
        return None
    
    def _update_or_add_pattern(self, user_id: int, new_pattern: LearningPattern):
        """Actualizar patrón existente o agregar nuevo"""
        for i, existing_pattern in enumerate(self.patterns[user_id]):
            if (existing_pattern.pattern_type == new_pattern.pattern_type and 
                existing_pattern.user_id == new_pattern.user_id):
                
                # Actualizar patrón existente
                existing_pattern.pattern_data.update(new_pattern.pattern_data)
                existing_pattern.confidence = max(existing_pattern.confidence, new_pattern.confidence)
                existing_pattern.last_seen = new_pattern.last_seen
                existing_pattern.frequency += 1
                return
        
        # Agregar nuevo patrón
        self.patterns[user_id].append(new_pattern)
    
    def get_user_patterns(self, user_id: int) -> List[LearningPattern]:
        """Obtener patrones del usuario"""
        return self.patterns.get(user_id, [])


class AdaptiveLearningSystem:
    """Sistema principal de aprendizaje adaptativo"""
    
    def __init__(self):
        self.preference_learner = PreferenceLearner()
        self.pattern_detector = PatternDetector()
        self.feedback_history: List[UserFeedback] = []
        self.learning_enabled = os.getenv("ENABLE_ADAPTIVE_LEARNING", "true").lower() == "true"
        
        if self.learning_enabled:
            logger.info("✅ Sistema de aprendizaje adaptativo habilitado")
        else:
            logger.info("⚠️ Sistema de aprendizaje adaptativo deshabilitado")
    
    async def process_feedback(
        self, 
        user_id: int, 
        recommendation_id: str, 
        feedback_type: str,
        context: Dict[str, Any] = None,
        rating: Optional[float] = None,
        comment: Optional[str] = None
    ):
        """Procesar feedback del usuario"""
        if not self.learning_enabled:
            return
        
        try:
            # Crear registro de feedback
            feedback = UserFeedback(
                user_id=user_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                timestamp=datetime.now(),
                context=context or {},
                rating=rating,
                comment=comment
            )
            
            # Agregar a historial
            self.feedback_history.append(feedback)
            
            # Mantener solo últimos 1000 feedbacks
            if len(self.feedback_history) > 1000:
                self.feedback_history = self.feedback_history[-1000:]
            
            # Actualizar preferencias basadas en feedback
            self._update_preferences_from_feedback(feedback)
            
            # Detectar patrones si hay suficientes interacciones
            user_interactions = [f for f in self.feedback_history if f.user_id == user_id]
            if len(user_interactions) >= 5:
                self.pattern_detector.detect_patterns(user_id, [
                    {
                        'feedback_type': f.feedback_type,
                        'timestamp': f.timestamp.isoformat(),
                        'context': f.context
                    }
                    for f in user_interactions[-20:]  # Últimas 20 interacciones
                ])
            
            logger.debug(f"📚 Feedback procesado: {user_id} - {feedback_type} - {recommendation_id}")
            
        except Exception as e:
            logger.error(f"❌ Error procesando feedback: {e}")
    
    def _update_preferences_from_feedback(self, feedback: UserFeedback):
        """Actualizar preferencias basadas en feedback"""
        context = feedback.context
        
        # Actualizar preferencias de género
        if 'genres' in context:
            for genre in context['genres']:
                self.preference_learner.update_preference(
                    feedback.user_id,
                    'genre',
                    genre,
                    feedback.feedback_type,
                    context
                )
        
        # Actualizar preferencias de artista
        if 'artist' in context:
            self.preference_learner.update_preference(
                feedback.user_id,
                'artist',
                context['artist'],
                feedback.feedback_type,
                context
            )
        
        # Actualizar preferencias de mood
        if 'mood' in context:
            self.preference_learner.update_preference(
                feedback.user_id,
                'mood',
                context['mood'],
                feedback.feedback_type,
                context
            )
        
        # Actualizar preferencias de actividad
        if 'activity' in context:
            self.preference_learner.update_preference(
                feedback.user_id,
                'activity',
                context['activity'],
                feedback.feedback_type,
                context
            )
    
    def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Obtener insights del usuario basados en aprendizaje"""
        preferences = self.preference_learner.get_user_preferences(user_id)
        patterns = self.pattern_detector.get_user_patterns(user_id)
        
        # Calcular score de personalización
        personalization_score = self._calculate_personalization_score(user_id)
        
        # Generar recomendaciones de mejora
        improvement_suggestions = self._generate_improvement_suggestions(user_id, preferences, patterns)
        
        return {
            'user_id': user_id,
            'preferences': preferences,
            'patterns': [
                {
                    'type': p.pattern_type,
                    'data': p.pattern_data,
                    'confidence': p.confidence,
                    'frequency': p.frequency
                }
                for p in patterns
            ],
            'personalization_score': personalization_score,
            'improvement_suggestions': improvement_suggestions,
            'total_feedback': len([f for f in self.feedback_history if f.user_id == user_id]),
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_personalization_score(self, user_id: int) -> float:
        """Calcular score de personalización del usuario"""
        preferences = self.preference_learner.get_user_preferences(user_id)
        patterns = self.pattern_detector.get_user_patterns(user_id)
        
        # Score basado en número de preferencias
        preference_score = min(len(preferences) / 10, 1.0)
        
        # Score basado en patrones detectados
        pattern_score = min(len(patterns) / 5, 1.0)
        
        # Score basado en confianza promedio de preferencias
        if preferences:
            total_confidence = 0
            total_prefs = 0
            for feature_prefs in preferences.values():
                for _, weight in feature_prefs:
                    total_confidence += weight
                    total_prefs += 1
            
            confidence_score = total_confidence / total_prefs if total_prefs > 0 else 0
        else:
            confidence_score = 0
        
        # Combinar scores
        return (preference_score * 0.4 + pattern_score * 0.3 + confidence_score * 0.3)
    
    def _generate_improvement_suggestions(self, user_id: int, preferences: Dict, patterns: List) -> List[str]:
        """Generar sugerencias de mejora para el usuario"""
        suggestions = []
        
        # Sugerencias basadas en preferencias
        if not preferences:
            suggestions.append("Interactúa más con las recomendaciones para mejorar la personalización")
        elif len(preferences) < 3:
            suggestions.append("Explora diferentes géneros para diversificar tus preferencias")
        
        # Sugerencias basadas en patrones
        if not patterns:
            suggestions.append("Usa el bot regularmente para detectar patrones de escucha")
        
        # Sugerencias específicas
        if 'genre' in preferences:
            top_genres = preferences['genre'][:3]
            if len(top_genres) == 1:
                suggestions.append(f"Considera explorar géneros similares a {top_genres[0][0]}")
        
        return suggestions
    
    def get_recommendation_weights(self, user_id: int, features: Dict[str, Any]) -> Dict[str, float]:
        """Obtener pesos de recomendación basados en preferencias del usuario"""
        weights = {}
        
        # Peso por género
        if 'genres' in features:
            genre_weights = []
            for genre in features['genres']:
                weight = self.preference_learner.get_preference_score(user_id, 'genre', genre)
                genre_weights.append(weight)
            
            if genre_weights:
                weights['genre'] = max(genre_weights)
        
        # Peso por artista
        if 'artist' in features:
            weights['artist'] = self.preference_learner.get_preference_score(user_id, 'artist', features['artist'])
        
        # Peso por mood
        if 'mood' in features:
            weights['mood'] = self.preference_learner.get_preference_score(user_id, 'mood', features['mood'])
        
        # Peso por actividad
        if 'activity' in features:
            weights['activity'] = self.preference_learner.get_preference_score(user_id, 'activity', features['activity'])
        
        return weights


# Instancia global del sistema de aprendizaje adaptativo
adaptive_learning_system = AdaptiveLearningSystem()
