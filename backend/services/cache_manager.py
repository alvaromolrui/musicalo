"""
Sistema de caché distribuido con Redis y fallback automático
"""
import json
import asyncio
import logging
from typing import Any, Optional, Dict, Callable, Union
from datetime import datetime, timedelta
import aioredis
import os
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """Gestor de caché distribuido con Redis y fallback local"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = int(os.getenv("REDIS_CACHE_TTL", "3600"))
        self.redis_client: Optional[aioredis.Redis] = None
        self.local_cache: Dict[str, Dict] = {}
        self.cache_hierarchy = {
            'user_context': 3600,      # 1 hora
            'recommendations': 1800,   # 30 minutos
            'library_data': 7200,      # 2 horas
            'musicbrainz_metadata': 86400,  # 24 horas
            'listenbrainz_data': 300,  # 5 minutos
            'ai_responses': 600,       # 10 minutos
            'analytics': 3600          # 1 hora
        }
        self._connection_lock = asyncio.Lock()
    
    async def _ensure_connection(self):
        """Asegurar conexión a Redis"""
        if self.redis_client is None:
            async with self._connection_lock:
                if self.redis_client is None:
                    try:
                        self.redis_client = await aioredis.from_url(
                            self.redis_url,
                            encoding="utf-8",
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_keepalive=True,
                            retry_on_timeout=True
                        )
                        # Test connection
                        await self.redis_client.ping()
                        logger.info("✅ Conexión a Redis establecida")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo conectar a Redis: {e}")
                        self.redis_client = None
    
    async def get_with_fallback(
        self, 
        key: str, 
        fetch_func: Callable, 
        ttl: Optional[int] = None,
        cache_type: str = 'default'
    ) -> Any:
        """
        Obtener datos con fallback automático: Redis -> Local -> Fetch
        
        Args:
            key: Clave del caché
            fetch_func: Función para obtener datos si no están en caché
            ttl: Tiempo de vida en segundos (usa cache_hierarchy si no se especifica)
            cache_type: Tipo de caché para determinar TTL automático
            
        Returns:
            Datos desde caché o fetch_func
        """
        if ttl is None:
            ttl = self.cache_hierarchy.get(cache_type, self.default_ttl)
        
        # 1. Verificar caché local primero (más rápido)
        local_data = self._get_local_cache(key, ttl)
        if local_data is not None:
            logger.debug(f"💾 Cache hit local: {key}")
            return local_data
        
        # 2. Verificar Redis
        try:
            await self._ensure_connection()
            if self.redis_client:
                redis_data = await self.redis_client.get(key)
                if redis_data:
                    data = json.loads(redis_data)
                    # Guardar en caché local para próximas consultas
                    self._set_local_cache(key, data, ttl)
                    logger.debug(f"💾 Cache hit Redis: {key}")
                    return data
        except Exception as e:
            logger.warning(f"⚠️ Error accediendo a Redis: {e}")
        
        # 3. Fetch y cachear
        try:
            logger.debug(f"🔄 Fetching data for key: {key}")
            data = await fetch_func()
            
            # Cachear en ambos niveles
            self._set_local_cache(key, data, ttl)
            await self._set_redis_cache(key, data, ttl)
            
            logger.debug(f"✅ Data fetched and cached: {key}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {key}: {e}")
            raise
    
    def _get_local_cache(self, key: str, ttl: int) -> Optional[Any]:
        """Obtener del caché local si no ha expirado"""
        if key in self.local_cache:
            cache_entry = self.local_cache[key]
            if datetime.now() < cache_entry['expires_at']:
                return cache_entry['data']
            else:
                # Expirar entrada
                del self.local_cache[key]
        return None
    
    def _set_local_cache(self, key: str, data: Any, ttl: int):
        """Guardar en caché local"""
        self.local_cache[key] = {
            'data': data,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
            'created_at': datetime.now()
        }
        
        # Limpiar caché local si tiene demasiadas entradas
        if len(self.local_cache) > 1000:
            self._cleanup_local_cache()
    
    async def _set_redis_cache(self, key: str, data: Any, ttl: int):
        """Guardar en Redis"""
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    key, 
                    ttl, 
                    json.dumps(data, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.warning(f"⚠️ Error guardando en Redis: {e}")
    
    def _cleanup_local_cache(self):
        """Limpiar caché local eliminando entradas expiradas"""
        current_time = datetime.now()
        expired_keys = [
            key for key, entry in self.local_cache.items()
            if current_time >= entry['expires_at']
        ]
        
        for key in expired_keys:
            del self.local_cache[key]
        
        logger.debug(f"🧹 Limpiadas {len(expired_keys)} entradas expiradas del caché local")
    
    async def invalidate(self, key: str):
        """Invalidar entrada específica en ambos cachés"""
        # Local
        if key in self.local_cache:
            del self.local_cache[key]
        
        # Redis
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"⚠️ Error invalidando en Redis: {e}")
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidar entradas que coincidan con un patrón"""
        try:
            if self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"🗑️ Invalidadas {len(keys)} entradas con patrón: {pattern}")
        except Exception as e:
            logger.warning(f"⚠️ Error invalidando patrón en Redis: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del caché"""
        local_stats = {
            'local_entries': len(self.local_cache),
            'local_memory_usage': sum(
                len(str(entry['data'])) for entry in self.local_cache.values()
            )
        }
        
        redis_stats = {}
        try:
            if self.redis_client:
                info = await self.redis_client.info('memory')
                redis_stats = {
                    'redis_used_memory': info.get('used_memory_human', 'N/A'),
                    'redis_connected_clients': info.get('connected_clients', 0),
                    'redis_keyspace_hits': info.get('keyspace_hits', 0),
                    'redis_keyspace_misses': info.get('keyspace_misses', 0)
                }
        except Exception as e:
            redis_stats = {'error': str(e)}
        
        return {
            'local': local_stats,
            'redis': redis_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    async def close(self):
        """Cerrar conexión a Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None


def cached(
    ttl: Optional[int] = None,
    cache_type: str = 'default',
    key_prefix: str = ''
):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        ttl: Tiempo de vida en segundos
        cache_type: Tipo de caché para TTL automático
        key_prefix: Prefijo para la clave del caché
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generar clave única basada en función y argumentos
            func_name = func.__name__
            args_str = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}{func_name}:{hash(args_str)}"
            
            # Obtener instancia del cache manager
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if cache_manager is None:
                # Crear instancia global si no existe
                cache_manager = CacheManager()
                wrapper._cache_manager = cache_manager
            
            # Usar caché con fallback
            return await cache_manager.get_with_fallback(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl,
                cache_type
            )
        return wrapper
    return decorator


# Instancia global del cache manager
cache_manager = CacheManager()
