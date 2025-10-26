"""
Sistema de detección de intenciones mejorado con contexto enriquecido
y análisis de sentimiento
"""
import google.generativeai as genai
import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analizador de sentimiento para mensajes de usuario"""
    
    def __init__(self):
        self.sentiment_keywords = {
            'positive': [
                'gracias', 'perfecto', 'excelente', 'genial', 'me gusta', 'love', 'amazing',
                'increíble', 'fantástico', 'maravilloso', 'bueno', 'bien', 'sí', 'yes'
            ],
            'negative': [
                'no me gusta', 'odio', 'hate', 'malo', 'terrible', 'horrible', 'no', 'no',
                'dislike', 'aburrido', 'boring', 'mal', 'pésimo', 'fatal'
            ],
            'neutral': [
                'ok', 'vale', 'bien', 'okay', 'entendido', 'claro', 'sí', 'si'
            ],
            'excited': [
                '¡wow!', 'increíble', 'amazing', 'fantástico', 'genial', 'perfecto',
                'excelente', 'maravilloso', 'increíble', 'wow', 'omg'
            ],
            'frustrated': [
                'no funciona', 'error', 'problema', 'no entiendo', 'confuso', 'difícil',
                'complicado', 'no sirve', 'falla', 'bug'
            ]
        }
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analizar sentimiento del texto"""
        text_lower = text.lower()
        
        # Contar palabras clave por categoría
        sentiment_scores = {}
        for category, keywords in self.sentiment_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            sentiment_scores[category] = score
        
        # Determinar sentimiento dominante
        dominant_sentiment = max(sentiment_scores.items(), key=lambda x: x[1])
        
        # Calcular intensidad
        total_keywords = sum(sentiment_scores.values())
        intensity = min(total_keywords / 3, 1.0) if total_keywords > 0 else 0.0
        
        return {
            'sentiment': dominant_sentiment[0] if dominant_sentiment[1] > 0 else 'neutral',
            'intensity': intensity,
            'scores': sentiment_scores,
            'confidence': min(dominant_sentiment[1] / 2, 1.0) if dominant_sentiment[1] > 0 else 0.0
        }


class ContextAnalyzer:
    """Analizador de contexto conversacional"""
    
    def __init__(self):
        self.context_patterns = {
            'question': [
                r'\?', r'¿', r'qué', r'que', r'cuál', r'cual', r'cuando', r'cuándo',
                r'como', r'cómo', r'por qué', r'porque', r'where', r'what', r'how', r'why'
            ],
            'request': [
                r'por favor', r'please', r'puedes', r'can you', r'quiero', r'i want',
                r'necesito', r'i need', r'dame', r'give me', r'muéstrame', r'show me'
            ],
            'command': [
                r'busca', r'search', r'encuentra', r'find', r'crea', r'create',
                r'haz', r'make', r'genera', r'generate', r'recomienda', r'recommend'
            ],
            'reference': [
                r'más de eso', r'more of that', r'otro así', r'another like that',
                r'similar', r'parecido', r'like this', r'como este'
            ],
            'urgency': [
                r'urgente', r'urgent', r'ya', r'now', r'inmediatamente', r'immediately',
                r'pronto', r'soon', r'asap', r'rapidamente', r'quickly'
            ]
        }
    
    def analyze_context(self, text: str, session_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analizar contexto del mensaje"""
        text_lower = text.lower()
        
        # Detectar patrones de contexto
        context_scores = {}
        for context_type, patterns in self.context_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            context_scores[context_type] = score
        
        # Determinar tipo de contexto dominante
        dominant_context = max(context_scores.items(), key=lambda x: x[1])
        
        # Análisis de urgencia
        urgency_level = 'low'
        if context_scores.get('urgency', 0) > 0:
            urgency_level = 'high'
        elif any(word in text_lower for word in ['rápido', 'quick', 'pronto', 'soon']):
            urgency_level = 'medium'
        
        # Análisis de referencia a conversación anterior
        has_reference = context_scores.get('reference', 0) > 0
        if session_context and session_context.get('last_recommendations'):
            has_reference = True
        
        return {
            'context_type': dominant_context[0] if dominant_context[1] > 0 else 'general',
            'urgency': urgency_level,
            'has_reference': has_reference,
            'scores': context_scores,
            'confidence': min(dominant_context[1] / 2, 1.0) if dominant_context[1] > 0 else 0.0
        }


class MusicContextExtractor:
    """Extractor de contexto musical específico"""
    
    def __init__(self):
        self.music_keywords = {
            'genres': [
                'rock', 'pop', 'jazz', 'classical', 'electronic', 'hip hop', 'rap',
                'country', 'blues', 'reggae', 'folk', 'metal', 'punk', 'indie',
                'progressive', 'alternative', 'ambient', 'techno', 'house', 'trance'
            ],
            'time_periods': [
                '60s', '70s', '80s', '90s', '2000s', '2010s', '2020s',
                'años 60', 'años 70', 'años 80', 'años 90', 'década',
                'sixties', 'seventies', 'eighties', 'nineties'
            ],
            'moods': [
                'tranquilo', 'calm', 'relajante', 'relaxing', 'energético', 'energetic',
                'triste', 'sad', 'feliz', 'happy', 'melancólico', 'melancholic',
                'romántico', 'romantic', 'agresivo', 'aggressive', 'suave', 'soft'
            ],
            'activities': [
                'estudiar', 'study', 'trabajar', 'work', 'correr', 'run', 'gym',
                'conducir', 'drive', 'cocinar', 'cook', 'dormir', 'sleep',
                'fiesta', 'party', 'relajarse', 'relax'
            ],
            'instruments': [
                'guitarra', 'guitar', 'piano', 'batería', 'drums', 'bajo', 'bass',
                'violín', 'violin', 'saxofón', 'saxophone', 'trompeta', 'trumpet'
            ]
        }
    
    def extract_music_context(self, text: str) -> Dict[str, Any]:
        """Extraer contexto musical del texto"""
        text_lower = text.lower()
        
        extracted_context = {
            'genres': [],
            'time_periods': [],
            'moods': [],
            'activities': [],
            'instruments': [],
            'artists_mentioned': [],
            'albums_mentioned': [],
            'songs_mentioned': []
        }
        
        # Extraer géneros
        for genre in self.music_keywords['genres']:
            if genre in text_lower:
                extracted_context['genres'].append(genre)
        
        # Extraer períodos de tiempo
        for period in self.music_keywords['time_periods']:
            if period in text_lower:
                extracted_context['time_periods'].append(period)
        
        # Extraer estados de ánimo
        for mood in self.music_keywords['moods']:
            if mood in text_lower:
                extracted_context['moods'].append(mood)
        
        # Extraer actividades
        for activity in self.music_keywords['activities']:
            if activity in text_lower:
                extracted_context['activities'].append(activity)
        
        # Extraer instrumentos
        for instrument in self.music_keywords['instruments']:
            if instrument in text_lower:
                extracted_context['instruments'].append(instrument)
        
        # Detectar menciones de artistas, álbumes o canciones (patrones básicos)
        artist_patterns = [
            r'de\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "de Pink Floyd"
            r'artista\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "artista Queen"
            r'grupo\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'  # "grupo The Beatles"
        ]
        
        for pattern in artist_patterns:
            matches = re.findall(pattern, text)
            extracted_context['artists_mentioned'].extend(matches)
        
        return extracted_context


class EnhancedIntentDetector:
    """Detector de intenciones mejorado con contexto enriquecido"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Componentes de análisis
        self.sentiment_analyzer = SentimentAnalyzer()
        self.context_analyzer = ContextAnalyzer()
        self.music_extractor = MusicContextExtractor()
        
        # Configuración
        self.intent_confidence_threshold = 0.7
        self.fallback_intent = "conversacion"
        
        logger.info("✅ EnhancedIntentDetector inicializado")
    
    async def detect_intent(
        self, 
        user_message: str,
        session_context: Optional[Dict] = None,
        user_stats: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Detectar intención con análisis de contexto enriquecido"""
        
        try:
            logger.debug(f"🔍 Analizando intención para: '{user_message}'")
            
            # Análisis de sentimiento
            sentiment = self.sentiment_analyzer.analyze_sentiment(user_message)
            
            # Análisis de contexto
            context = self.context_analyzer.analyze_context(user_message, session_context)
            
            # Extracción de contexto musical
            music_context = self.music_extractor.extract_music_context(user_message)
            
            # Construir prompt enriquecido
            prompt = self._build_enhanced_prompt(
                user_message, 
                session_context, 
                user_stats,
                sentiment,
                context,
                music_context
            )
            
            # Generar respuesta con múltiples intentos
            for attempt in range(3):
                try:
                    response = await self.model.generate_content_async(prompt)
                    response_text = response.text.strip()
                    
                    # Limpiar markdown si existe
                    if response_text.startswith("```"):
                        response_text = response_text.replace("```json", "").replace("```", "").strip()
                    
                    # Parsear JSON
                    intent_data = json.loads(response_text)
                    
                    # Validar y enriquecer con análisis local
                    enriched_intent = self._enrich_intent_data(
                        intent_data, 
                        sentiment, 
                        context, 
                        music_context
                    )
                    
                    logger.info(f"✅ Intención detectada: {enriched_intent.get('intent')} (confianza: {enriched_intent.get('confidence', 0)})")
                    return enriched_intent
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Error parseando JSON (intento {attempt + 1}): {e}")
                    if attempt == 2:  # Último intento
                        return self._create_fallback_intent(user_message, sentiment, context, music_context)
                except Exception as e:
                    logger.warning(f"⚠️ Error en intento {attempt + 1}: {e}")
                    if attempt == 2:
                        return self._create_fallback_intent(user_message, sentiment, context, music_context)
            
        except Exception as e:
            logger.error(f"❌ Error detectando intención: {e}")
            return self._create_fallback_intent(user_message, {}, {}, {})
    
    def _build_enhanced_prompt(
        self, 
        user_message: str, 
        session_context: Optional[Dict],
        user_stats: Optional[Dict],
        sentiment: Dict[str, Any],
        context: Dict[str, Any],
        music_context: Dict[str, Any]
    ) -> str:
        """Construir prompt enriquecido con análisis de contexto"""
        
        prompt_parts = [
            "Eres un analizador de intenciones avanzado para un asistente musical.",
            "",
            f"MENSAJE DEL USUARIO: \"{user_message}\"",
            ""
        ]
        
        # Análisis de sentimiento
        prompt_parts.extend([
            "ANÁLISIS DE SENTIMIENTO:",
            f"- Sentimiento: {sentiment.get('sentiment', 'neutral')}",
            f"- Intensidad: {sentiment.get('intensity', 0):.2f}",
            f"- Confianza: {sentiment.get('confidence', 0):.2f}",
            ""
        ])
        
        # Análisis de contexto
        prompt_parts.extend([
            "ANÁLISIS DE CONTEXTO:",
            f"- Tipo: {context.get('context_type', 'general')}",
            f"- Urgencia: {context.get('urgency', 'low')}",
            f"- Tiene referencia: {context.get('has_reference', False)}",
            ""
        ])
        
        # Contexto musical
        if any(music_context.values()):
            prompt_parts.extend([
                "CONTEXTO MUSICAL DETECTADO:",
                f"- Géneros: {', '.join(music_context.get('genres', []))}",
                f"- Períodos: {', '.join(music_context.get('time_periods', []))}",
                f"- Estados de ánimo: {', '.join(music_context.get('moods', []))}",
                f"- Actividades: {', '.join(music_context.get('activities', []))}",
                f"- Instrumentos: {', '.join(music_context.get('instruments', []))}",
                f"- Artistas mencionados: {', '.join(music_context.get('artists_mentioned', []))}",
                ""
            ])
        
        # Contexto de sesión
        if session_context:
            prompt_parts.extend([
                "CONTEXTO DE SESIÓN:",
                session_context,
                ""
            ])
        
        # Stats del usuario
        if user_stats:
            top_artists = user_stats.get('top_artists', [])
            if top_artists:
                prompt_parts.extend([
                    "TOP ARTISTAS DEL USUARIO:",
                    ", ".join(top_artists[:5]),
                    ""
                ])
        
        # Instrucciones de detección
        prompt_parts.extend([
            "INSTRUCCIONES DE DETECCIÓN:",
            "Usa TODA la información de contexto para hacer una detección más precisa.",
            "Considera el sentimiento, urgencia y contexto musical en tu decisión.",
            "",
            "INTENCIONES DISPONIBLES (solo 7):",
            "",
            "1. 'playlist' - SOLO cuando pide EXPLÍCITAMENTE crear una playlist M3U",
            "   Palabras clave: 'haz playlist', 'crea playlist', 'genera playlist'",
            "   Ejemplo: 'haz playlist de Pink Floyd y Queen'",
            "",
            "2. 'buscar' - SOLO cuando usa la palabra 'busca' o 'buscar' (pero NO 'busca más')",
            "   Palabras clave: 'busca', 'buscar'",
            "   Ejemplo: 'busca Queen'",
            "   EXCEPCIÓN: 'busca más', 'buscar más' → usar 'conversacion'",
            "",
            "3. 'recomendar' - SOLO cuando dice 'similar a' Y menciona artista específico",
            "   Palabras clave: 'similar a [artista]', 'parecido a [artista]'",
            "   Ejemplo: 'similar a Pink Floyd'",
            "   NOTA: 'recomiéndame rock' → usa 'conversacion', NO 'recomendar'",
            "",
            "4. 'recomendar_biblioteca' - SOLO cuando pide recomendaciones DE SU BIBLIOTECA",
            "   Palabras clave: 'de mi biblioteca', 'de la biblioteca', 'que tengo', 'redescubrir'",
            "   Ejemplo: 'recomiéndame algo de mi biblioteca'",
            "",
            "5. 'referencia' - SOLO cuando dice 'más de eso', 'otro así' SIN mencionar artista",
            "   Palabras clave: 'más de eso', 'otro así', 'ponme otro'",
            "   Ejemplo: 'ponme más de eso'",
            "",
            "6. 'releases' - SOLO cuando pregunta por LANZAMIENTOS RECIENTES o música NUEVA",
            "   Palabras clave: 'lanzamientos', 'releases', 'nuevo', 'nueva', 'nuevos', 'nuevas'",
            "   Ejemplos: '¿qué hay nuevo?', 'lanzamientos recientes', 'música nueva'",
            "",
            "7. 'conversacion' - TODO LO DEMÁS (usar por defecto, 90% de los casos)",
            "   Incluye: preguntas, solicitudes generales, info, CUALQUIER conversación natural",
            "",
            "FACTORES DE CONTEXTO A CONSIDERAR:",
            "- Si el usuario está frustrado (sentiment: frustrated) → priorizar 'conversacion'",
            "- Si hay urgencia alta → ajustar confidence según la urgencia",
            "- Si hay contexto musical específico → usar en los parámetros",
            "- Si hay referencia a conversación anterior → considerar 'referencia'",
            "",
            "RESPONDE SOLO CON JSON (sin markdown, sin explicaciones):",
            '{"intent": "...", "params": {...}, "confidence": 0.0-1.0, "reasoning": "breve explicación"}'
        ])
        
        return "\n".join(prompt_parts)
    
    def _enrich_intent_data(
        self, 
        intent_data: Dict[str, Any], 
        sentiment: Dict[str, Any],
        context: Dict[str, Any],
        music_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enriquecer datos de intención con análisis local"""
        
        # Validar campos requeridos
        intent = intent_data.get("intent", "conversacion")
        params = intent_data.get("params", {})
        confidence = float(intent_data.get("confidence", 0.5))
        reasoning = intent_data.get("reasoning", "")
        
        # Ajustar confianza basada en análisis local
        confidence_adjustment = 0.0
        
        # Si hay contexto musical específico, aumentar confianza
        if any(music_context.values()):
            confidence_adjustment += 0.1
        
        # Si el sentimiento es claro, ajustar confianza
        if sentiment.get('confidence', 0) > 0.5:
            confidence_adjustment += 0.05
        
        # Si hay urgencia, ajustar confianza
        if context.get('urgency') == 'high':
            confidence_adjustment += 0.1
        
        # Aplicar ajuste
        confidence = min(confidence + confidence_adjustment, 1.0)
        
        # Enriquecer parámetros con contexto musical
        if music_context.get('genres'):
            params['genres'] = music_context['genres']
        
        if music_context.get('moods'):
            params['mood'] = music_context['moods'][0]  # Tomar el primer mood
        
        if music_context.get('activities'):
            params['activity'] = music_context['activities'][0]
        
        if music_context.get('artists_mentioned'):
            params['artists'] = music_context['artists_mentioned']
        
        # Agregar información de contexto
        params['sentiment'] = sentiment.get('sentiment', 'neutral')
        params['urgency'] = context.get('urgency', 'low')
        params['has_reference'] = context.get('has_reference', False)
        
        return {
            "intent": intent,
            "params": params,
            "confidence": confidence,
            "reasoning": reasoning,
            "analysis": {
                "sentiment": sentiment,
                "context": context,
                "music_context": music_context
            }
        }
    
    def _create_fallback_intent(
        self, 
        user_message: str, 
        sentiment: Dict[str, Any],
        context: Dict[str, Any],
        music_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crear intención de fallback con análisis local"""
        
        # Análisis básico para determinar intención más probable
        text_lower = user_message.lower()
        
        # Detectar patrones básicos
        if any(word in text_lower for word in ['playlist', 'lista']):
            intent = "playlist"
            confidence = 0.6
        elif any(word in text_lower for word in ['busca', 'buscar']):
            intent = "buscar"
            confidence = 0.6
        elif any(word in text_lower for word in ['similar', 'parecido']):
            intent = "recomendar"
            confidence = 0.6
        elif any(word in text_lower for word in ['biblioteca', 'tengo']):
            intent = "recomendar_biblioteca"
            confidence = 0.6
        elif any(word in text_lower for word in ['más de eso', 'otro así']):
            intent = "referencia"
            confidence = 0.6
        elif any(word in text_lower for word in ['nuevo', 'lanzamientos']):
            intent = "releases"
            confidence = 0.6
        else:
            intent = "conversacion"
            confidence = 0.8
        
        return {
            "intent": intent,
            "params": {
                "sentiment": sentiment.get('sentiment', 'neutral'),
                "urgency": context.get('urgency', 'low'),
                "has_reference": context.get('has_reference', False)
            },
            "confidence": confidence,
            "reasoning": "Fallback basado en análisis local",
            "analysis": {
                "sentiment": sentiment,
                "context": context,
                "music_context": music_context
            }
        }
    
    def get_intent_description(self, intent: str) -> str:
        """Obtener descripción legible de una intención"""
        descriptions = {
            "playlist": "Crear playlist M3U",
            "buscar": "Buscar en biblioteca",
            "recomendar": "Música similar a artista",
            "recomendar_biblioteca": "Recomendaciones de biblioteca (redescubrimiento)",
            "referencia": "Referencia a algo anterior",
            "releases": "Lanzamientos recientes y música nueva",
            "conversacion": "Conversación general (maneja TODO lo demás)"
        }
        
        return descriptions.get(intent, "Conversación general")
