"""
Sistema de características adicionales para usuarios
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import os
import random
import hashlib

from models.schemas import UserProfile, Track, Recommendation
from services.cache_manager import cached

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Tipos de características de usuario"""
    MUSIC_DISCOVERY = "music_discovery"
    SOCIAL_FEATURES = "social_features"
    PERSONALIZATION = "personalization"
    GAMIFICATION = "gamification"
    ANALYTICS = "analytics"


class AchievementType(Enum):
    """Tipos de logros"""
    LISTENING_STREAK = "listening_streak"
    GENRE_EXPLORER = "genre_explorer"
    ARTIST_DISCOVERER = "artist_discoverer"
    PLAYLIST_CREATOR = "playlist_creator"
    SOCIAL_USER = "social_user"
    POWER_USER = "power_user"


@dataclass
class UserAchievement:
    """Logro de usuario"""
    achievement_id: str
    user_id: int
    achievement_type: AchievementType
    title: str
    description: str
    earned_at: datetime
    points: int
    rarity: str  # common, rare, epic, legendary


@dataclass
class UserStreak:
    """Racha de usuario"""
    user_id: int
    streak_type: str
    current_streak: int
    longest_streak: int
    last_activity: datetime
    streak_start: datetime


@dataclass
class UserStats:
    """Estadísticas del usuario"""
    user_id: int
    total_listens: int
    unique_artists: int
    unique_genres: int
    playlists_created: int
    recommendations_given: int
    recommendations_liked: int
    days_active: int
    last_activity: datetime
    level: int
    experience_points: int


class MusicDiscoveryEngine:
    """Motor de descubrimiento musical avanzado"""
    
    def __init__(self):
        self.discovery_algorithms = {
            'similar_artists': self._discover_similar_artists,
            'genre_exploration': self._discover_genre_exploration,
            'temporal_discovery': self._discover_temporal_patterns,
            'collaborative_discovery': self._discover_collaborative,
            'serendipity': self._discover_serendipity
        }
    
    async def discover_new_music(self, user_profile: UserProfile, user_id: int, 
                               discovery_type: str = 'mixed') -> List[Recommendation]:
        """Descubrir nueva música para el usuario"""
        try:
            recommendations = []
            
            if discovery_type == 'mixed':
                # Usar múltiples algoritmos
                for algo_name, algo_func in self.discovery_algorithms.items():
                    try:
                        algo_recs = await algo_func(user_profile, user_id)
                        recommendations.extend(algo_recs)
                    except Exception as e:
                        logger.warning(f"⚠️ Error en algoritmo {algo_name}: {e}")
            else:
                # Usar algoritmo específico
                if discovery_type in self.discovery_algorithms:
                    recommendations = await self.discovery_algorithms[discovery_type](user_profile, user_id)
            
            # Mezclar y limitar resultados
            random.shuffle(recommendations)
            return recommendations[:10]
            
        except Exception as e:
            logger.error(f"❌ Error en descubrimiento musical: {e}")
            return []
    
    async def _discover_similar_artists(self, user_profile: UserProfile, user_id: int) -> List[Recommendation]:
        """Descubrir artistas similares a los favoritos"""
        # Simular descubrimiento de artistas similares
        # En implementación real, esto usaría APIs de música
        recommendations = []
        
        for artist in user_profile.top_artists[:3]:
            # Simular artistas similares
            similar_artists = [
                f"Similar to {artist.name}",
                f"Inspired by {artist.name}",
                f"Like {artist.name}"
            ]
            
            for similar_name in similar_artists:
                track = Track(
                    id=f"discovery_{hash(similar_name) % 10000}",
                    title=f"Discovery Track",
                    artist=similar_name,
                    album="Discovery Album"
                )
                
                recommendation = Recommendation(
                    track=track,
                    confidence=0.7,
                    reasoning=f"Similar to your favorite artist {artist.name}",
                    tags=["discovery", "similar_artists"]
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    async def _discover_genre_exploration(self, user_profile: UserProfile, user_id: int) -> List[Recommendation]:
        """Descubrir géneros relacionados"""
        recommendations = []
        
        # Simular exploración de géneros
        genre_expansions = {
            'rock': ['alternative rock', 'progressive rock', 'indie rock'],
            'pop': ['indie pop', 'electropop', 'synthpop'],
            'electronic': ['ambient', 'techno', 'house'],
            'jazz': ['fusion', 'smooth jazz', 'bebop']
        }
        
        for genre in user_profile.preferred_genres:
            if genre.lower() in genre_expansions:
                for related_genre in genre_expansions[genre.lower()]:
                    track = Track(
                        id=f"genre_{hash(related_genre) % 10000}",
                        title=f"{related_genre} Discovery",
                        artist=f"{related_genre} Artist",
                        album=f"{related_genre} Collection"
                    )
                    
                    recommendation = Recommendation(
                        track=track,
                        confidence=0.6,
                        reasoning=f"Explore {related_genre} related to {genre}",
                        tags=["discovery", "genre_exploration", related_genre]
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    async def _discover_temporal_patterns(self, user_profile: UserProfile, user_id: int) -> List[Recommendation]:
        """Descubrir basado en patrones temporales"""
        # Simular descubrimiento basado en horarios de escucha
        current_hour = datetime.now().hour
        
        time_based_genres = {
            'morning': ['ambient', 'classical', 'acoustic'],
            'afternoon': ['pop', 'indie', 'alternative'],
            'evening': ['rock', 'electronic', 'jazz'],
            'night': ['ambient', 'chill', 'lounge']
        }
        
        time_period = 'morning' if 6 <= current_hour < 12 else \
                     'afternoon' if 12 <= current_hour < 18 else \
                     'evening' if 18 <= current_hour < 22 else 'night'
        
        recommendations = []
        for genre in time_based_genres.get(time_period, []):
            track = Track(
                id=f"time_{hash(genre) % 10000}",
                title=f"{time_period.title()} {genre}",
                artist=f"{time_period.title()} Artist",
                album=f"{time_period.title()} Vibes"
            )
            
            recommendation = Recommendation(
                track=track,
                confidence=0.5,
                reasoning=f"Perfect for {time_period} listening",
                tags=["discovery", "temporal", time_period, genre]
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    async def _discover_collaborative(self, user_profile: UserProfile, user_id: int) -> List[Recommendation]:
        """Descubrimiento colaborativo"""
        # Simular recomendaciones basadas en usuarios similares
        recommendations = []
        
        # Simular usuarios similares
        similar_users = [
            "User with similar taste",
            "Music lover like you",
            "Compatible listener"
        ]
        
        for user in similar_users:
            track = Track(
                id=f"collab_{hash(user) % 10000}",
                title=f"Liked by {user}",
                artist="Community Favorite",
                album="Trending Now"
            )
            
            recommendation = Recommendation(
                track=track,
                confidence=0.6,
                reasoning=f"Liked by users with similar taste",
                tags=["discovery", "collaborative", "community"]
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    async def _discover_serendipity(self, user_profile: UserProfile, user_id: int) -> List[Recommendation]:
        """Descubrimiento por serendipidad (sorpresas)"""
        recommendations = []
        
        # Simular descubrimientos inesperados
        serendipity_sources = [
            "Hidden gem",
            "Underrated classic",
            "Unexpected find",
            "Musical surprise",
            "Diamond in the rough"
        ]
        
        for source in serendipity_sources:
            track = Track(
                id=f"serendipity_{hash(source) % 10000}",
                title=f"{source}",
                artist="Unknown Artist",
                album="Hidden Treasures"
            )
            
            recommendation = Recommendation(
                track=track,
                confidence=0.4,
                reasoning=f"Unexpected discovery: {source}",
                tags=["discovery", "serendipity", "surprise"]
            )
            recommendations.append(recommendation)
        
        return recommendations


class GamificationSystem:
    """Sistema de gamificación"""
    
    def __init__(self):
        self.achievements: Dict[int, List[UserAchievement]] = {}
        self.streaks: Dict[int, UserStreak] = {}
        self.user_stats: Dict[int, UserStats] = {}
        self.achievement_definitions = self._setup_achievement_definitions()
    
    def _setup_achievement_definitions(self) -> Dict[AchievementType, Dict[str, Any]]:
        """Configurar definiciones de logros"""
        return {
            AchievementType.LISTENING_STREAK: {
                "title": "Streak Master",
                "description": "Listen to music for 7 consecutive days",
                "points": 100,
                "rarity": "common",
                "requirement": {"type": "streak", "value": 7}
            },
            AchievementType.GENRE_EXPLORER: {
                "title": "Genre Explorer",
                "description": "Listen to 10 different genres",
                "points": 150,
                "rarity": "rare",
                "requirement": {"type": "genres", "value": 10}
            },
            AchievementType.ARTIST_DISCOVERER: {
                "title": "Artist Discoverer",
                "description": "Discover 50 new artists",
                "points": 200,
                "rarity": "epic",
                "requirement": {"type": "artists", "value": 50}
            },
            AchievementType.PLAYLIST_CREATOR: {
                "title": "Playlist Creator",
                "description": "Create 5 playlists",
                "points": 75,
                "rarity": "common",
                "requirement": {"type": "playlists", "value": 5}
            },
            AchievementType.SOCIAL_USER: {
                "title": "Social Butterfly",
                "description": "Share 10 recommendations",
                "points": 125,
                "rarity": "rare",
                "requirement": {"type": "shares", "value": 10}
            },
            AchievementType.POWER_USER: {
                "title": "Power User",
                "description": "Use the bot for 30 days",
                "points": 300,
                "rarity": "legendary",
                "requirement": {"type": "days_active", "value": 30}
            }
        }
    
    def update_user_stats(self, user_id: int, activity_type: str, metadata: Dict[str, Any] = None):
        """Actualizar estadísticas del usuario"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = UserStats(
                user_id=user_id,
                total_listens=0,
                unique_artists=0,
                unique_genres=0,
                playlists_created=0,
                recommendations_given=0,
                recommendations_liked=0,
                days_active=0,
                last_activity=datetime.now(),
                level=1,
                experience_points=0
            )
        
        stats = self.user_stats[user_id]
        stats.last_activity = datetime.now()
        
        # Actualizar según tipo de actividad
        if activity_type == "listen":
            stats.total_listens += 1
            stats.experience_points += 1
        elif activity_type == "artist_discovered":
            stats.unique_artists += 1
            stats.experience_points += 5
        elif activity_type == "genre_explored":
            stats.unique_genres += 1
            stats.experience_points += 3
        elif activity_type == "playlist_created":
            stats.playlists_created += 1
            stats.experience_points += 10
        elif activity_type == "recommendation_given":
            stats.recommendations_given += 1
            stats.experience_points += 2
        elif activity_type == "recommendation_liked":
            stats.recommendations_liked += 1
            stats.experience_points += 1
        
        # Calcular nivel
        stats.level = (stats.experience_points // 100) + 1
        
        # Verificar logros
        self._check_achievements(user_id, stats)
    
    def _check_achievements(self, user_id: int, stats: UserStats):
        """Verificar si el usuario ha ganado logros"""
        if user_id not in self.achievements:
            self.achievements[user_id] = []
        
        user_achievements = self.achievements[user_id]
        earned_achievement_ids = {a.achievement_type for a in user_achievements}
        
        for achievement_type, definition in self.achievement_definitions.items():
            if achievement_type in earned_achievement_ids:
                continue
            
            requirement = definition["requirement"]
            requirement_met = False
            
            if requirement["type"] == "streak":
                streak = self.streaks.get(user_id)
                requirement_met = streak and streak.current_streak >= requirement["value"]
            elif requirement["type"] == "genres":
                requirement_met = stats.unique_genres >= requirement["value"]
            elif requirement["type"] == "artists":
                requirement_met = stats.unique_artists >= requirement["value"]
            elif requirement["type"] == "playlists":
                requirement_met = stats.playlists_created >= requirement["value"]
            elif requirement["type"] == "shares":
                # Simular shares (en implementación real vendría de base de datos)
                requirement_met = stats.recommendations_given >= requirement["value"]
            elif requirement["type"] == "days_active":
                days_active = (datetime.now() - stats.last_activity).days
                requirement_met = days_active >= requirement["value"]
            
            if requirement_met:
                achievement = UserAchievement(
                    achievement_id=f"ACH_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    achievement_type=achievement_type,
                    title=definition["title"],
                    description=definition["description"],
                    earned_at=datetime.now(),
                    points=definition["points"],
                    rarity=definition["rarity"]
                )
                
                user_achievements.append(achievement)
                logger.info(f"🏆 Usuario {user_id} ganó logro: {achievement.title}")
    
    def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Obtener logros del usuario"""
        return self.achievements.get(user_id, [])
    
    def get_user_stats(self, user_id: int) -> Optional[UserStats]:
        """Obtener estadísticas del usuario"""
        return self.user_stats.get(user_id)
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple[int, int, int]]:
        """Obtener tabla de clasificación (user_id, level, experience_points)"""
        leaderboard = []
        for user_id, stats in self.user_stats.items():
            leaderboard.append((user_id, stats.level, stats.experience_points))
        
        # Ordenar por puntos de experiencia
        leaderboard.sort(key=lambda x: x[2], reverse=True)
        return leaderboard[:limit]


class UserFeaturesSystem:
    """Sistema principal de características de usuario"""
    
    def __init__(self):
        self.discovery_engine = MusicDiscoveryEngine()
        self.gamification = GamificationSystem()
        self.features_enabled = os.getenv("ENABLE_USER_FEATURES", "true").lower() == "true"
        
        if self.features_enabled:
            logger.info("✅ UserFeaturesSystem habilitado")
        else:
            logger.info("⚠️ UserFeaturesSystem deshabilitado")
    
    async def discover_music(self, user_profile: UserProfile, user_id: int, 
                           discovery_type: str = 'mixed') -> List[Recommendation]:
        """Descubrir nueva música para el usuario"""
        if not self.features_enabled:
            return []
        
        try:
            recommendations = await self.discovery_engine.discover_new_music(
                user_profile, user_id, discovery_type
            )
            
            # Actualizar estadísticas
            self.gamification.update_user_stats(user_id, "recommendation_given")
            
            return recommendations
        except Exception as e:
            logger.error(f"❌ Error en descubrimiento musical: {e}")
            return []
    
    def track_user_activity(self, user_id: int, activity_type: str, metadata: Dict[str, Any] = None):
        """Rastrear actividad del usuario"""
        if not self.features_enabled:
            return
        
        try:
            self.gamification.update_user_stats(user_id, activity_type, metadata)
        except Exception as e:
            logger.error(f"❌ Error rastreando actividad: {e}")
    
    def get_user_profile_enhanced(self, user_id: int) -> Dict[str, Any]:
        """Obtener perfil mejorado del usuario"""
        if not self.features_enabled:
            return {"error": "Features disabled"}
        
        try:
            stats = self.gamification.get_user_stats(user_id)
            achievements = self.gamification.get_user_achievements(user_id)
            
            if not stats:
                return {"error": "User not found"}
            
            return {
                "user_id": user_id,
                "level": stats.level,
                "experience_points": stats.experience_points,
                "total_listens": stats.total_listens,
                "unique_artists": stats.unique_artists,
                "unique_genres": stats.unique_genres,
                "playlists_created": stats.playlists_created,
                "recommendations_given": stats.recommendations_given,
                "recommendations_liked": stats.recommendations_liked,
                "days_active": stats.days_active,
                "last_activity": stats.last_activity.isoformat(),
                "achievements": [
                    {
                        "title": a.title,
                        "description": a.description,
                        "points": a.points,
                        "rarity": a.rarity,
                        "earned_at": a.earned_at.isoformat()
                    }
                    for a in achievements
                ],
                "achievement_count": len(achievements),
                "next_level_points": (stats.level * 100) - stats.experience_points
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo perfil mejorado: {e}")
            return {"error": str(e)}
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener tabla de clasificación"""
        if not self.features_enabled:
            return []
        
        try:
            leaderboard = self.gamification.get_leaderboard(limit)
            return [
                {
                    "rank": i + 1,
                    "user_id": user_id,
                    "level": level,
                    "experience_points": points
                }
                for i, (user_id, level, points) in enumerate(leaderboard)
            ]
        except Exception as e:
            logger.error(f"❌ Error obteniendo leaderboard: {e}")
            return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema de características"""
        if not self.features_enabled:
            return {"error": "Features disabled"}
        
        try:
            total_users = len(self.gamification.user_stats)
            total_achievements = sum(len(achievements) for achievements in self.gamification.achievements.values())
            
            return {
                "total_users": total_users,
                "total_achievements_earned": total_achievements,
                "features_enabled": self.features_enabled,
                "discovery_algorithms": list(self.discovery_engine.discovery_algorithms.keys()),
                "achievement_types": len(self.gamification.achievement_definitions)
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas del sistema: {e}")
            return {"error": str(e)}


# Instancia global del sistema de características de usuario
user_features_system = UserFeaturesSystem()
