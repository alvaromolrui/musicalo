"""
Sistema de caché distribuido con Redis y fallback automático
"""
import redis
import json
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar, Awaitable
from functools import wraps
import logging

logger = logging.getLogger(__name__)

R = TypeVar('R')

class CacheManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_ttl: Dict[str, datetime] = {}
        
        # Configurable TTLs por tipo de caché
        self.cache_type_ttls = {
            'user_context': int(os.getenv("REDIS_CACHE_TTL_USER_CONTEXT", "3600")),  # 1 hora
            'recommendations': int(os.getenv("REDIS_CACHE_TTL_RECOMMENDATIONS", "1800")),  # 30 minutos
            'library_data': int(os.getenv("REDIS_CACHE_TTL_LIBRARY_DATA", "7200")),  # 2 horas
            'musicbrainz_metadata': int(os.getenv("REDIS_CACHE_TTL_MUSICBRAINZ", "86400")), # 24 horas
            'default': int(os.getenv("REDIS_CACHE_TTL", "300")) # 5 minutos
        }
        self._connect_redis()

    def _connect_redis(self):
        try:
            self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Conectado a Redis exitosamente.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"❌ No se pudo conectar a Redis: {e}. Usando solo caché local.")
            self.redis_client = None

    def _get_ttl(self, cache_type: str) -> int:
        return self.cache_type_ttls.get(cache_type, self.cache_type_ttls['default'])

    async def get_with_fallback(self, key: str, fetch_func: Callable[..., Awaitable[R]], cache_type: str = 'default') -> R:
        """
        Obtiene datos del caché o los genera usando fetch_func si no están en caché o han expirado.
        Prioriza caché local, luego Redis.
        """
        # 1. Verificar caché local
        if key in self.local_cache and self.local_cache_ttl.get(key, datetime.min) > datetime.now():
            logger.debug(f"⚡ Cache hit (local): {key}")
            return self.local_cache[key]

        # 2. Verificar Redis
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    # Actualizar caché local
                    self.local_cache[key] = data
                    self.local_cache_ttl[key] = datetime.now() + timedelta(seconds=self._get_ttl(cache_type))
                    logger.debug(f"⚡ Cache hit (Redis): {key}")
                    return data
            except Exception as e:
                logger.warning(f"⚠️ Error al leer de Redis para {key}: {e}")

        # 3. Fetch y cachear
        data = await fetch_func()
        await self._cache_data(key, data, cache_type)
        return data

    async def _cache_data(self, key: str, data: Any, cache_type: str = 'default'):
        """Almacena datos en caché local y Redis."""
        ttl = self._get_ttl(cache_type)
        
        # Cache local
        self.local_cache[key] = data
        self.local_cache_ttl[key] = datetime.now() + timedelta(seconds=ttl)

        # Cache Redis
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(data))
                logger.debug(f"💾 Cached in Redis: {key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"⚠️ Error al escribir en Redis para {key}: {e}")

    async def invalidate_cache(self, key: str):
        """Invalida una entrada específica del caché."""
        if key in self.local_cache:
            del self.local_cache[key]
            if key in self.local_cache_ttl:
                del self.local_cache_ttl[key]
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                logger.debug(f"🗑️ Cache invalidated: {key}")
            except Exception as e:
                logger.warning(f"⚠️ Error al invalidar caché en Redis para {key}: {e}")

    async def clear_all_cache(self):
        """Limpia todo el caché (local y Redis)."""
        self.local_cache.clear()
        self.local_cache_ttl.clear()
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("🗑️ Todo el caché de Redis ha sido limpiado.")
            except Exception as e:
                logger.error(f"❌ Error al limpiar Redis: {e}")
        logger.info("🗑️ Todo el caché local ha sido limpiado.")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas básicas del caché."""
        stats = {
            "local_entries": len(self.local_cache),
            "redis_connected": self.redis_client is not None,
            "redis_keys": 0,
            "redis_memory_usage_mb": 0
        }
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_keys"] = info.get("db0", {}).get("keys", 0)
                stats["redis_memory_usage_mb"] = round(info.get("used_memory", 0) / (1024 * 1024), 2)
            except Exception as e:
                logger.warning(f"⚠️ Error al obtener info de Redis: {e}")
        return stats

cache_manager = CacheManager()

def cached(cache_type: str = 'default', ttl: Optional[int] = None):
    """
    Decorador para cachear resultados de funciones asíncronas.
    Genera una clave de caché basada en el nombre de la función y sus argumentos.
    """
    def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> R:
            # Generar clave de caché
            # Excluir 'self' del cálculo de la clave si es un método de instancia
            func_args = [arg for i, arg in enumerate(args) if i > 0 or not hasattr(args[i], func.__name__)]
            cache_key_parts = [func.__module__, func.__name__] + [str(arg) for arg in func_args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = ":".join(cache_key_parts)

            # Usar el TTL del decorador si se especifica, de lo contrario, el del tipo de caché
            effective_ttl = ttl if ttl is not None else cache_manager._get_ttl(cache_type)

            return await cache_manager.get_with_fallback(
                cache_key,
                lambda: func(*args, **kwargs),
                cache_type=cache_type
            )
        return wrapper
    return decorator