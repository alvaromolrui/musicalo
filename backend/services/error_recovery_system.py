"""
Sistema de recuperación automática y manejo de errores mejorado
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import traceback
import json
import os

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Niveles de severidad de errores"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categorías de errores"""
    NETWORK = "network"
    API = "api"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Contexto de un error"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    error_message: str
    stack_trace: str
    user_id: Optional[int] = None
    operation: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None


class CircuitBreaker:
    """Circuit Breaker para prevenir cascadas de errores"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Verificar si se puede ejecutar la operación"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Registrar éxito y resetear el circuit breaker"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Registrar fallo"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"🔴 Circuit breaker abierto después de {self.failure_count} fallos")


class RetryStrategy:
    """Estrategia de reintentos con backoff exponencial"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """Calcular delay para el intento actual"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecutar función con reintentos"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(f"⚠️ Intento {attempt + 1} falló, reintentando en {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Todos los reintentos fallaron: {e}")
        
        raise last_exception


class ErrorRecoverySystem:
    """Sistema principal de recuperación de errores"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies: Dict[str, RetryStrategy] = {}
        self.error_history: List[ErrorContext] = []
        self.max_error_history = 1000
        
        # Configurar estrategias de reintento por categoría
        self.retry_strategies = {
            ErrorCategory.NETWORK: RetryStrategy(max_retries=3, base_delay=1.0),
            ErrorCategory.API: RetryStrategy(max_retries=2, base_delay=2.0),
            ErrorCategory.RATE_LIMIT: RetryStrategy(max_retries=1, base_delay=5.0),
            ErrorCategory.TIMEOUT: RetryStrategy(max_retries=2, base_delay=1.0),
            ErrorCategory.DATABASE: RetryStrategy(max_retries=1, base_delay=3.0),
        }
        
        logger.info("✅ ErrorRecoverySystem inicializado")
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Obtener o crear circuit breaker para un servicio"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]
    
    def get_retry_strategy(self, category: ErrorCategory) -> RetryStrategy:
        """Obtener estrategia de reintento para una categoría"""
        return self.retry_strategies.get(category, RetryStrategy())
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorizar un error basado en su tipo"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        if "connection" in error_message or "network" in error_message:
            return ErrorCategory.NETWORK
        elif "api" in error_message or "http" in error_message:
            return ErrorCategory.API
        elif "database" in error_message or "sql" in error_message:
            return ErrorCategory.DATABASE
        elif "auth" in error_message or "token" in error_message:
            return ErrorCategory.AUTHENTICATION
        elif "rate" in error_message or "limit" in error_message:
            return ErrorCategory.RATE_LIMIT
        elif "timeout" in error_message:
            return ErrorCategory.TIMEOUT
        elif "validation" in error_message or "invalid" in error_message:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.UNKNOWN
    
    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determinar severidad del error"""
        error_message = str(error).lower()
        
        if "critical" in error_message or category == ErrorCategory.DATABASE:
            return ErrorSeverity.CRITICAL
        elif "auth" in error_message or "permission" in error_message:
            return ErrorSeverity.HIGH
        elif "rate" in error_message or "timeout" in error_message:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def log_error(self, error: Exception, user_id: Optional[int] = None, 
                  operation: Optional[str] = None, metadata: Dict[str, Any] = None) -> ErrorContext:
        """Registrar un error en el sistema"""
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(error)}"
        category = self.categorize_error(error)
        severity = self.determine_severity(error, category)
        
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            user_id=user_id,
            operation=operation,
            metadata=metadata or {}
        )
        
        # Agregar a historial
        self.error_history.append(error_context)
        
        # Mantener solo los últimos errores
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
        
        # Log según severidad
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"🚨 Error crítico [{error_id}]: {error}")
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"❌ Error alto [{error_id}]: {error}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"⚠️ Error medio [{error_id}]: {error}")
        else:
            logger.info(f"ℹ️ Error bajo [{error_id}]: {error}")
        
        return error_context
    
    async def execute_with_recovery(self, func: Callable, service_name: str, 
                                  *args, user_id: Optional[int] = None, 
                                  operation: Optional[str] = None, **kwargs) -> Any:
        """Ejecutar función con recuperación automática"""
        circuit_breaker = self.get_circuit_breaker(service_name)
        
        # Verificar circuit breaker
        if not circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker abierto para {service_name}")
        
        try:
            # Ejecutar función
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Registrar éxito
            circuit_breaker.record_success()
            return result
            
        except Exception as error:
            # Registrar error
            error_context = self.log_error(error, user_id, operation)
            
            # Registrar fallo en circuit breaker
            circuit_breaker.record_failure()
            
            # Intentar recuperación automática
            if error_context.category in self.retry_strategies:
                try:
                    retry_strategy = self.get_retry_strategy(error_context.category)
                    result = await retry_strategy.execute_with_retry(func, *args, **kwargs)
                    circuit_breaker.record_success()
                    logger.info(f"✅ Recuperación exitosa para {service_name}")
                    return result
                except Exception as retry_error:
                    logger.error(f"❌ Recuperación falló para {service_name}: {retry_error}")
                    raise retry_error
            else:
                raise error
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener estadísticas de errores"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff_time]
        
        if not recent_errors:
            return {"total_errors": 0, "by_category": {}, "by_severity": {}}
        
        by_category = {}
        by_severity = {}
        
        for error in recent_errors:
            category = error.category.value
            severity = error.severity.value
            
            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_errors": len(recent_errors),
            "by_category": by_category,
            "by_severity": by_severity,
            "circuit_breakers": {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for name, cb in self.circuit_breakers.items()
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Obtener estado de salud del sistema"""
        open_circuits = sum(1 for cb in self.circuit_breakers.values() if cb.state == "OPEN")
        total_circuits = len(self.circuit_breakers)
        
        recent_errors = self.get_error_stats(hours=1)
        critical_errors = recent_errors.get("by_severity", {}).get("critical", 0)
        
        health_score = 100
        if open_circuits > 0:
            health_score -= (open_circuits / total_circuits) * 50
        if critical_errors > 0:
            health_score -= min(critical_errors * 10, 50)
        
        status = "healthy"
        if health_score < 50:
            status = "unhealthy"
        elif health_score < 80:
            status = "degraded"
        
        return {
            "status": status,
            "health_score": health_score,
            "open_circuits": open_circuits,
            "total_circuits": total_circuits,
            "recent_errors": recent_errors,
            "timestamp": datetime.now().isoformat()
        }


# Instancia global del sistema de recuperación de errores
error_recovery_system = ErrorRecoverySystem()
