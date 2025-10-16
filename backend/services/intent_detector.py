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
            "INSTRUCCIONES:",
            "Analiza el mensaje y determina:",
            "1. La intención principal (intent)",
            "2. Los parámetros relevantes (params)",
            "3. Tu nivel de confianza (confidence: 0.0 a 1.0)",
            "",
            "INTENCIONES DISPONIBLES:",
            "- 'recomendar': Usuario quiere recomendaciones de música (álbumes, artistas, canciones)",
            "- 'playlist': Usuario quiere crear una playlist M3U con criterios específicos",
            "- 'buscar': Usuario quiere buscar algo específico en su biblioteca",
            "- 'info': Usuario pregunta por información de un artista/álbum específico",
            "- 'stats': Usuario quiere ver sus estadísticas de escucha",
            "- 'biblioteca': Usuario quiere explorar su biblioteca completa",
            "- 'pregunta_general': Pregunta teórica sobre música (no relacionada con su biblioteca)",
            "- 'conversacion': Conversación general, consulta sobre su música personal",
            "- 'referencia': Usuario hace referencia a algo anterior ('más así', 'otro como ese')",
            "",
            "PARÁMETROS IMPORTANTES:",
            "- artists: Lista de artistas mencionados específicamente",
            "- genres: Lista de géneros mencionados",
            "- type: 'album', 'artist', 'track' (solo para recomendaciones)",
            "- similar_to: Nombre del artista/álbum para buscar similares",
            "- reference_to_previous: true si se refiere a algo anterior",
            "- description: Descripción completa para playlists o criterios específicos",
            "- search_query: Término de búsqueda específico",
            "- mood: Estado de ánimo si se menciona (energetic, calm, melancholic, etc.)",
            "- time_period: Si menciona época ('70s', '90s', 'actual', etc.)",
            "- count: Número de items solicitados (por defecto 5)",
            "",
            "REGLAS CRÍTICAS:",
            "1. Si pide 'disco DE [artista]' o 'álbum DE [artista]' → intent='info' (busca en SU biblioteca)",
            "2. Si pide 'similar A [artista]' o 'parecido A [artista]' → intent='recomendar' con similar_to",
            "3. Si dice 'más de eso', 'otro así', 'parecido' SIN nombre → intent='referencia'",
            "4. Si pide 'playlist con/de [artistas]' → intent='playlist' con description",
            "5. Si menciona múltiples características → incluir TODO en description",
            "6. Si pide 'un' álbum/disco (singular) → count=1, type='album'",
            "7. Si pregunta '¿qué tengo de...?' → intent='info' o 'conversacion'",
            "",
            "EJEMPLOS:",
            "",
            "Usuario: 'recomiéndame un disco'",
            '{"intent": "recomendar", "params": {"type": "album", "count": 1}, "confidence": 0.95}',
            "",
            "Usuario: 'recomiéndame un álbum de Oasis'",
            '{"intent": "info", "params": {"artists": ["Oasis"], "type": "album"}, "confidence": 0.9}',
            "",
            "Usuario: 'música similar a Pink Floyd'",
            '{"intent": "recomendar", "params": {"similar_to": "Pink Floyd"}, "confidence": 0.95}',
            "",
            "Usuario: 'ponme algo parecido' (después de recomendar Queen)",
            '{"intent": "referencia", "params": {"reference_to_previous": true}, "confidence": 0.85}',
            "",
            "Usuario: 'haz playlist con Pink Floyd y Queen'",
            '{"intent": "playlist", "params": {"description": "Pink Floyd y Queen", "artists": ["Pink Floyd", "Queen"]}, "confidence": 0.9}',
            "",
            "Usuario: 'rock progresivo de los 70s con sintetizadores'",
            '{"intent": "recomendar", "params": {"description": "rock progresivo de los 70s con sintetizadores", "genres": ["rock progresivo"], "time_period": "70s"}, "confidence": 0.9}',
            "",
            "Usuario: 'qué he escuchado hoy'",
            '{"intent": "stats", "params": {"timeframe": "today"}, "confidence": 0.95}',
            "",
            "Usuario: 'busca Queen'",
            '{"intent": "buscar", "params": {"search_query": "Queen"}, "confidence": 0.95}',
            "",
            "Usuario: '¿qué es el jazz?'",
            '{"intent": "pregunta_general", "params": {"question": "qué es el jazz"}, "confidence": 0.95}',
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
        
        # Normalizar intención
        valid_intents = [
            "recomendar", "playlist", "buscar", "info", "stats", 
            "biblioteca", "pregunta_general", "conversacion", "referencia"
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
            "recomendar": "Recomendaciones de música",
            "playlist": "Crear playlist personalizada",
            "buscar": "Buscar en biblioteca",
            "info": "Información de artista/álbum",
            "stats": "Ver estadísticas de escucha",
            "biblioteca": "Explorar biblioteca completa",
            "pregunta_general": "Pregunta sobre música",
            "conversacion": "Conversación general",
            "referencia": "Referencia a algo anterior"
        }
        
        return descriptions.get(intent, "Acción desconocida")

