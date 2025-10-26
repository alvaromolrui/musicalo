"""
Sistema de analytics y métricas para Musicalo
"""
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Tipos de interacciones del usuario"""
    COMMAND = "command"
    CONVERSATION = "conversation"
    RECOMMENDATION = "recommendation"
    SEARCH = "search"
    PLAYLIST = "playlist"
    STATS = "stats"
    RELEASES = "releases"
    NOWPLAYING = "nowplaying"
    SHARE = "share"
    BUTTON_CLICK = "button_click"


class InteractionResult(Enum):
    """Resultados de interacciones"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class InteractionMetrics:
    """Métricas de una interacción"""
    user_id: int
    interaction_type: str
    result: str
    duration_ms: float
    timestamp: datetime
    session_id: Optional[str] = None
    error_message: Optional[str] = None
    cache_hit: bool = False
    data_size: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class UserSession:
    """Sesión de usuario"""
    user_id: int
    session_id: str
    start_time: datetime
    last_activity: datetime
    interaction_count: int = 0
    total_duration_ms: float = 0.0
    successful_interactions: int = 0
    failed_interactions: int = 0


class MetricsCollector:
    """Recolector de métricas en tiempo real"""
    
    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self.metrics_file = Path("/app/logs/analytics.json")
        self.sessions_file = Path("/app/logs/sessions.json")
        self._metrics_buffer: List[InteractionMetrics] = []
        self._sessions: Dict[str, UserSession] = {}
        self._buffer_lock = asyncio.Lock()
        self._flush_interval = 60  # Flush cada minuto
        self._last_flush = datetime.now()
        
        # Crear directorio de logs si no existe
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Cargar sesiones existentes
        self._load_sessions()
    
    def _load_sessions(self):
        """Cargar sesiones desde archivo"""
        try:
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    for session_data in sessions_data:
                        session = UserSession(
                            user_id=session_data['user_id'],
                            session_id=session_data['session_id'],
                            start_time=datetime.fromisoformat(session_data['start_time']),
                            last_activity=datetime.fromisoformat(session_data['last_activity']),
                            interaction_count=session_data.get('interaction_count', 0),
                            total_duration_ms=session_data.get('total_duration_ms', 0.0),
                            successful_interactions=session_data.get('successful_interactions', 0),
                            failed_interactions=session_data.get('failed_interactions', 0)
                        )
                        self._sessions[session.session_id] = session
                logger.info(f"✅ Cargadas {len(self._sessions)} sesiones existentes")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando sesiones: {e}")
    
    def _save_sessions(self):
        """Guardar sesiones en archivo"""
        try:
            sessions_data = []
            for session in self._sessions.values():
                sessions_data.append({
                    'user_id': session.user_id,
                    'session_id': session.session_id,
                    'start_time': session.start_time.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'interaction_count': session.interaction_count,
                    'total_duration_ms': session.total_duration_ms,
                    'successful_interactions': session.successful_interactions,
                    'failed_interactions': session.failed_interactions
                })
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando sesiones: {e}")
    
    async def record_interaction(self, metrics: InteractionMetrics):
        """Registrar una interacción"""
        async with self._buffer_lock:
            self._metrics_buffer.append(metrics)
            
            # Actualizar sesión
            session_id = metrics.session_id or f"session_{metrics.user_id}_{datetime.now().strftime('%Y%m%d')}"
            if session_id not in self._sessions:
                self._sessions[session_id] = UserSession(
                    user_id=metrics.user_id,
                    session_id=session_id,
                    start_time=metrics.timestamp,
                    last_activity=metrics.timestamp
                )
            
            session = self._sessions[session_id]
            session.last_activity = metrics.timestamp
            session.interaction_count += 1
            session.total_duration_ms += metrics.duration_ms
            
            if metrics.result == InteractionResult.SUCCESS.value:
                session.successful_interactions += 1
            else:
                session.failed_interactions += 1
            
            # Flush si el buffer está lleno o ha pasado el tiempo
            if (len(self._metrics_buffer) >= 100 or 
                (datetime.now() - self._last_flush).seconds >= self._flush_interval):
                await self._flush_metrics()
    
    async def _flush_metrics(self):
        """Volcar métricas al archivo"""
        if not self._metrics_buffer:
            return
        
        try:
            # Leer métricas existentes
            existing_metrics = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    existing_metrics = json.load(f)
            
            # Agregar nuevas métricas
            new_metrics = [asdict(metric) for metric in self._metrics_buffer]
            all_metrics = existing_metrics + new_metrics
            
            # Limpiar métricas antiguas
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            filtered_metrics = [
                metric for metric in all_metrics
                if datetime.fromisoformat(metric['timestamp']) >= cutoff_date
            ]
            
            # Guardar
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_metrics, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"📊 Flushed {len(self._metrics_buffer)} métricas")
            self._metrics_buffer.clear()
            self._last_flush = datetime.now()
            
            # Guardar sesiones
            self._save_sessions()
            
        except Exception as e:
            logger.error(f"❌ Error flushing métricas: {e}")
    
    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener resumen de métricas"""
        try:
            if not self.metrics_file.exists():
                return {"error": "No hay métricas disponibles"}
            
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                all_metrics = json.load(f)
            
            # Filtrar por tiempo
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [
                metric for metric in all_metrics
                if datetime.fromisoformat(metric['timestamp']) >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"message": f"No hay métricas en las últimas {hours} horas"}
            
            # Calcular estadísticas
            total_interactions = len(recent_metrics)
            successful_interactions = len([
                m for m in recent_metrics 
                if m['result'] == InteractionResult.SUCCESS.value
            ])
            
            avg_duration = sum(m['duration_ms'] for m in recent_metrics) / total_interactions
            
            # Interacciones por tipo
            type_counts = {}
            for metric in recent_metrics:
                interaction_type = metric['interaction_type']
                type_counts[interaction_type] = type_counts.get(interaction_type, 0) + 1
            
            # Usuarios únicos
            unique_users = len(set(m['user_id'] for m in recent_metrics))
            
            # Cache hit rate
            cache_hits = len([m for m in recent_metrics if m.get('cache_hit', False)])
            cache_hit_rate = (cache_hits / total_interactions * 100) if total_interactions > 0 else 0
            
            return {
                "period_hours": hours,
                "total_interactions": total_interactions,
                "successful_interactions": successful_interactions,
                "success_rate": (successful_interactions / total_interactions * 100) if total_interactions > 0 else 0,
                "unique_users": unique_users,
                "average_duration_ms": round(avg_duration, 2),
                "interactions_by_type": type_counts,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "active_sessions": len(self._sessions),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen de métricas: {e}")
            return {"error": str(e)}


class PerformanceMonitor:
    """Monitor de rendimiento del sistema"""
    
    def __init__(self):
        self.response_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.cache_stats: Dict[str, int] = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
    
    def record_response_time(self, operation: str, duration_ms: float):
        """Registrar tiempo de respuesta"""
        if operation not in self.response_times:
            self.response_times[operation] = []
        
        self.response_times[operation].append(duration_ms)
        
        # Mantener solo últimos 1000 registros por operación
        if len(self.response_times[operation]) > 1000:
            self.response_times[operation] = self.response_times[operation][-1000:]
    
    def record_error(self, operation: str, error_type: str = "unknown"):
        """Registrar error"""
        key = f"{operation}:{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
    
    def record_cache_event(self, event_type: str):
        """Registrar evento de caché"""
        if event_type in self.cache_stats:
            self.cache_stats[event_type] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtener resumen de rendimiento"""
        summary = {
            "response_times": {},
            "error_counts": self.error_counts.copy(),
            "cache_stats": self.cache_stats.copy(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Calcular estadísticas de tiempos de respuesta
        for operation, times in self.response_times.items():
            if times:
                summary["response_times"][operation] = {
                    "count": len(times),
                    "avg_ms": round(sum(times) / len(times), 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2) if len(times) > 20 else None
                }
        
        return summary


class UserBehaviorAnalyzer:
    """Analizador de comportamiento del usuario"""
    
    def __init__(self):
        self.user_patterns: Dict[int, Dict[str, Any]] = {}
    
    def analyze_user_pattern(self, user_id: int, interaction: InteractionMetrics) -> Dict[str, Any]:
        """Analizar patrón de comportamiento del usuario"""
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = {
                'total_interactions': 0,
                'favorite_commands': {},
                'avg_session_duration': 0,
                'peak_hours': {},
                'error_rate': 0,
                'last_seen': None
            }
        
        pattern = self.user_patterns[user_id]
        pattern['total_interactions'] += 1
        pattern['last_seen'] = interaction.timestamp.isoformat()
        
        # Comando favorito
        cmd = interaction.interaction_type
        pattern['favorite_commands'][cmd] = pattern['favorite_commands'].get(cmd, 0) + 1
        
        # Hora pico
        hour = interaction.timestamp.hour
        pattern['peak_hours'][hour] = pattern['peak_hours'].get(hour, 0) + 1
        
        return pattern
    
    def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Obtener insights del usuario"""
        if user_id not in self.user_patterns:
            return {"message": "Usuario no encontrado"}
        
        pattern = self.user_patterns[user_id]
        
        # Comando más usado
        favorite_command = max(pattern['favorite_commands'].items(), key=lambda x: x[1])[0] if pattern['favorite_commands'] else None
        
        # Hora pico
        peak_hour = max(pattern['peak_hours'].items(), key=lambda x: x[1])[0] if pattern['peak_hours'] else None
        
        return {
            "user_id": user_id,
            "total_interactions": pattern['total_interactions'],
            "favorite_command": favorite_command,
            "peak_hour": peak_hour,
            "last_seen": pattern['last_seen'],
            "command_distribution": pattern['favorite_commands']
        }


class AnalyticsSystem:
    """Sistema principal de analytics"""
    
    def __init__(self, retention_days: int = 30):
        self.metrics_collector = MetricsCollector(retention_days)
        self.performance_monitor = PerformanceMonitor()
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.enabled = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
        
        if self.enabled:
            logger.info("✅ Sistema de analytics habilitado")
        else:
            logger.info("⚠️ Sistema de analytics deshabilitado")
    
    async def track_interaction(
        self, 
        user_id: int, 
        interaction_type: str, 
        duration_ms: float, 
        success: bool,
        session_id: Optional[str] = None,
        error_message: Optional[str] = None,
        cache_hit: bool = False,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Rastrear interacción del usuario"""
        if not self.enabled:
            return
        
        try:
            metrics = InteractionMetrics(
                user_id=user_id,
                interaction_type=interaction_type,
                result=InteractionResult.SUCCESS.value if success else InteractionResult.ERROR.value,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                session_id=session_id,
                error_message=error_message,
                cache_hit=cache_hit,
                additional_data=additional_data
            )
            
            await self.metrics_collector.record_interaction(metrics)
            
            # Actualizar monitores
            self.performance_monitor.record_response_time(interaction_type, duration_ms)
            if not success:
                self.performance_monitor.record_error(interaction_type, error_message or "unknown")
            
            if cache_hit:
                self.performance_monitor.record_cache_event('hits')
            else:
                self.performance_monitor.record_cache_event('misses')
            
            # Analizar comportamiento del usuario
            self.behavior_analyzer.analyze_user_pattern(user_id, metrics)
            
        except Exception as e:
            logger.error(f"❌ Error tracking interaction: {e}")
    
    async def get_system_insights(self) -> Dict[str, Any]:
        """Obtener insights del sistema"""
        try:
            metrics_summary = await self.metrics_collector.get_metrics_summary(24)
            performance_summary = self.performance_monitor.get_performance_summary()
            
            return {
                "metrics": metrics_summary,
                "performance": performance_summary,
                "active_users": len(self.behavior_analyzer.user_patterns),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo insights: {e}")
            return {"error": str(e)}
    
    async def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Obtener insights específicos del usuario"""
        return self.behavior_analyzer.get_user_insights(user_id)
    
    async def cleanup_old_data(self):
        """Limpiar datos antiguos"""
        try:
            await self.metrics_collector._flush_metrics()
            logger.info("🧹 Datos antiguos limpiados")
        except Exception as e:
            logger.error(f"❌ Error limpiando datos: {e}")


# Instancia global del sistema de analytics
analytics_system = AnalyticsSystem()
