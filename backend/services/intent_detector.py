"""
Detector de intenciones usando LLM para interpretar mensajes de usuario
Reemplaza el sistema complejo de regex y keywords
"""
import google.generativeai as genai
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detector de intenciones usando Gemini para interpretar lenguaje natural"""
    
    def __init__(self):
        """Inicializar detector de intenciones"""
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("IntentDetector inicializado con Gemini 2.0 Flash")
    
    async def detect_intent(
        self, 
        user_message: str,
        session_context: Optional[str] = None,
        user_stats: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Detectar intención del usuario usando LLM
        
        Args:
            user_message: Mensaje del usuario
            session_context: Contexto de la sesión conversacional
            user_stats: Estadísticas del usuario (top artistas, etc.)
            
        Returns:
            Diccionario con intent, params y confidence
        """
        try:
            logger.debug(f"Detectando intención para: '{user_message}'")
            
            # Construir prompt para detección de intención
            prompt = self._build_intent_prompt(user_message, session_context, user_stats)
            
            # Generar respuesta
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Limpiar markdown si existe
            if response_text.startswith("```"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Parsear JSON
            intent_data = json.loads(response_text)
            
            logger.info(f"Intención detectada: {intent_data.get('intent')} (confianza: {intent_data.get('confidence', 0)})")
            
            # Validar y normalizar
            return self._validate_and_normalize(intent_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de intención: {e}")
            logger.debug(f"Respuesta recibida: {response_text}")
            # Fallback: conversación general
            return {
                "intent": "conversacion",
                "params": {},
                "confidence": 0.3,
                "raw_message": user_message
            }
        
        except Exception as e:
            logger.error(f"Error detectando intención: {e}")
            return {
                "intent": "conversacion",
                "params": {},
                "confidence": 0.1,
                "error": str(e)
            }
    
    def _build_intent_prompt(
        self, 
        user_message: str, 
        session_context: Optional[str],
        user_stats: Optional[Dict]
    ) -> str:
        """Construir prompt para detección de intención
        
        FILOSOFÍA: El agente conversacional es inteligente y puede manejar CUALQUIER consulta.
        Solo detectamos intenciones MUY OBVIAS que requieren acciones específicas.
        Cuando hay duda, usamos 'conversacion' y dejamos que el agente lo maneje.
        
        Args:
            user_message: Mensaje del usuario
            session_context: Contexto conversacional
            user_stats: Estadísticas del usuario
            
        Returns:
            Prompt formateado
        """
        prompt_parts = [
            "Eres un analizador de intenciones para un asistente musical.",
            "",
            f"MENSAJE DEL USUARIO: \"{user_message}\"",
            ""
        ]
        
        # Agregar contexto si existe
        if session_context:
            prompt_parts.extend([
                "CONTEXTO DE LA CONVERSACIÓN:",
                session_context,
                ""
            ])
        
        # Agregar stats del usuario si existen
        if user_stats:
            top_artists = user_stats.get('top_artists', [])
            if top_artists:
                prompt_parts.extend([
                    "TOP ARTISTAS DEL USUARIO:",
                    ", ".join(top_artists[:5]),
                    ""
                ])
        
        prompt_parts.extend([
            "FILOSOFÍA:",
            "El agente conversacional es MUY inteligente y puede manejar CUALQUIER consulta.",
            "Tu trabajo es detectar SOLO las intenciones MUY OBVIAS que requieren acciones específicas.",
            "Cuando tengas duda, usa 'conversacion' y deja que el agente lo maneje.",
            "",
            "INTENCIONES DISPONIBLES (solo 5):",
            "",
            "1. 'playlist' - SOLO cuando pide EXPLÍCITAMENTE crear una playlist M3U",
            "   Palabras clave: 'haz playlist', 'crea playlist', 'genera playlist'",
            "   Ejemplo: 'haz playlist de Pink Floyd y Queen'",
            "",
            "2. 'buscar' - SOLO cuando usa la palabra 'busca' o 'buscar'",
            "   Palabras clave: 'busca', 'buscar'",
            "   Ejemplo: 'busca Queen'",
            "",
            "3. 'recomendar' - SOLO cuando dice 'similar a' Y menciona artista específico",
            "   Palabras clave: 'similar a [artista]', 'parecido a [artista]'",
            "   Ejemplo: 'similar a Pink Floyd'",
            "   NOTA: 'recomiéndame rock' → usa 'conversacion', NO 'recomendar'",
            "",
            "4. 'referencia' - SOLO cuando dice 'más de eso', 'otro así' SIN mencionar artista",
            "   Palabras clave: 'más de eso', 'otro así', 'ponme otro'",
            "   Ejemplo: 'ponme más de eso'",
            "",
            "5. 'conversacion' - TODO LO DEMÁS (usar por defecto, 95% de los casos)",
            "   Incluye:",
            "   - Preguntas: 'mis stats', 'últimos artistas', 'qué escuché', 'qué tengo de X'",
            "   - Solicitudes: 'recomiéndame rock', 'ponme un disco', 'música tranquila'",
            "   - Info: '¿qué es el jazz?', 'cuéntame de Queen'",
            "   - CUALQUIER conversación natural",
            "",
            "REGLA DE ORO:",
            "Si tienes CUALQUIER duda → usa 'conversacion'",
            "El agente conversacional es experto y puede manejar TODO.",
            "",
            "EJEMPLOS:",
            "",
            "Usuario: 'haz playlist con Pink Floyd y Queen'",
            '{"intent": "playlist", "params": {"description": "Pink Floyd y Queen"}, "confidence": 0.95}',
            "",
            "Usuario: 'busca Queen'",
            '{"intent": "buscar", "params": {"search_query": "Queen"}, "confidence": 0.95}',
            "",
            "Usuario: 'similar a Pink Floyd'",
            '{"intent": "recomendar", "params": {"similar_to": "Pink Floyd"}, "confidence": 0.9}',
            "",
            "Usuario: 'ponme más de eso'",
            '{"intent": "referencia", "params": {"reference_to_previous": true}, "confidence": 0.85}',
            "",
            "--- TODO LO DEMÁS ES CONVERSACION ---",
            "",
            "Usuario: 'recomiéndame un disco'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.9}',
            "",
            "Usuario: 'recomiéndame rock progresivo'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.9}',
            "",
            "Usuario: '¿cuáles son los últimos 3 artistas que escuché?'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.95}',
            "",
            "Usuario: 'mis estadísticas'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.95}',
            "",
            "Usuario: '¿qué álbumes tengo de Radiohead?'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.95}',
            "",
            "Usuario: '¿qué es el jazz?'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.95}',
            "",
            "Usuario: 'ponme algo tranquilo'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.9}',
            "",
            "Usuario: '¿cuál es mi última canción?'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.95}',
            "",
            "Usuario: 'qué he escuchado hoy'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.95}',
            "",
            "Usuario: 'un disco de Oasis'",
            '{"intent": "conversacion", "params": {}, "confidence": 0.9}',
            "",
            "RESPONDE SOLO CON JSON (sin markdown, sin explicaciones):",
            '{"intent": "...", "params": {...}, "confidence": 0.0-1.0}'
        ])
        
        return "\n".join(prompt_parts)
    
    def _validate_and_normalize(self, intent_data: Dict) -> Dict[str, Any]:
        """Validar y normalizar datos de intención
        
        Args:
            intent_data: Datos crudos de intención
            
        Returns:
            Datos validados y normalizados
        """
        # Validar campos requeridos
        intent = intent_data.get("intent", "conversacion")
        params = intent_data.get("params", {})
        confidence = float(intent_data.get("confidence", 0.5))
        
        # Normalizar intención - SOLO 5 intenciones válidas
        valid_intents = [
            "playlist", "buscar", "recomendar", "referencia", "conversacion"
        ]
        
        if intent not in valid_intents:
            logger.warning(f"Intención inválida '{intent}', usando 'conversacion'")
            intent = "conversacion"
        
        # Normalizar parámetros
        normalized_params = {}
        
        # Artistas
        if "artists" in params and isinstance(params["artists"], list):
            normalized_params["artists"] = [str(a).strip() for a in params["artists"] if a]
        
        # Géneros
        if "genres" in params and isinstance(params["genres"], list):
            normalized_params["genres"] = [str(g).strip() for g in params["genres"] if g]
        
        # Tipo
        if "type" in params:
            type_val = str(params["type"]).lower()
            if type_val in ["album", "artist", "track"]:
                normalized_params["type"] = type_val
        
        # Similar to
        if "similar_to" in params and params["similar_to"]:
            normalized_params["similar_to"] = str(params["similar_to"]).strip()
        
        # Reference to previous
        if "reference_to_previous" in params:
            normalized_params["reference_to_previous"] = bool(params["reference_to_previous"])
        
        # Description
        if "description" in params and params["description"]:
            normalized_params["description"] = str(params["description"]).strip()
        
        # Search query
        if "search_query" in params and params["search_query"]:
            normalized_params["search_query"] = str(params["search_query"]).strip()
        
        # Mood
        if "mood" in params and params["mood"]:
            normalized_params["mood"] = str(params["mood"]).strip()
        
        # Time period
        if "time_period" in params and params["time_period"]:
            normalized_params["time_period"] = str(params["time_period"]).strip()
        
        # Count
        if "count" in params:
            try:
                count = int(params["count"])
                normalized_params["count"] = max(1, min(count, 20))  # Entre 1 y 20
            except (ValueError, TypeError):
                normalized_params["count"] = 5
        
        # Timeframe
        if "timeframe" in params and params["timeframe"]:
            normalized_params["timeframe"] = str(params["timeframe"]).strip()
        
        # Question
        if "question" in params and params["question"]:
            normalized_params["question"] = str(params["question"]).strip()
        
        # Copiar cualquier otro parámetro que no hayamos procesado
        for key, value in params.items():
            if key not in normalized_params:
                normalized_params[key] = value
        
        return {
            "intent": intent,
            "params": normalized_params,
            "confidence": confidence
        }
    
    def get_intent_description(self, intent: str) -> str:
        """Obtener descripción legible de una intención
        
        Args:
            intent: Nombre de la intención
            
        Returns:
            Descripción en español
        """
        descriptions = {
            "playlist": "Crear playlist M3U",
            "buscar": "Buscar en biblioteca",
            "recomendar": "Música similar a artista",
            "referencia": "Referencia a algo anterior",
            "conversacion": "Conversación general (maneja TODO lo demás)"
        }
        
        return descriptions.get(intent, "Conversación general")

