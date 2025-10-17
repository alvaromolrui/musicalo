"""
Gestor de contexto conversacional para mantener estado entre mensajes
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ConversationSession:
    """Sesión conversacional de un usuario"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.last_interaction = datetime.now()
        self.message_history: List[Dict] = []  # Últimos N mensajes
        self.last_recommendations: List[Dict] = []  # Últimas recomendaciones
        self.last_query_context: Dict = {}  # Contexto de la última query
        self.preferences: Dict = {}  # Preferencias detectadas en la sesión
        self.last_action: Optional[str] = None  # Última acción realizada
        self.action_params: Dict = {}  # Parámetros de la última acción
    
    def add_message(self, role: str, content: str):
        """Agregar mensaje al historial
        
        Args:
            role: "user" o "assistant"
            content: Contenido del mensaje
        """
        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        
        # Mantener solo últimos 10 mensajes
        if len(self.message_history) > 10:
            self.message_history = self.message_history[-10:]
        
        logger.debug(f"Agregado mensaje de {role} a sesión de usuario {self.user_id}")
    
    def set_last_recommendations(self, recommendations: List):
        """Guardar últimas recomendaciones para referencias futuras
        
        Args:
            recommendations: Lista de objetos Recommendation
        """
        self.last_recommendations = [
            {
                "artist": rec.track.artist,
                "title": rec.track.title,
                "album": rec.track.album,
                "source": rec.source,
                "id": rec.track.id
            }
            for rec in recommendations[:10]  # Guardar máximo 10
        ]
        logger.info(f"Guardadas {len(self.last_recommendations)} recomendaciones en sesión {self.user_id}")
    
    def set_last_action(self, action: str, params: Dict = None):
        """Guardar última acción realizada
        
        Args:
            action: Nombre de la acción (recommend, search, playlist, etc.)
            params: Parámetros usados en la acción
        """
        self.last_action = action
        self.action_params = params or {}
        logger.debug(f"Acción '{action}' guardada en sesión {self.user_id}")
    
    def get_context_for_ai(self) -> str:
        """Formatear contexto para incluir en prompts a la IA
        
        Returns:
            String formateado con el contexto relevante
        """
        context_parts = []
        
        # Historial de conversación reciente
        if self.message_history:
            context_parts.append("=== CONVERSACIÓN RECIENTE ===")
            for msg in self.message_history[-5:]:  # Últimos 5 mensajes
                role = "Usuario" if msg['role'] == "user" else "Asistente"
                context_parts.append(f"{role}: {msg['content']}")
            context_parts.append("")
        
        # Últimas recomendaciones
        if self.last_recommendations:
            context_parts.append("=== ÚLTIMAS RECOMENDACIONES DADAS ===")
            for i, rec in enumerate(self.last_recommendations[:5], 1):
                context_parts.append(f"{i}. {rec['artist']} - {rec['title']}")
                if rec['album']:
                    context_parts.append(f"   Álbum: {rec['album']}")
            context_parts.append("")
        
        # Última acción
        if self.last_action:
            context_parts.append(f"=== ÚLTIMA ACCIÓN: {self.last_action} ===")
            if self.action_params:
                for key, value in self.action_params.items():
                    context_parts.append(f"  - {key}: {value}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def get_last_artists(self) -> List[str]:
        """Obtener lista de artistas de las últimas recomendaciones
        
        Returns:
            Lista de nombres de artistas
        """
        return [rec['artist'] for rec in self.last_recommendations]
    
    def update_preference(self, key: str, value: Any):
        """Actualizar una preferencia del usuario en esta sesión
        
        Args:
            key: Clave de la preferencia
            value: Valor de la preferencia
        """
        self.preferences[key] = value
        logger.debug(f"Preferencia '{key}' actualizada en sesión {self.user_id}")
    
    def clear(self):
        """Limpiar toda la sesión"""
        self.message_history = []
        self.last_recommendations = []
        self.last_query_context = {}
        self.preferences = {}
        self.last_action = None
        self.action_params = {}
        logger.info(f"Sesión {self.user_id} limpiada completamente")


class ConversationManager:
    """Gestiona el contexto conversacional entre mensajes de múltiples usuarios"""
    
    def __init__(self, session_timeout_hours: int = 2):
        """Inicializar gestor de conversaciones
        
        Args:
            session_timeout_hours: Horas después de las cuales una sesión expira
        """
        self.sessions: Dict[int, ConversationSession] = {}
        self.session_timeout = timedelta(hours=session_timeout_hours)
        logger.info(f"ConversationManager inicializado (timeout: {session_timeout_hours}h)")
    
    def get_session(self, user_id: int) -> ConversationSession:
        """Obtener o crear sesión para un usuario
        
        Args:
            user_id: ID del usuario de Telegram
            
        Returns:
            ConversationSession del usuario
        """
        # Crear nueva sesión si no existe
        if user_id not in self.sessions:
            self.sessions[user_id] = ConversationSession(user_id)
            logger.info(f"Nueva sesión creada para usuario {user_id}")
        
        session = self.sessions[user_id]
        
        # Verificar si la sesión ha expirado
        time_since_last = datetime.now() - session.last_interaction
        if time_since_last > self.session_timeout:
            logger.info(f"Sesión de usuario {user_id} expirada ({time_since_last}), reiniciando")
            session.clear()
        
        # Actualizar timestamp
        session.last_interaction = datetime.now()
        return session
    
    def clear_session(self, user_id: int):
        """Limpiar sesión de usuario específico
        
        Args:
            user_id: ID del usuario de Telegram
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Sesión de usuario {user_id} eliminada")
    
    def clear_old_sessions(self):
        """Limpiar sesiones inactivas (ejecutar periódicamente)"""
        current_time = datetime.now()
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if current_time - session.last_interaction > self.session_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]
        
        if expired_users:
            logger.info(f"Limpiadas {len(expired_users)} sesiones expiradas")
    
    def get_active_sessions_count(self) -> int:
        """Obtener número de sesiones activas
        
        Returns:
            Número de sesiones activas
        """
        return len(self.sessions)
    
    def get_session_info(self, user_id: int) -> Dict:
        """Obtener información sobre una sesión
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Diccionario con información de la sesión
        """
        if user_id not in self.sessions:
            return {"exists": False}
        
        session = self.sessions[user_id]
        time_since_last = datetime.now() - session.last_interaction
        
        return {
            "exists": True,
            "message_count": len(session.message_history),
            "last_recommendations_count": len(session.last_recommendations),
            "last_action": session.last_action,
            "time_since_last_interaction": str(time_since_last),
            "preferences": session.preferences
        }

