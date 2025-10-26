"""
Sistema de monitoreo avanzado y alertas
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import os
import psutil
import time

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveles de alerta"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Tipos de métricas"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class Metric:
    """Métrica del sistema"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = None
    unit: str = ""


@dataclass
class Alert:
    """Alerta del sistema"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    metric_name: str
    threshold: float
    current_value: float
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class SystemMetricsCollector:
    """Recolector de métricas del sistema"""
    
    def __init__(self):
        self.metrics: List[Metric] = []
        self.max_metrics = 10000
    
    def collect_system_metrics(self) -> List[Metric]:
        """Recolectar métricas del sistema"""
        current_time = datetime.now()
        metrics = []
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(Metric(
                name="system_cpu_usage",
                value=cpu_percent,
                metric_type=MetricType.GAUGE,
                timestamp=current_time,
                unit="percent"
            ))
            
            # Memoria
            memory = psutil.virtual_memory()
            metrics.append(Metric(
                name="system_memory_usage",
                value=memory.percent,
                metric_type=MetricType.GAUGE,
                timestamp=current_time,
                unit="percent"
            ))
            
            metrics.append(Metric(
                name="system_memory_available",
                value=memory.available / (1024**3),  # GB
                metric_type=MetricType.GAUGE,
                timestamp=current_time,
                unit="GB"
            ))
            
            # Disco
            disk = psutil.disk_usage('/')
            metrics.append(Metric(
                name="system_disk_usage",
                value=disk.percent,
                metric_type=MetricType.GAUGE,
                timestamp=current_time,
                unit="percent"
            ))
            
            # Procesos
            process = psutil.Process()
            metrics.append(Metric(
                name="process_memory_usage",
                value=process.memory_info().rss / (1024**2),  # MB
                metric_type=MetricType.GAUGE,
                timestamp=current_time,
                unit="MB"
            ))
            
            metrics.append(Metric(
                name="process_cpu_usage",
                value=process.cpu_percent(),
                metric_type=MetricType.GAUGE,
                timestamp=current_time,
                unit="percent"
            ))
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas del sistema: {e}")
        
        return metrics
    
    def add_metric(self, metric: Metric):
        """Agregar métrica"""
        self.metrics.append(metric)
        
        # Mantener solo las últimas métricas
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_metrics(self, name: Optional[str] = None, hours: int = 24) -> List[Metric]:
        """Obtener métricas filtradas"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        
        if name:
            filtered_metrics = [m for m in filtered_metrics if m.name == name]
        
        return filtered_metrics
    
    def get_latest_metric(self, name: str) -> Optional[Metric]:
        """Obtener la última métrica de un tipo específico"""
        matching_metrics = [m for m in self.metrics if m.name == name]
        if matching_metrics:
            return max(matching_metrics, key=lambda m: m.timestamp)
        return None


class AlertManager:
    """Gestor de alertas"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.max_alerts = 1000
        
        # Configurar reglas de alerta por defecto
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self):
        """Configurar reglas de alerta por defecto"""
        self.alert_rules = {
            "high_cpu_usage": {
                "metric": "system_cpu_usage",
                "threshold": 80.0,
                "level": AlertLevel.WARNING,
                "title": "Alto uso de CPU",
                "message": "El uso de CPU está por encima del 80%"
            },
            "critical_cpu_usage": {
                "metric": "system_cpu_usage",
                "threshold": 95.0,
                "level": AlertLevel.CRITICAL,
                "title": "Uso crítico de CPU",
                "message": "El uso de CPU está por encima del 95%"
            },
            "high_memory_usage": {
                "metric": "system_memory_usage",
                "threshold": 85.0,
                "level": AlertLevel.WARNING,
                "title": "Alto uso de memoria",
                "message": "El uso de memoria está por encima del 85%"
            },
            "critical_memory_usage": {
                "metric": "system_memory_usage",
                "threshold": 95.0,
                "level": AlertLevel.CRITICAL,
                "title": "Uso crítico de memoria",
                "message": "El uso de memoria está por encima del 95%"
            },
            "low_disk_space": {
                "metric": "system_disk_usage",
                "threshold": 90.0,
                "level": AlertLevel.WARNING,
                "title": "Poco espacio en disco",
                "message": "El espacio en disco está por debajo del 10%"
            },
            "critical_disk_space": {
                "metric": "system_disk_usage",
                "threshold": 95.0,
                "level": AlertLevel.CRITICAL,
                "title": "Espacio crítico en disco",
                "message": "El espacio en disco está por debajo del 5%"
            }
        }
    
    def check_alerts(self, metrics: List[Metric]):
        """Verificar alertas basadas en métricas"""
        for rule_name, rule in self.alert_rules.items():
            metric_name = rule["metric"]
            threshold = rule["threshold"]
            level = rule["level"]
            
            # Buscar la métrica más reciente
            latest_metric = None
            for metric in metrics:
                if metric.name == metric_name:
                    if latest_metric is None or metric.timestamp > latest_metric.timestamp:
                        latest_metric = metric
            
            if latest_metric is None:
                continue
            
            # Verificar si se debe generar alerta
            should_alert = False
            if "cpu" in metric_name or "memory" in metric_name:
                should_alert = latest_metric.value >= threshold
            elif "disk" in metric_name:
                should_alert = latest_metric.value >= threshold
            
            if should_alert:
                # Verificar si ya existe una alerta activa para esta regla
                existing_alert = None
                for alert in self.alerts:
                    if (alert.metric_name == metric_name and 
                        not alert.resolved and 
                        alert.level == level):
                        existing_alert = alert
                        break
                
                if not existing_alert:
                    # Crear nueva alerta
                    alert = Alert(
                        alert_id=f"ALERT_{int(time.time())}_{rule_name}",
                        level=level,
                        title=rule["title"],
                        message=rule["message"],
                        timestamp=datetime.now(),
                        metric_name=metric_name,
                        threshold=threshold,
                        current_value=latest_metric.value
                    )
                    
                    self.alerts.append(alert)
                    logger.warning(f"🚨 {level.value.upper()}: {alert.title} - {alert.message}")
    
    def resolve_alert(self, alert_id: str):
        """Resolver una alerta"""
        for alert in self.alerts:
            if alert.alert_id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"✅ Alerta resuelta: {alert.title}")
                break
    
    def get_active_alerts(self) -> List[Alert]:
        """Obtener alertas activas"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener estadísticas de alertas"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alerts if a.timestamp > cutoff_time]
        
        by_level = {}
        for alert in recent_alerts:
            level = alert.level.value
            by_level[level] = by_level.get(level, 0) + 1
        
        return {
            "total_alerts": len(recent_alerts),
            "active_alerts": len(self.get_active_alerts()),
            "by_level": by_level,
            "resolved_rate": len([a for a in recent_alerts if a.resolved]) / len(recent_alerts) if recent_alerts else 0
        }


class PerformanceProfiler:
    """Profiler de rendimiento"""
    
    def __init__(self):
        self.profiles: Dict[str, List[float]] = {}
        self.max_samples = 1000
    
    def start_profile(self, operation: str) -> str:
        """Iniciar perfil de una operación"""
        profile_id = f"{operation}_{int(time.time() * 1000)}"
        return profile_id
    
    def end_profile(self, profile_id: str, operation: str, duration: float):
        """Finalizar perfil de una operación"""
        if operation not in self.profiles:
            self.profiles[operation] = []
        
        self.profiles[operation].append(duration)
        
        # Mantener solo las últimas muestras
        if len(self.profiles[operation]) > self.max_samples:
            self.profiles[operation] = self.profiles[operation][-self.max_samples:]
    
    def get_performance_stats(self, operation: str) -> Dict[str, float]:
        """Obtener estadísticas de rendimiento para una operación"""
        if operation not in self.profiles or not self.profiles[operation]:
            return {}
        
        durations = self.profiles[operation]
        
        return {
            "count": len(durations),
            "avg": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
            "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
            "p99": sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0]
        }
    
    def get_all_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Obtener estadísticas de rendimiento para todas las operaciones"""
        return {
            operation: self.get_performance_stats(operation)
            for operation in self.profiles.keys()
        }


class AdvancedMonitoringSystem:
    """Sistema principal de monitoreo avanzado"""
    
    def __init__(self):
        self.metrics_collector = SystemMetricsCollector()
        self.alert_manager = AlertManager()
        self.profiler = PerformanceProfiler()
        self.monitoring_enabled = os.getenv("ENABLE_ADVANCED_MONITORING", "true").lower() == "true"
        self.collection_interval = int(os.getenv("MONITORING_COLLECTION_INTERVAL", "60"))  # segundos
        
        if self.monitoring_enabled:
            logger.info("✅ AdvancedMonitoringSystem habilitado")
            # Iniciar recolección automática de métricas
            asyncio.create_task(self._start_metrics_collection())
        else:
            logger.info("⚠️ AdvancedMonitoringSystem deshabilitado")
    
    async def _start_metrics_collection(self):
        """Iniciar recolección automática de métricas"""
        while True:
            try:
                metrics = self.metrics_collector.collect_system_metrics()
                for metric in metrics:
                    self.metrics_collector.add_metric(metric)
                
                # Verificar alertas
                self.alert_manager.check_alerts(metrics)
                
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"❌ Error en recolección de métricas: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def profile_operation(self, operation: str):
        """Decorador para perfilar operaciones"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                if not self.monitoring_enabled:
                    return await func(*args, **kwargs)
                
                profile_id = self.profiler.start_profile(operation)
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.profiler.end_profile(profile_id, operation, duration)
            
            def sync_wrapper(*args, **kwargs):
                if not self.monitoring_enabled:
                    return func(*args, **kwargs)
                
                profile_id = self.profiler.start_profile(operation)
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.profiler.end_profile(profile_id, operation, duration)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def get_system_health(self) -> Dict[str, Any]:
        """Obtener estado de salud del sistema"""
        if not self.monitoring_enabled:
            return {"status": "monitoring_disabled"}
        
        # Obtener métricas recientes
        recent_metrics = self.metrics_collector.get_metrics(hours=1)
        
        # Obtener alertas activas
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Calcular score de salud
        health_score = 100
        
        # Penalizar por alertas activas
        for alert in active_alerts:
            if alert.level == AlertLevel.CRITICAL:
                health_score -= 20
            elif alert.level == AlertLevel.ERROR:
                health_score -= 10
            elif alert.level == AlertLevel.WARNING:
                health_score -= 5
        
        # Determinar estado
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "status": status,
            "health_score": health_score,
            "active_alerts": len(active_alerts),
            "recent_metrics": len(recent_metrics),
            "timestamp": datetime.now().isoformat(),
            "monitoring_enabled": self.monitoring_enabled
        }
    
    def get_detailed_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener métricas detalladas"""
        if not self.monitoring_enabled:
            return {"error": "Monitoring disabled"}
        
        metrics = self.metrics_collector.get_metrics(hours=hours)
        
        # Agrupar por tipo de métrica
        by_name = {}
        for metric in metrics:
            if metric.name not in by_name:
                by_name[metric.name] = []
            by_name[metric.name].append(metric)
        
        # Calcular estadísticas para cada métrica
        metric_stats = {}
        for name, metric_list in by_name.items():
            values = [m.value for m in metric_list]
            metric_stats[name] = {
                "count": len(values),
                "latest": values[-1] if values else 0,
                "avg": sum(values) / len(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "unit": metric_list[0].unit if metric_list else ""
            }
        
        return {
            "metrics": metric_stats,
            "performance": self.profiler.get_all_performance_stats(),
            "alerts": self.alert_manager.get_alert_stats(hours),
            "period_hours": hours
        }


# Instancia global del sistema de monitoreo avanzado
advanced_monitoring_system = AdvancedMonitoringSystem()
