from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from typing import List, Dict, Any, Optional
import os
import json
import random
import google.generativeai as genai
from models.schemas import Recommendation, Track, ScrobbleTrack, ScrobbleArtist
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.ai_service import MusicRecommendationService
from services.playlist_service import PlaylistService
from services.music_agent_service import MusicAgentService
from services.conversation_manager import ConversationManager
from services.intent_detector import IntentDetector
from services.enhanced_intent_detector import EnhancedIntentDetector
from services.system_prompts import SystemPrompts
from services.analytics_system import analytics_system
from functools import wraps
from datetime import datetime
import time

class TelegramService:
    def __init__(self):
        self.navidrome = NavidromeService()
        self.listenbrainz = ListenBrainzService()
        self.ai = MusicRecommendationService()
        self.playlist_service = PlaylistService()
        self.agent = MusicAgentService()
        
        # Nuevos componentes conversacionales
        self.conversation_manager = ConversationManager()
        self.intent_detector = IntentDetector()
        self.enhanced_intent_detector = EnhancedIntentDetector()
        
        # Configurar lista de usuarios permitidos
        allowed_ids_str = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        if allowed_ids_str.strip():
            try:
                self.allowed_user_ids = [int(uid.strip()) for uid in allowed_ids_str.split(',') if uid.strip()]
                print(f"🔒 Bot configurado en modo privado para {len(self.allowed_user_ids)} usuario(s)")
            except ValueError as e:
                print(f"⚠️ Error parseando TELEGRAM_ALLOWED_USER_IDS: {e}")
                print(f"⚠️ Usando modo público (sin restricciones)")
                self.allowed_user_ids = []
        else:
            self.allowed_user_ids = []
            print("⚠️ Bot en modo público - cualquier usuario puede usarlo")
            print("💡 Para hacerlo privado, configura TELEGRAM_ALLOWED_USER_IDS en .env")
        
        # Usar ListenBrainz para datos de escucha y descubrimiento
        if os.getenv("LISTENBRAINZ_USERNAME"):
            self.music_service = self.listenbrainz
            self.music_service_name = "ListenBrainz"
            print("✅ Usando ListenBrainz para datos de escucha y descubrimiento")
        else:
            self.music_service = None
            self.music_service_name = None
            print("⚠️ No hay servicio de scrobbling configurado. Por favor configura LISTENBRAINZ_USERNAME en .env")
    
    def track_analytics(interaction_type: str):
        """Decorador para tracking automático de analytics"""
        def decorator(func):
            @wraps(func)
            async def wrapper(self, update, context, *args, **kwargs):
                user_id = update.effective_user.id
                start_time = time.time()
                success = True
                error_message = None
                
                try:
                    result = await func(self, update, context, *args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    raise
                finally:
                    # Calcular duración
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Tracking de analytics
                    await analytics_system.track_interaction(
                        user_id=user_id,
                        interaction_type=interaction_type,
                        duration_ms=duration_ms,
                        success=success,
                        error_message=error_message
                    )
            
            return wrapper
        return decorator
    
    def _is_user_allowed(self, user_id: int) -> bool:
        """Verifica si un usuario está autorizado para usar el bot"""
        # Si no hay lista de usuarios permitidos, todos están permitidos
        if not self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids
    
    def _check_authorization(func):
        """Decorador para verificar autorización de usuario"""
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            if not self._is_user_allowed(user_id):
                print(f"🚫 Acceso denegado para usuario {username} (ID: {user_id})")
                await update.message.reply_text(
                    "🚫 <b>Acceso Denegado</b>\n\n"
                    "Este bot es privado y solo puede ser usado por usuarios autorizados.\n\n"
                    f"Tu ID de usuario es: <code>{user_id}</code>\n\n"
                    "Si crees que deberías tener acceso, contacta con el administrador del bot "
                    "y proporciona tu ID de usuario.",
                    parse_mode='HTML'
                )
                return
            
            # Usuario autorizado, ejecutar función
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    
    @_check_authorization
    @track_analytics("command")
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Bienvenida del bot"""
        welcome_text = """🎵 <b>¡Bienvenido a Musicalo!</b>

Soy tu asistente personal de música con IA que entiende lenguaje natural. Puedes hablarme directamente o usar comandos.

<b>✨ Nuevo: Habla conmigo naturalmente</b>
Ya no necesitas recordar comandos. Escribe lo que quieras:
• "Recomiéndame música rock"
• "Busca Queen en mi biblioteca"
• "Muéstrame mis estadísticas"
• "¿Qué álbumes tengo de Pink Floyd?"
• "¿Qué estoy escuchando?"

<b>🎨 Sé específico en tus peticiones:</b>
Puedes dar todos los detalles que quieras:
• "Rock progresivo de los 70s con sintetizadores"
• "Música energética para hacer ejercicio"
• "Jazz suave para estudiar"
• "Metal melódico con voces limpias"

<b>📝 Comandos disponibles:</b>
/recommend - Obtener recomendaciones personalizadas
/playlist &lt;descripción&gt; - Crear playlist M3U 🎵
/share &lt;nombre&gt; - Compartir música con enlace público 🔗
/nowplaying - Ver qué se está reproduciendo ahora 🎧
/library - Explorar tu biblioteca musical
/stats - Ver estadísticas de escucha
/releases [week/month/year] - Lanzamientos recientes 🆕
/search &lt;término&gt; - Buscar música en tu biblioteca
/help - Mostrar ayuda

<b>¿Cómo funciona?</b>
Analizo tu actividad en ListenBrainz y tu biblioteca de Navidrome para sugerirte música que realmente te gustará. Uso MusicBrainz para descubrir artistas relacionados y obtener metadatos detallados.

¡Simplemente escríbeme lo que necesites! 🎶"""
        
        keyboard = [
            [KeyboardButton("🎵 Recomendaciones"), KeyboardButton("📚 Mi Biblioteca")],
            [KeyboardButton("📊 Estadísticas"), KeyboardButton("🔍 Buscar")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
    
    @_check_authorization
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Ayuda detallada"""
        help_text = """🎵 <b>Musicalo - Guía de Comandos</b>

<b>✨ Lenguaje Natural (NUEVO):</b>
Ahora puedes escribirme directamente sin usar comandos:
• "Recomiéndame álbumes de rock"
• "Busca Queen"
• "Muéstrame mis estadísticas"
• "¿Qué artistas tengo en mi biblioteca?"
• "Crea una playlist de rock progresivo"
• "¿Qué estoy escuchando?"

<b>🎨 Peticiones Específicas (NUEVO):</b>
Sé todo lo detallado que quieras:
• "Rock progresivo de los 70s con sintetizadores"
• "Música energética con buenos solos de guitarra"
• "Álbumes conceptuales melancólicos"
• "Jazz suave para estudiar"
• "Metal melódico con voces limpias"

<b>Comandos principales:</b>
• /recommend - Recomendaciones generales
• /recommend album - Recomendar álbumes
• /recommend artist - Recomendar artistas
• /recommend track - Recomendar canciones
• /playlist &lt;descripción&gt; - Crear playlist M3U 🎵
• /share &lt;nombre&gt; - Compartir música con enlace público 🔗
• /nowplaying - Ver qué se está reproduciendo ahora 🎧
• /library - Ver tu biblioteca musical
• /stats - Estadísticas de escucha
• /releases - Lanzamientos recientes de tus artistas 🆕
• /search &lt;término&gt; - Buscar en tu biblioteca

<b>Recomendaciones con filtros:</b>
• /recommend rock - Música de rock
• /recommend album jazz - Álbumes de jazz
• /recommend artist metal - Artistas de metal
• /recommend track pop - Canciones pop

<b>Recomendaciones similares:</b>
• /recommend similar albertucho - Artistas similares
• /recommend like extremoduro - Música parecida
• /recommend como marea - Alternativa en español

<b>Redescubrir tu biblioteca (🆕):</b>
• /recommend biblioteca - Redescubrir música olvidada
• /recommend biblioteca rock - Rock de tu biblioteca
• /recommend biblioteca album - Álbumes olvidados
💡 Te recomiendo música que YA tienes pero no escuchas

<b>Búsqueda:</b>
• /search queen - Buscar Queen
• /search bohemian rhapsody - Buscar canción

<b>Playlists:</b>
• /playlist rock de los 80s - Playlist de rock ochentero
• /playlist jazz suave - Música jazz relajante
• /playlist 20 canciones de Queen - Playlist con cantidad específica

<b>Compartir música (🆕):</b>
• /share The Dark Side of the Moon - Compartir álbum
• /share Bohemian Rhapsody - Compartir canción
• /share Queen - Compartir todas las canciones del artista
💡 Genera enlace público para reproducción en streaming 🎧

<b>Reproducción actual (🆕):</b>
• /nowplaying - Ver qué se está reproduciendo ahora
💡 Muestra lo que está sonando en TODOS los reproductores conectados al servidor
💡 También puedes preguntar: "¿Qué estoy escuchando?"

<b>Lanzamientos Recientes (🆕):</b>
• /releases - Esta semana (por defecto)
• /releases week - Esta semana
• /releases month - Este mes
• /releases last_month - Últimos 2 meses
• /releases year - Todo el año
• /releases 90 - Días específicos (ej: 90 días)
• /releases Pink Floyd - Últimos 3 releases de un artista
💡 Ve los álbumes y EPs nuevos de artistas en tu biblioteca

<b>Botones interactivos:</b>
• ❤️ Me gusta / 👎 No me gusta
• 🔄 Más recomendaciones (genera nuevas)
• 📚 Ver más (biblioteca)
• 📊 Actualizar (estadísticas)

<b>Servicios:</b>
• ListenBrainz: Análisis de escucha y recomendaciones colaborativas
• MusicBrainz: Metadatos detallados y descubrimiento por relaciones
• Navidrome: Tu biblioteca musical
• Gemini AI: Recomendaciones inteligentes contextuales

<b>💡 Tip:</b> Puedes preguntarme cualquier cosa sobre música directamente, sin usar comandos. ¡Prueba!"""
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    @_check_authorization
    @track_analytics("recommendation")
    async def recommend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /recommend - Generar recomendaciones
        
        Uso:
        - /recommend → Recomendaciones generales
        - /recommend album → Solo álbumes
        - /recommend artist → Solo artistas
        - /recommend track → Solo canciones
        - /recommend rock → Recomendaciones de rock
        - /recommend album metal → Álbumes de metal
        - /recommend biblioteca → Recomendaciones solo de tu biblioteca (redescubrimiento)
        - /recommend biblioteca rock → Recomendaciones de rock de tu biblioteca
        """
        # Parsear argumentos
        rec_type = "general"  # general, album, artist, track
        genre_filter = None
        similar_to = None  # Para búsquedas "similar a..."
        recommendation_limit = 5  # Por defecto
        custom_prompt = None  # Para descripciones específicas
        from_library_only = False  # NUEVO: solo de biblioteca
        
        # Extraer argumentos especiales (vienen de handle_message)
        if context.args:
            for arg in context.args[:]:
                if arg.startswith("__limit="):
                    try:
                        recommendation_limit = int(arg.split("=", 1)[1])
                        context.args.remove(arg)
                    except:
                        pass
                elif arg.startswith("__custom_prompt="):
                    try:
                        custom_prompt = arg.split("=", 1)[1]
                        context.args.remove(arg)
                        print(f"🎨 Custom prompt extraído: {custom_prompt}")
                    except:
                        pass
        
        if context.args:
            args = [arg.lower() for arg in context.args]
            
            # NUEVO: Detectar flag de "biblioteca"/"library"
            if any(word in args for word in ["biblioteca", "library", "lib", "mi", "redescubrir", "redescubrimiento"]):
                from_library_only = True
                # Remover esas palabras de args
                args = [a for a in args if a not in ["biblioteca", "library", "lib", "mi", "redescubrir", "redescubrimiento"]]
                print(f"📚 Modo biblioteca detectado: from_library_only=True")
            
            # Primero detectar tipo de recomendación (puede estar en cualquier posición)
            if any(word in args for word in ["album", "disco", "cd", "álbum"]):
                rec_type = "album"
                args = [a for a in args if a not in ["album", "disco", "cd", "álbum"]]
            elif any(word in args for word in ["artist", "artista", "banda", "grupo"]):
                rec_type = "artist"
                args = [a for a in args if a not in ["artist", "artista", "banda", "grupo"]]
            elif any(word in args for word in ["track", "song", "cancion", "canción", "tema"]):
                rec_type = "track"
                args = [a for a in args if a not in ["track", "song", "cancion", "canción", "tema"]]
            
            # Luego detectar búsquedas "similar a..." o "como..."
            if "similar" in args or "like" in args or "como" in args or "parecido" in args:
                # Encontrar el índice de la palabra clave
                similar_idx = -1
                for keyword in ["similar", "like", "como", "parecido"]:
                    if keyword in args:
                        similar_idx = args.index(keyword)
                        break
                
                if similar_idx >= 0 and similar_idx + 1 < len(args):
                    # Tomar todo después de "similar"
                    similar_to = " ".join(args[similar_idx + 1:])
                    print(f"🔍 Búsqueda de similares a: {similar_to} (tipo: {rec_type})")
            else:
                # Si no hay "similar", el resto son géneros/estilos
                if args:
                    genre_filter = " ".join(args)
        
        # Mensaje personalizado según el tipo
        library_prefix = "📚 de tu biblioteca" if from_library_only else ""
        
        if custom_prompt:
            msg = f"🎨 Analizando tu petición: '{custom_prompt}'"
            if from_library_only:
                msg += " (solo de tu biblioteca)"
            await update.message.reply_text(msg + "...")
        elif similar_to:
            await update.message.reply_text(f"🔍 Buscando música similar a '{similar_to}'...")
        elif rec_type == "album":
            await update.message.reply_text(f"📀 Analizando álbumes{library_prefix}{f' de {genre_filter}' if genre_filter else ''}...")
        elif rec_type == "artist":
            await update.message.reply_text(f"🎤 Buscando artistas{library_prefix}{f' de {genre_filter}' if genre_filter else ''}...")
        elif rec_type == "track":
            await update.message.reply_text(f"🎵 Buscando canciones{library_prefix}{f' de {genre_filter}' if genre_filter else ''}...")
        else:
            if from_library_only:
                await update.message.reply_text("📚 Analizando tu biblioteca para redescubrir música...")
            else:
                await update.message.reply_text("🎵 Analizando tus gustos musicales...")
        
        try:
            recommendations = []
            
            # Si es una búsqueda "similar a...", usar ListenBrainz directamente
            if similar_to:
                print(f"🎯 Usando límite: {recommendation_limit} para similares")
                
                print(f"🔍 Buscando similares a '{similar_to}' en ListenBrainz+MusicBrainz (tipo: {rec_type})...")
                # Buscar más artistas de los necesarios por si algunos no tienen álbumes/tracks
                search_limit = max(30, recommendation_limit * 5)
                # Pasar MusicBrainz como fallback para buscar relaciones de artistas
                similar_artists = await self.listenbrainz.get_similar_artists_from_recording(
                    similar_to, 
                    limit=search_limit,
                    musicbrainz_service=self.agent.musicbrainz
                )
                
                if similar_artists:
                    # Añadir variedad: mezclar los resultados para no siempre mostrar los mismos
                    # Mantener los top 5 pero mezclar el resto
                    top_artists = similar_artists[:5]
                    rest_artists = similar_artists[5:]
                    random.shuffle(rest_artists)
                    mixed_artists = top_artists + rest_artists
                    
                    print(f"🎲 Mezclando artistas para variedad (total: {len(mixed_artists)})")
                    
                    # Crear recomendaciones de los artistas similares
                    # Continuar hasta tener suficientes recomendaciones
                    for similar_artist in mixed_artists:
                        if len(recommendations) >= recommendation_limit:
                            break  # Ya tenemos suficientes recomendaciones
                        from models.schemas import Track
                        
                        title = ""
                        album_name = ""
                        reason = ""
                        artist_url = similar_artist.url if similar_artist.url else ""
                        
                        # Obtener datos específicos según el tipo usando MusicBrainz
                        if rec_type == "album":
                            if self.agent.musicbrainz:
                                top_albums = await self.agent.musicbrainz.get_artist_top_albums(similar_artist.name, limit=1)
                            else:
                                top_albums = []
                            if top_albums:
                                album_data = top_albums[0]
                                album_name = album_data.get("name", similar_artist.name)
                                title = f"{album_name}"  # Solo el nombre del álbum
                                artist_url = album_data.get("url", artist_url)
                                reason = f"📀 Álbum top de {similar_artist.name}, artista similar a {similar_to}"
                                print(f"   📀 Encontrado álbum: {album_name} de {similar_artist.name}")
                            else:
                                # Si no hay álbum disponible, buscar el siguiente artista
                                print(f"   ⚠️ No se encontró álbum para {similar_artist.name}")
                                continue  # Saltar este artista y buscar el siguiente
                        
                        elif rec_type == "track":
                            if self.agent.musicbrainz:
                                top_tracks = await self.agent.musicbrainz.get_artist_top_tracks(similar_artist.name, limit=1)
                            else:
                                top_tracks = []
                            if top_tracks:
                                track_data = top_tracks[0]
                                title = track_data.get("name", f"Música de {similar_artist.name}")
                                artist_url = track_data.get("url", artist_url)
                                reason = f"🎵 Canción top de artista similar a {similar_to}"
                            else:
                                title = f"Música de {similar_artist.name}"
                                reason = f"🎵 Similar a {similar_to}"
                        
                        else:
                            title = similar_artist.name
                            reason = f"🎯 Similar a {similar_to}"
                        
                        track = Track(
                            id=f"listenbrainz_similar_{similar_artist.name.replace(' ', '_')}",
                            title=title,
                            artist=similar_artist.name,
                            album=album_name,
                            duration=None,
                            year=None,
                            genre="",
                            play_count=None,
                            path=artist_url,
                            cover_url=None
                        )
                        
                        from models.schemas import Recommendation
                        recommendation = Recommendation(
                            track=track,
                            reason=reason,
                            confidence=0.9,
                            source="ListenBrainz+MusicBrainz",
                            tags=[]
                        )
                        recommendations.append(recommendation)
                else:
                    await update.message.reply_text(
                        f"😔 No encontré artistas similares a '{similar_to}'\n\n"
                        f"💡 Esto puede pasar si:\n"
                        f"• El artista es muy nuevo o poco conocido\n"
                        f"• ListenBrainz no tiene suficientes datos\n"
                        f"• No hay relaciones registradas en MusicBrainz\n\n"
                        f"Puedes intentar:\n"
                        f"• Buscar el artista en tu biblioteca: /search {similar_to}\n"
                        f"• Pedir recomendaciones generales: /recommend"
                    )
                    return
            
            else:
                # Búsqueda normal basada en tu perfil
                # Verificar que haya servicio de scrobbling configurado
                if not self.music_service:
                    await update.message.reply_text(
                        "⚠️ No hay servicio de scrobbling configurado.\n\n"
                        "Por favor configura ListenBrainz (LISTENBRAINZ_USERNAME en .env) para recibir recomendaciones personalizadas."
                    )
                    return
                
                # Obtener datos del usuario
                recent_tracks = await self.music_service.get_recent_tracks(limit=20)
                top_artists = await self.music_service.get_top_artists(limit=10)
                
                if not recent_tracks:
                    await update.message.reply_text(
                        f"⚠️ No se encontraron escuchas recientes.\n\n"
                        "Asegúrate de tener escuchas registradas en ListenBrainz para recibir recomendaciones personalizadas."
                    )
                    return
                
                # Crear perfil de usuario
                from models.schemas import UserProfile
                user_profile = UserProfile(
                    recent_tracks=recent_tracks,
                    top_artists=top_artists,
                    favorite_genres=[],
                    mood_preference="",
                    activity_context=""
                )
                
                # Generar recomendaciones (recommendation_limit ya está definido arriba)
                if from_library_only:
                    print(f"📚 Generando recomendaciones SOLO de biblioteca (tipo: {rec_type}, género: {genre_filter})")
                elif custom_prompt:
                    print(f"🎯 Generando recomendaciones con prompt personalizado: {custom_prompt}")
                else:
                    print(f"🎯 Generando recomendaciones (tipo: {rec_type}, género: {genre_filter}) para {len(recent_tracks)} tracks y {len(top_artists)} artistas...")
                
                recommendations = await self.ai.generate_recommendations(
                    user_profile, 
                    limit=recommendation_limit,
                    recommendation_type=rec_type,
                    genre_filter=genre_filter,
                    custom_prompt=custom_prompt,
                    from_library_only=from_library_only
                )
                print(f"✅ Recomendaciones generadas: {len(recommendations)}")
            
            if not recommendations:
                print("❌ No se generaron recomendaciones")
                await update.message.reply_text(
                    "😔 No pude generar recomendaciones en este momento.\n\n"
                    "Intenta de nuevo más tarde o verifica tu configuración."
                )
                return
            
            print(f"📝 Primera recomendación: {recommendations[0].track.artist} - {recommendations[0].track.title}")
            
            # Mostrar recomendaciones con título personalizado
            if custom_prompt:
                text = f"🎨 <b>Recomendaciones para:</b> <i>{custom_prompt}</i>\n\n"
            elif similar_to:
                text = f"🎯 <b>Música similar a '{similar_to}':</b>\n\n"
            elif rec_type == "album":
                text = f"📀 <b>Álbumes recomendados{f' de {genre_filter}' if genre_filter else ''}:</b>\n\n"
            elif rec_type == "artist":
                text = f"🎤 <b>Artistas recomendados{f' de {genre_filter}' if genre_filter else ''}:</b>\n\n"
            elif rec_type == "track":
                text = f"🎵 <b>Canciones recomendadas{f' de {genre_filter}' if genre_filter else ''}:</b>\n\n"
            else:
                text = "🎵 <b>Tus recomendaciones personalizadas:</b>\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                # Formato diferente según el tipo de recomendación
                if rec_type == "album":
                    # Para álbumes: mostrar prominentemente el nombre del álbum
                    text += f"<b>{i}. 📀 {rec.track.title}</b>\n"
                    text += f"   🎤 Artista: {rec.track.artist}\n"
                elif rec_type == "artist":
                    # Para artistas: solo el nombre del artista
                    text += f"<b>{i}. 🎤 {rec.track.artist}</b>\n"
                else:
                    # Para canciones y general: formato estándar
                    text += f"<b>{i}.</b> {rec.track.artist} - {rec.track.title}\n"
                    if rec.track.album:
                        text += f"   📀 {rec.track.album}\n"
                
                text += f"   💡 {rec.reason}\n"
                if rec.source:
                    text += f"   🔗 Fuente: {rec.source}\n"
                # Agregar enlace si existe (está en el campo path)
                if rec.track.path:
                    # Determinar el nombre del servicio según la URL
                    service_name = "Ver información"
                    if "musicbrainz.org" in rec.track.path:
                        service_name = "Ver en MusicBrainz"
                    elif "listenbrainz.org" in rec.track.path:
                        service_name = "Ver en ListenBrainz"
                    text += f"   🌐 <a href=\"{rec.track.path}\">{service_name}</a>\n"
                text += f"   🎯 {int(rec.confidence * 100)}% match\n\n"
            
            # Botones de interacción (callback_data limitado a 64 bytes)
            keyboard = [
                [InlineKeyboardButton("❤️ Me gusta", callback_data="like_rec"),
                 InlineKeyboardButton("👎 No me gusta", callback_data="dislike_rec")],
                [InlineKeyboardButton("🔄 Más recomendaciones", callback_data="more_recommendations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            print("✅ Recomendaciones enviadas correctamente")
            
            # Guardar recomendaciones en la sesión conversacional
            user_id = update.effective_user.id
            session = self.conversation_manager.get_session(user_id)
            session.set_last_recommendations(recommendations)
            
        except Exception as e:
            print(f"❌ Error en recommend_command: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error generando recomendaciones: {str(e)}")
    
    @_check_authorization
    async def library_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /library - Explorar biblioteca con IA
        
        Usa el agente conversacional con contexto adaptativo para dar
        un resumen inteligente y personalizado de tu biblioteca.
        """
        # 🧠 Usar agente conversacional con contexto adaptativo
        user_id = update.effective_user.id
        agent_query = "Muéstrame un resumen de mi biblioteca musical con recomendaciones"
        
        await update.message.reply_text("📚 Analizando tu biblioteca musical...")
        
        try:
            # Usar el agente con contexto adaptativo
            result = await self.agent.query(agent_query, user_id)
            
            if result.get('success') and result.get('answer'):
                await update.message.reply_text(result['answer'], parse_mode='HTML')
            else:
                await update.message.reply_text("⚠️ No pude acceder a tu biblioteca.")
        except Exception as e:
            print(f"❌ Error accediendo a la biblioteca: {e}")
            await update.message.reply_text(f"❌ Error accediendo a la biblioteca: {str(e)}")
    
    @_check_authorization
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats - Mostrar estadísticas con IA
        
        Usa el agente conversacional con contexto adaptativo para generar
        análisis inteligentes de tus estadísticas de escucha.
        
        Uso:
        - /stats → Estadísticas de este mes (por defecto)
        - /stats week → Estadísticas de esta semana
        - /stats month → Estadísticas de este mes
        - /stats year → Estadísticas de este año
        - /stats all_time → Estadísticas de todo el tiempo
        """
        # 🧠 Usar agente conversacional con contexto adaptativo (nivel 3)
        user_id = update.effective_user.id
        
        # Determinar periodo
        period = "este mes"
        if context.args:
            arg = context.args[0].lower()
            period_map = {
                "week": "esta semana",
                "month": "este mes",
                "year": "este año",
                "all": "de todo el tiempo",
                "all_time": "de todo el tiempo"
            }
            period = period_map.get(arg, "este mes")
        
        # Construir query para el agente
        agent_query = f"Muéstrame mis estadísticas de escucha de {period}"
        
        await update.message.reply_text(f"📊 Analizando tus estadísticas de {period}...")
        
        try:
            # Usar el agente con contexto adaptativo
            result = await self.agent.query(agent_query, user_id)
            
            if result.get('success') and result.get('answer'):
                # El agente genera análisis inteligente
                await update.message.reply_text(result['answer'], parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "⚠️ No pude obtener tus estadísticas.\n\n"
                    "Por favor configura ListenBrainz (LISTENBRAINZ_USERNAME en .env) para ver tus estadísticas."
                )
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error obteniendo estadísticas: {str(e)}")
    
    @_check_authorization
    async def releases_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /releases - Lanzamientos recientes con IA
        
        Usa el agente conversacional con contexto adaptativo para mostrar
        lanzamientos filtrados según tus gustos.
        
        Uso:
        - /releases → Esta semana
        - /releases month → Este mes
        - /releases year → Este año
        - /releases Pink Floyd → Lanzamientos de un artista
        """
        # 🧠 Usar agente conversacional con contexto adaptativo
        user_id = update.effective_user.id
        
        # Determinar query para el agente
        if context.args:
            query_text = " ".join(context.args)
            agent_query = f"Muéstrame los lanzamientos recientes de {query_text}"
        else:
            agent_query = "Muéstrame los lanzamientos recientes de esta semana de artistas de mi biblioteca"
        
        await update.message.reply_text(f"🔍 Buscando lanzamientos recientes...")
        
        try:
            # Usar el agente con contexto adaptativo
            result = await self.agent.query(agent_query, user_id)
            
            if result.get('success') and result.get('answer'):
                await update.message.reply_text(result['answer'], parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "⚠️ No pude obtener los lanzamientos.\n\n"
                    "Asegúrate de que MusicBrainz esté configurado (ENABLE_MUSICBRAINZ=true)."
                )
        except Exception as e:
            print(f"❌ Error obteniendo lanzamientos: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error obteniendo lanzamientos: {str(e)}")
    
    @_check_authorization
    @track_analytics("search")
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /search - Buscar música con IA
        
        Usa el agente conversacional para buscar y dar contexto sobre
        los resultados encontrados.
        """
        if not context.args:
            await update.message.reply_text(
                "🔍 <b>Uso:</b> <code>/search &lt;término&gt;</code>\n\n"
                "Ejemplos:\n"
                "• <code>/search queen</code>\n"
                "• <code>/search bohemian rhapsody</code>\n"
                "• <code>/search the beatles</code>",
                parse_mode='HTML'
            )
            return
        
        # 🧠 Usar agente conversacional con contexto adaptativo
        user_id = update.effective_user.id
        search_term = " ".join(context.args)
        agent_query = f"Busca '{search_term}' en mi biblioteca y dime qué tengo"
        
        await update.message.reply_text(f"🔍 Buscando '{search_term}' en tu biblioteca...")
        
        try:
            # Usar el agente con contexto adaptativo
            result = await self.agent.query(agent_query, user_id)
            
            if result.get('success') and result.get('answer'):
                await update.message.reply_text(result['answer'], parse_mode='HTML')
            else:
                await update.message.reply_text(
                    f"😔 No se encontraron resultados para '{search_term}'.\n\n"
                    "💡 Intenta con diferentes palabras clave."
                )
        except Exception as e:
            print(f"❌ Error en la búsqueda: {e}")
            await update.message.reply_text(f"❌ Error en la búsqueda: {str(e)}")
    
    @_check_authorization
    async def playlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /playlist - Crear playlist M3U
        
        Uso:
        - /playlist rock de los 80s
        - /playlist música relajante
        - /playlist similar a Pink Floyd
        """
        if not context.args:
            await update.message.reply_text(
                "🎵 <b>Crear Playlist</b>\n\n"
                "<b>Uso:</b> <code>/playlist &lt;descripción&gt;</code>\n\n"
                "<b>Ejemplos:</b>\n"
                "• <code>/playlist rock progresivo de los 70s</code>\n"
                "• <code>/playlist música energética para correr</code>\n"
                "• <code>/playlist jazz suave</code>\n"
                "• <code>/playlist similar a Pink Floyd</code>\n"
                "• <code>/playlist 10 canciones de metal melódico</code>\n"
                "• <code>/playlist 25 temas de mujeres, vera fauna y cala vento</code>\n"
                "• <code>/playlist 30 canciones de Pink Floyd y Queen</code>\n\n"
                "💡 <b>Tip:</b> Puedes especificar la cantidad de canciones (ej: '20 canciones', '15 temas')",
                parse_mode='HTML'
            )
            return
        
        # 🧠 Usar agente conversacional con contexto adaptativo
        user_id = update.effective_user.id
        description = " ".join(context.args)
        agent_query = f"Crea una playlist de {description} con canciones de mi biblioteca"
        
        await update.message.reply_text(f"🎵 Creando playlist: <i>{description}</i>...", parse_mode='HTML')
        
        try:
            # Usar el agente con contexto adaptativo
            result = await self.agent.query(agent_query, user_id)
            
            if result.get('success') and result.get('answer'):
                await update.message.reply_text(result['answer'], parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "😔 No pude crear la playlist.\n\n"
                    "Intenta con una descripción más específica o general."
                )
        except Exception as e:
            print(f"❌ Error creando playlist: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error creando playlist: {str(e)}")
    
    def _generate_search_variations(self, search_term: str) -> list:
        """Generar variaciones del término de búsqueda para matching flexible"""
        variations = [search_term]
        
        # Quitar plural (última 's')
        if search_term.endswith('s') and len(search_term) > 2:
            variations.append(search_term[:-1])
        
        # Variaciones ortográficas comunes
        # q -> k, c -> k (común en español)
        if 'qu' in search_term or 'c' in search_term:
            variant = search_term.replace('qu', 'k').replace('c', 'k')
            variations.append(variant)
            if variant.endswith('s'):
                variations.append(variant[:-1])
        
        # k -> qu, k -> c
        if 'k' in search_term:
            variations.append(search_term.replace('k', 'qu'))
            variations.append(search_term.replace('k', 'c'))
        
        # Palabras individuales (si hay más de una)
        words = search_term.split()
        if len(words) > 1:
            # Agregar cada palabra individual
            variations.extend(words)
            # Orden inverso
            variations.append(' '.join(reversed(words)))
        
        # Remover duplicados y strings vacíos
        return list(set(v for v in variations if v and len(v) > 1))
    
    async def share_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /share - Crear enlace compartible de música
        
        Uso:
        - /share Pink Floyd - The Dark Side of the Moon
        - /share Bohemian Rhapsody
        - /share Queen (todas las canciones del artista)
        """
        if not context.args:
            await update.message.reply_text(
                "🔗 <b>Compartir Música</b>\n\n"
                "<b>Uso:</b> <code>/share &lt;nombre&gt;</code>\n\n"
                "<b>Puedes compartir:</b>\n"
                "• Álbumes: <code>/share The Dark Side of the Moon</code>\n"
                "• Canciones: <code>/share Bohemian Rhapsody</code>\n"
                "• Artistas: <code>/share Queen</code> (todas sus canciones)\n\n"
                "💡 <b>Qué obtienes:</b>\n"
                "  🔗 Enlace público con interfaz web de Navidrome\n"
                "  🎧 Reproducir música en streaming\n"
                "  📋 Ver lista completa de canciones\n\n"
                "✨ El enlace es público - no requiere autenticación\n\n"
                "ℹ️ <i>Las descargas dependen de la configuración de tu servidor</i>",
                parse_mode='HTML'
            )
            return
        
        search_term = " ".join(context.args)
        # Normalizar el término de búsqueda (eliminar espacios extras, etc.)
        search_term_normalized = " ".join(search_term.split())
        
        await update.message.reply_text(f"🔍 Buscando '{search_term_normalized}' para compartir...")
        
        try:
            # 1. Generar variaciones del término de búsqueda
            search_variations = self._generate_search_variations(search_term_normalized.lower())
            print(f"🔍 Variaciones de búsqueda: {search_variations}")
            
            # 2. Intentar búsquedas con cada variación hasta encontrar resultados
            results = None
            successful_search_term = None
            
            for variation in search_variations:
                temp_results = await self.navidrome.search(variation, limit=20)
                if temp_results.get('albums') or temp_results.get('tracks') or temp_results.get('artists'):
                    results = temp_results
                    successful_search_term = variation
                    if variation != search_term_normalized.lower():
                        print(f"✅ Encontrado con variación: '{variation}'")
                    break
            
            # Si no se encontró nada, usar los resultados de la última búsqueda
            if not results:
                results = await self.navidrome.search(search_term_normalized, limit=20)
            
            items_to_share = []
            share_type = ""
            found_name = ""
            
            # Priorizar: Álbumes > Canciones > Artistas
            if results.get('albums'):
                # Compartir primer álbum encontrado
                album = results['albums'][0]
                found_name = f"📀 {album.artist} - {album.name}"
                share_type = "álbum"
                
                # Obtener IDs de todas las canciones del álbum
                album_tracks = await self.navidrome.get_album_tracks(album.id)
                items_to_share = [t.id for t in album_tracks]
                
            elif results.get('tracks'):
                # Compartir primera canción encontrada
                track = results['tracks'][0]
                found_name = f"🎵 {track.artist} - {track.title}"
                share_type = "canción"
                items_to_share = [track.id]
                
            elif results.get('artists'):
                # Compartir todas las canciones del artista
                artist = results['artists'][0]
                found_name = f"🎤 {artist.name}"
                share_type = "artista"
                
                # Buscar todas las canciones del artista de forma más permisiva
                artist_tracks = await self.navidrome.search(artist.name, limit=500)
                
                # Normalizar nombre del artista para matching flexible
                artist_name_normalized = artist.name.lower().strip()
                
                # Filtrar canciones del artista (matching flexible)
                items_to_share = [
                    t.id for t in artist_tracks.get('tracks', []) 
                    if artist_name_normalized in t.artist.lower() or t.artist.lower() in artist_name_normalized
                ]
            
            if not items_to_share:
                # Intentar búsqueda más flexible con palabras individuales
                words = search_term_normalized.split()
                if len(words) > 1:
                    # Buscar con solo la primera palabra clave
                    alt_results = await self.navidrome.search(words[0], limit=20)
                    
                    # Buscar coincidencias parciales en álbumes
                    search_lower = search_term_normalized.lower()
                    for album in alt_results.get('albums', []):
                        album_name_lower = album.name.lower()
                        album_artist_lower = album.artist.lower()
                        # Matching flexible: cualquier palabra en común
                        if any(word.lower() in album_name_lower or word.lower() in album_artist_lower for word in words):
                            found_name = f"📀 {album.artist} - {album.name}"
                            share_type = "álbum"
                            album_tracks = await self.navidrome.get_album_tracks(album.id)
                            items_to_share = [t.id for t in album_tracks]
                            break
                    
                    # Si no hay álbumes, buscar en canciones
                    if not items_to_share:
                        for track in alt_results.get('tracks', []):
                            track_title_lower = track.title.lower()
                            track_artist_lower = track.artist.lower()
                            if any(word.lower() in track_title_lower or word.lower() in track_artist_lower for word in words):
                                found_name = f"🎵 {track.artist} - {track.title}"
                                share_type = "canción"
                                items_to_share = [track.id]
                                break
                
                # Si aún no hay resultados, mostrar error
                if not items_to_share:
                    await update.message.reply_text(
                        f"😔 No encontré '{search_term_normalized}' en tu biblioteca.\n\n"
                        "💡 Intenta buscar primero con <code>/search {search_term_normalized}</code> "
                        "para verificar qué hay disponible.",
                        parse_mode='HTML'
                    )
                    return
            
            # 2. Informar si se encontró algo diferente con búsqueda flexible
            search_was_flexible = False
            if successful_search_term and successful_search_term != search_term_normalized.lower():
                # Se usó una variación del término de búsqueda
                search_was_flexible = True
            elif not (results.get('albums') or results.get('tracks') or results.get('artists')):
                # Se usó búsqueda flexible de palabras individuales
                search_was_flexible = True
            
            # 3. Crear share en Navidrome
            description = f"Compartido desde Musicalo: {found_name}"
            share_info = await self.navidrome.create_share(
                items_to_share,
                description=description
            )
            
            if not share_info:
                await update.message.reply_text(
                    "❌ No pude crear el enlace para compartir.\n\n"
                    "Verifica que tu instancia de Navidrome tenga habilitada "
                    "la función de compartir (shares)."
                )
                return
            
            # 4. Formatear respuesta
            text = f"""✅ <b>Enlace compartido creado</b>

{found_name}
📦 <b>{len(items_to_share)}</b> {'canción' if len(items_to_share) == 1 else 'canciones'}

🔗 <b>Enlace del share:</b>
<code>{share_info['url']}</code>

💡 <b>Al abrir este enlace:</b>
• 🎧 Reproducir la música en streaming
• 📋 Ver la lista completa de canciones

📋 <b>Información:</b>
• Tipo: {share_type}
• ID: <code>{share_info['id']}</code>
• Enlace público sin autenticación"""

            # Agregar nota si se usó búsqueda flexible
            if search_was_flexible:
                text += f"\n\nℹ️ <i>Búsqueda flexible activada - encontré el mejor resultado para '{search_term_normalized}'</i>"
            
            # Si es un enlace con muchas canciones, agregar detalles
            if len(items_to_share) > 1:
                text += f"\n• Compartiendo {len(items_to_share)} canciones"
            
            await update.message.reply_text(text, parse_mode='HTML')
            print(f"✅ Share creado: {share_info['url']} ({len(items_to_share)} items)")
            
        except Exception as e:
            print(f"❌ Error en share_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                f"❌ Error creando enlace: {str(e)}\n\n"
                "Verifica tu configuración de Navidrome."
            )
    
    @_check_authorization
    async def nowplaying_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /nowplaying - Ver reproducción actual con IA
        
        Usa el agente conversacional para mostrar qué se está reproduciendo
        y dar contexto o sugerencias basadas en lo que escuchas.
        """
        # 🧠 Usar agente conversacional con contexto adaptativo
        user_id = update.effective_user.id
        agent_query = "¿Qué estoy escuchando ahora?"
        
        await update.message.reply_text("🎵 Consultando reproducción actual...")
        
        try:
            # Usar el agente con contexto adaptativo
            result = await self.agent.query(agent_query, user_id)
            
            if result.get('success') and result.get('answer'):
                await update.message.reply_text(result['answer'], parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "⚠️ No hay nada reproduciéndose en este momento.\n\n"
                    "Asegúrate de que haya reproductores conectados a Navidrome."
                )
        except Exception as e:
            print(f"❌ Error en nowplaying_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error obteniendo información de reproducción: {str(e)}")
    
    @_check_authorization
    @track_analytics("analytics")
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /analytics - Mostrar métricas del sistema (solo administradores)"""
        user_id = update.effective_user.id
        
        # Verificar si es administrador (puedes personalizar esta lógica)
        admin_user_ids = os.getenv("TELEGRAM_ADMIN_USER_IDS", "").split(",")
        admin_user_ids = [int(uid.strip()) for uid in admin_user_ids if uid.strip()]
        
        if admin_user_ids and user_id not in admin_user_ids:
            await update.message.reply_text(
                "🚫 <b>Acceso Denegado</b>\n\n"
                "Este comando solo está disponible para administradores.",
                parse_mode='HTML'
            )
            return
        
        await update.message.reply_text("📊 Generando reporte de analytics...")
        
        try:
            # Obtener insights del sistema
            insights = await analytics_system.get_system_insights()
            
            if "error" in insights:
                await update.message.reply_text(f"❌ Error obteniendo analytics: {insights['error']}")
                return
            
            # Formatear respuesta
            metrics = insights.get("metrics", {})
            performance = insights.get("performance", {})
            
            text = "📊 <b>Analytics del Sistema</b>\n\n"
            
            # Métricas generales
            text += f"🕐 <b>Período:</b> Últimas {metrics.get('period_hours', 24)} horas\n"
            text += f"👥 <b>Usuarios únicos:</b> {metrics.get('unique_users', 0)}\n"
            text += f"🔄 <b>Total interacciones:</b> {metrics.get('total_interactions', 0)}\n"
            text += f"✅ <b>Tasa de éxito:</b> {metrics.get('success_rate', 0):.1f}%\n"
            text += f"⚡ <b>Tiempo promedio:</b> {metrics.get('average_duration_ms', 0):.0f}ms\n"
            text += f"💾 <b>Cache hit rate:</b> {metrics.get('cache_hit_rate', 0):.1f}%\n"
            text += f"🎯 <b>Sesiones activas:</b> {metrics.get('active_sessions', 0)}\n\n"
            
            # Interacciones por tipo
            interactions = metrics.get('interactions_by_type', {})
            if interactions:
                text += "📈 <b>Interacciones por tipo:</b>\n"
                for interaction_type, count in sorted(interactions.items(), key=lambda x: x[1], reverse=True):
                    text += f"• {interaction_type}: {count}\n"
                text += "\n"
            
            # Rendimiento
            response_times = performance.get('response_times', {})
            if response_times:
                text += "⚡ <b>Rendimiento (ms):</b>\n"
                for operation, stats in response_times.items():
                    text += f"• {operation}: avg {stats.get('avg_ms', 0):.0f}ms (p95: {stats.get('p95_ms', 0):.0f}ms)\n"
                text += "\n"
            
            # Cache stats
            cache_stats = performance.get('cache_stats', {})
            if cache_stats:
                text += "💾 <b>Estadísticas de caché:</b>\n"
                text += f"• Hits: {cache_stats.get('hits', 0)}\n"
                text += f"• Misses: {cache_stats.get('misses', 0)}\n"
                text += f"• Errores: {cache_stats.get('errors', 0)}\n\n"
            
            text += f"🕐 <i>Actualizado: {insights.get('timestamp', 'N/A')}</i>"
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            print(f"❌ Error en analytics_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error obteniendo analytics: {str(e)}")
    
    @_check_authorization
    @track_analytics("insights")
    async def insights_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /insights - Mostrar insights de aprendizaje personalizado"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("🧠 Analizando tus patrones de escucha...")
        
        try:
            # Obtener insights de aprendizaje
            insights = await self.ai.get_user_learning_insights(user_id)
            
            if "error" in insights:
                await update.message.reply_text(f"❌ Error obteniendo insights: {insights['error']}")
                return
            
            # Formatear respuesta
            text = "🧠 <b>Insights de Aprendizaje Personalizado</b>\n\n"
            
            # Score de personalización
            personalization_score = insights.get('personalization_score', 0)
            text += f"🎯 <b>Nivel de personalización:</b> {personalization_score:.1%}\n"
            
            # Preferencias detectadas
            preferences = insights.get('preferences', {})
            if preferences:
                text += f"\n📊 <b>Preferencias detectadas:</b>\n"
                for feature, values in preferences.items():
                    if values:
                        top_values = values[:3]  # Top 3
                        text += f"• <b>{feature.title()}:</b> {', '.join([v[0] for v in top_values])}\n"
            
            # Patrones detectados
            patterns = insights.get('patterns', [])
            if patterns:
                text += f"\n🔍 <b>Patrones detectados:</b>\n"
                for pattern in patterns:
                    pattern_type = pattern.get('type', '').replace('_', ' ').title()
                    confidence = pattern.get('confidence', 0)
                    text += f"• {pattern_type}: {confidence:.1%} confianza\n"
            
            # Sugerencias de mejora
            suggestions = insights.get('improvement_suggestions', [])
            if suggestions:
                text += f"\n💡 <b>Sugerencias:</b>\n"
                for suggestion in suggestions:
                    text += f"• {suggestion}\n"
            
            # Estadísticas
            total_feedback = insights.get('total_feedback', 0)
            text += f"\n📈 <b>Estadísticas:</b>\n"
            text += f"• Interacciones registradas: {total_feedback}\n"
            text += f"• Última actualización: {insights.get('last_updated', 'N/A')}\n"
            
            if personalization_score < 0.3:
                text += f"\n💡 <i>Tip: Interactúa más con las recomendaciones (❤️/👎) para mejorar la personalización</i>"
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            print(f"❌ Error en insights_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error obteniendo insights: {str(e)}")
    
    @_check_authorization
    @track_analytics("hybrid")
    async def hybrid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /hybrid - Generar recomendaciones híbridas avanzadas"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("🎯 Generando recomendaciones híbridas avanzadas...")
        
        try:
            # Obtener perfil del usuario
            user_profile = await self._get_user_profile(user_id)
            if not user_profile:
                await update.message.reply_text("❌ No se pudo obtener tu perfil. Usa /start primero.")
                return
            
            # Generar recomendaciones híbridas
            recommendations = await self.ai.generate_hybrid_recommendations(
                user_profile, user_id, max_recommendations=10
            )
            
            if not recommendations:
                await update.message.reply_text("❌ No se pudieron generar recomendaciones híbridas.")
                return
            
            # Formatear respuesta
            text = "🎯 <b>Recomendaciones Híbridas Avanzadas</b>\n\n"
            
            for i, rec in enumerate(recommendations[:5], 1):
                track = rec.track
                text += f"{i}. <b>{track.title}</b> - {track.artist}\n"
                text += f"   🎵 {rec.reasoning}\n"
                text += f"   📊 Confianza: {rec.confidence:.1%}\n"
                
                # Mostrar tags de estrategia
                strategy_tags = [tag for tag in rec.tags if tag.startswith('hybrid:')]
                if strategy_tags:
                    strategy = strategy_tags[0].split(':')[1]
                    text += f"   🔧 Estrategia: {strategy}\n"
                
                text += "\n"
            
            if len(recommendations) > 5:
                text += f"... y {len(recommendations) - 5} más\n"
            
            text += "\n💡 <i>Estas recomendaciones combinan múltiples estrategias de IA para mayor precisión</i>"
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            print(f"❌ Error en hybrid_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error generando recomendaciones híbridas: {str(e)}")
    
    @_check_authorization
    @track_analytics("profile")
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /profile - Mostrar perfil avanzado del usuario"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("🧠 Analizando tu perfil musical avanzado...")
        
        try:
            # Obtener perfil del usuario
            user_profile = await self._get_user_profile(user_id)
            if not user_profile:
                await update.message.reply_text("❌ No se pudo obtener tu perfil. Usa /start primero.")
                return
            
            # Analizar perfil avanzado
            advanced_profile = await self.ai.analyze_advanced_user_profile(user_profile, user_id)
            
            if "error" in advanced_profile:
                await update.message.reply_text(f"❌ Error analizando perfil: {advanced_profile['error']}")
                return
            
            # Formatear respuesta
            text = "🧠 <b>Tu Perfil Musical Avanzado</b>\n\n"
            
            # Personalidad musical
            personality = advanced_profile.get('personality', {})
            if personality:
                text += "🎭 <b>Personalidad Musical:</b>\n"
                traits = personality.get('traits', {})
                for trait, score in traits.items():
                    if score > 0.3:  # Solo mostrar rasgos significativos
                        text += f"• {trait.replace('_', ' ').title()}: {score:.1%}\n"
                
                text += f"\n🔍 <b>Descubrimiento:</b> {personality.get('discovery_rate', 0):.1%}\n"
                text += f"👥 <b>Influencia Social:</b> {personality.get('social_influence', 0):.1%}\n\n"
            
            # Preferencias contextuales
            contextual_prefs = advanced_profile.get('contextual_preferences', [])
            if contextual_prefs:
                text += "🎯 <b>Preferencias Contextuales:</b>\n"
                for pref in contextual_prefs[:3]:  # Top 3 contextos
                    context = pref['context'].replace('_', ' ').title()
                    genres = ', '.join(pref['preferred_genres'][:3])
                    text += f"• {context}: {genres}\n"
                text += "\n"
            
            # Insights de aprendizaje
            learning_insights = advanced_profile.get('learning_insights', {})
            if learning_insights:
                personalization_score = learning_insights.get('personalization_score', 0)
                text += f"📊 <b>Nivel de Personalización:</b> {personalization_score:.1%}\n"
                
                total_feedback = learning_insights.get('total_feedback', 0)
                text += f"💬 <b>Interacciones:</b> {total_feedback}\n\n"
            
            # Preferencias musicales
            music_prefs = advanced_profile.get('music_preferences', {})
            if music_prefs:
                text += "🎵 <b>Estadísticas Musicales:</b>\n"
                text += f"• Géneros únicos: {music_prefs.get('genre_diversity', 0)}\n"
                text += f"• Artistas únicos: {music_prefs.get('artist_diversity', 0)}\n"
                
                avg_duration = music_prefs.get('avg_track_duration', 0)
                if avg_duration > 0:
                    minutes = int(avg_duration // 60)
                    seconds = int(avg_duration % 60)
                    text += f"• Duración promedio: {minutes}:{seconds:02d}\n"
            
            text += f"\n🕐 <i>Actualizado: {advanced_profile.get('last_updated', 'N/A')}</i>"
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            print(f"❌ Error en profile_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error analizando perfil: {str(e)}")
    
    @_check_authorization
    async def _handle_conversational_query(self, update: Update, user_message: str):
        """Manejar consultas conversacionales usando el agente musical"""
        try:
            print(f"💬 Consulta conversacional: {user_message}")
            
            user_id = update.effective_user.id
            
            # USAR EL AGENTE MUSICAL con soporte conversacional
            # El agente buscará en biblioteca + ListenBrainz + MusicBrainz automáticamente
            result = await self.agent.query(
                user_message,
                user_id=user_id,
                context={"type": "conversational"}
            )
            
            if result.get("success"):
                answer = result["answer"]
                
                # Agregar enlaces si hay
                links = result.get("links", [])
                if links:
                    answer += "\n\n🔗 <b>Enlaces relevantes:</b>\n"
                    for link in links[:5]:  # Máximo 5 enlaces
                        answer += f"• {link}\n"
                
                await update.message.reply_text(answer, parse_mode='HTML')
                print(f"✅ Respuesta del agente enviada")
            else:
                await update.message.reply_text(
                    "😔 No pude procesar tu consulta en este momento.\n\n"
                    "Intenta reformular tu pregunta o usa los comandos disponibles."
                )
            
        except Exception as e:
            print(f"❌ Error en conversación: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                f"🤔 No pude procesar tu mensaje de forma conversacional.\n\n"
                f"💡 Puedes usar:\n"
                f"• /recommend - Para recomendaciones\n"
                f"• /search <término> - Para buscar\n"
                f"• /stats - Para estadísticas\n"
                f"• /help - Para ver todos los comandos"
            )
    
    @_check_authorization
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones inline"""
        query = update.callback_query
        
        # Importante: Responder primero al callback para que Telegram no muestre "loading"
        await query.answer()
        
        data = query.data
        print(f"🔘 Botón presionado: {data}")
        
        try:
            if data.startswith("like_"):
                print("   ➜ Procesando 'like'")
                track_id = data.split("_", 1)[1]
                
                # Procesar feedback de aprendizaje
                user_id = query.from_user.id
                await self.ai.process_recommendation_feedback(
                    user_id=user_id,
                    recommendation_id=track_id,
                    feedback_type="like",
                    recommendation_context={"timestamp": datetime.now().isoformat()}
                )
                
                await query.edit_message_text("❤️ ¡Gracias! He registrado que te gusta esta recomendación.")
                print("   ✅ Like procesado")
                
            elif data.startswith("dislike_"):
                print("   ➜ Procesando 'dislike'")
                track_id = data.split("_", 1)[1]
                
                # Procesar feedback de aprendizaje
                user_id = query.from_user.id
                await self.ai.process_recommendation_feedback(
                    user_id=user_id,
                    recommendation_id=track_id,
                    feedback_type="dislike",
                    recommendation_context={"timestamp": datetime.now().isoformat()}
                )
                
                await query.edit_message_text("👎 Entendido. Evitaré recomendaciones similares.")
                print("   ✅ Dislike procesado")
                
            elif data == "more_recommendations":
                print("   ➜ Procesando 'more_recommendations'")
                await query.edit_message_text("🔄 Generando más recomendaciones...")
                
                # 🧠 Usar agente conversacional con contexto adaptativo
                user_id = query.from_user.id
                agent_query = "Recomiéndame 5 canciones diferentes basándote en mis gustos"
                
                try:
                    result = await self.agent.query(agent_query, user_id)
                    
                    if result.get('success') and result.get('answer'):
                        # El agente devuelve respuesta formateada
                        text = f"🎵 <b>Nuevas recomendaciones para ti:</b>\n\n{result['answer']}"
                        
                        keyboard = [
                            [InlineKeyboardButton("❤️ Me gusta", callback_data="like_rec"),
                             InlineKeyboardButton("👎 No me gusta", callback_data="dislike_rec")],
                            [InlineKeyboardButton("🔄 Más recomendaciones", callback_data="more_recommendations")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                    else:
                        await query.edit_message_text("😔 No pude generar más recomendaciones en este momento.")
                except Exception as e:
                    print(f"❌ Error en more_recommendations: {e}")
                    await query.edit_message_text("😔 Hubo un error al generar recomendaciones.")
                
                print("   ✅ More recommendations procesado")
                
            elif data.startswith("play_"):
                print("   ➜ Procesando 'play'")
                track_id = data.split("_", 1)[1]
                await query.edit_message_text("🎵 Abriendo en Navidrome...\n\n⚠️ Funcionalidad en desarrollo")
                print("   ✅ Play procesado")
                
            elif data.startswith("library_"):
                print("   ➜ Procesando 'library'")
                category = data.split("_", 1)[1]
                await query.edit_message_text(f"📚 Cargando {category}...")
                
                if category == "tracks":
                    tracks = await self.navidrome.get_tracks(limit=20)
                    text = "🎵 <b>Canciones de tu biblioteca:</b>\n\n"
                    for i, track in enumerate(tracks[:15], 1):
                        text += f"{i}. {track.artist} - {track.title}\n"
                    await query.edit_message_text(text, parse_mode='HTML')
                    
                elif category == "albums":
                    albums = await self.navidrome.get_albums(limit=20)
                    text = "📀 <b>Álbumes de tu biblioteca:</b>\n\n"
                    for i, album in enumerate(albums[:15], 1):
                        text += f"{i}. {album.artist} - {album.name}\n"
                    await query.edit_message_text(text, parse_mode='HTML')
                    
                elif category == "artists":
                    artists = await self.navidrome.get_artists(limit=20)
                    text = "🎤 <b>Artistas de tu biblioteca:</b>\n\n"
                    for i, artist in enumerate(artists[:15], 1):
                        text += f"{i}. {artist.name}\n"
                    await query.edit_message_text(text, parse_mode='HTML')
                    
                elif category == "search":
                    await query.edit_message_text("🔍 Usa el comando <code>/search &lt;término&gt;</code> para buscar música", parse_mode='HTML')
                else:
                    await query.edit_message_text(f"📚 Cargando {category}...\n\n⚠️ Funcionalidad en desarrollo")
                
                print("   ✅ Library procesado")
                
            elif data == "daily_activity":
                print("   ➜ Procesando 'daily_activity'")
                await query.edit_message_text("📈 Calculando actividad diaria...")
                if self.music_service:
                    activity = await self.music_service.get_listening_activity(days=30) if hasattr(self.music_service, 'get_listening_activity') else {}
                    text = "📈 <b>Actividad de los últimos 30 días</b>\n\n"
                    if activity:
                        daily_listens = activity.get("daily_listens", {})
                        text += f"📊 Total de días activos: {activity.get('total_days', 0)}\n"
                        text += f"📊 Promedio diario: {activity.get('avg_daily_listens', 0):.1f} escuchas\n"
                    else:
                        text += "⚠️ No hay datos de actividad disponibles"
                    await query.edit_message_text(text, parse_mode='HTML')
                    print("   ✅ Daily activity procesado")
                else:
                    await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                    print("   ⚠️ No hay servicio configurado")
                
            elif data == "favorite_genres":
                print("   ➜ Procesando 'favorite_genres'")
                text = "🎯 <b>Géneros favoritos</b>\n\n⚠️ Funcionalidad en desarrollo"
                await query.edit_message_text(text, parse_mode='HTML')
                print("   ✅ Favorite genres procesado")
                
            elif data == "refresh_stats":
                print("   ➜ Procesando 'refresh_stats'")
                await query.edit_message_text("🔄 Actualizando estadísticas...")
                # Recalcular estadísticas
                if self.music_service:
                    user_stats = await self.music_service.get_user_stats() if hasattr(self.music_service, 'get_user_stats') else {}
                    recent_tracks = await self.music_service.get_recent_tracks(limit=100)
                    top_artists = await self.music_service.get_top_artists(limit=10)
                    
                    text = "📊 <b>Tus Estadísticas Musicales</b> (Actualizado)\n\n"
                    text += f"🎵 <b>Total de escuchas:</b> {user_stats.get('total_listens', 'N/A')}\n"
                    text += f"🎤 <b>Artistas únicos:</b> {user_stats.get('total_artists', 'N/A')}\n"
                    text += f"📀 <b>Álbumes únicos:</b> {user_stats.get('total_albums', 'N/A')}\n"
                    text += f"🎼 <b>Canciones únicas:</b> {user_stats.get('total_tracks', 'N/A')}\n\n"
                    
                    text += f"🏆 <b>Top 5 Artistas:</b>\n"
                    for i, artist in enumerate(top_artists[:5], 1):
                        text += f"{i}. {artist.name} ({artist.playcount} escuchas)\n"
                    
                    if recent_tracks:
                        text += f"\n⏰ <b>Última escucha:</b>\n"
                        last_track = recent_tracks[0]
                        text += f"{last_track.artist} - {last_track.name}\n"
                    
                    keyboard = [
                        [InlineKeyboardButton("📈 Actividad diaria", callback_data="daily_activity")],
                        [InlineKeyboardButton("🎯 Géneros favoritos", callback_data="favorite_genres")],
                        [InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_stats")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                    print("   ✅ Refresh stats procesado")
                else:
                    await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                    print("   ⚠️ No hay servicio configurado")
                    
            elif data.startswith("search_"):
                print("   ➜ Procesando 'search'")
                parts = data.split("_")
                category = parts[1]
                term = "_".join(parts[2:])
                await query.edit_message_text(f"🔍 Mostrando {category} para '{term}'...\n\n⚠️ Funcionalidad en desarrollo")
                print("   ✅ Search procesado")
            
            elif data.startswith("stats_"):
                print(f"   ➜ Procesando 'stats' con rango")
                period = data.replace("stats_", "")
                
                range_emojis = {
                    "this_week": "📅",
                    "this_month": "📆",
                    "this_year": "📋",
                    "last_week": "⏮️",
                    "last_month": "⏮️",
                    "last_year": "⏮️",
                    "all_time": "🌟"
                }
                
                range_names = {
                    "this_week": "Esta Semana",
                    "this_month": "Este Mes",
                    "this_year": "Este Año",
                    "last_week": "Semana Pasada",
                    "last_month": "Mes Pasado",
                    "last_year": "Año Pasado",
                    "all_time": "Todo el Tiempo"
                }
                
                emoji = range_emojis.get(period, "📊")
                range_name = range_names.get(period, "Este Mes")
                
                await query.edit_message_text(f"{emoji} Calculando estadísticas de <b>{range_name}</b>...")
                
                try:
                    if self.music_service:
                        # Obtener estadísticas del periodo
                        top_artists = await self.music_service.get_top_artists(period=period, limit=10)
                        top_tracks = await self.music_service.get_top_tracks(period=period, limit=5) if hasattr(self.music_service, 'get_top_tracks') else []
                        recent_tracks = await self.music_service.get_recent_tracks(limit=5)
                        
                        # Obtener álbumes si es ListenBrainz
                        top_albums = []
                        if hasattr(self.music_service, 'get_top_albums'):
                            top_albums = await self.music_service.get_top_albums(period=period, limit=5)
                        
                        text = f"{emoji} <b>Estadísticas de {range_name}</b>\n"
                        text += f"<i>Servicio: {self.music_service_name}</i>\n\n"
                        
                        # Top artistas
                        if top_artists:
                            text += f"🏆 <b>Top 5 Artistas:</b>\n"
                            for i, artist in enumerate(top_artists[:5], 1):
                                text += f"{i}. {artist.name} - {artist.playcount} escuchas\n"
                            text += "\n"
                        
                        # Top álbumes
                        if top_albums:
                            text += f"📀 <b>Top 3 Álbumes:</b>\n"
                            for i, album in enumerate(top_albums[:3], 1):
                                text += f"{i}. {album['artist']} - {album['name']} ({album['listen_count']} escuchas)\n"
                            text += "\n"
                        
                        # Top tracks
                        if top_tracks:
                            text += f"🎵 <b>Top 3 Canciones:</b>\n"
                            for i, track in enumerate(top_tracks[:3], 1):
                                text += f"{i}. {track.artist} - {track.name} ({track.playcount} escuchas)\n"
                            text += "\n"
                        
                        # Actividad reciente
                        if recent_tracks:
                            text += f"⏰ <b>Última escucha:</b>\n"
                            last_track = recent_tracks[0]
                            text += f"{last_track.artist} - {last_track.name}\n"
                        
                        # Botones para cambiar de rango
                        keyboard = [
                            [
                                InlineKeyboardButton("📅 Esta Semana", callback_data="stats_this_week"),
                                InlineKeyboardButton("📆 Este Mes", callback_data="stats_this_month")
                            ],
                            [
                                InlineKeyboardButton("📋 Este Año", callback_data="stats_this_year"),
                                InlineKeyboardButton("🌟 Todo el Tiempo", callback_data="stats_all_time")
                            ],
                            [
                                InlineKeyboardButton("⏮️ Mes Pasado", callback_data="stats_last_month"),
                                InlineKeyboardButton("⏮️ Año Pasado", callback_data="stats_last_year")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                    else:
                        await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                    
                    print(f"   ✅ Stats de {period} procesado")
                    
                except Exception as e:
                    print(f"   ❌ Error obteniendo estadísticas: {e}")
                    import traceback
                    traceback.print_exc()
                    await query.edit_message_text(f"❌ Error obteniendo estadísticas de {range_name}")
                
            else:
                print(f"   ⚠️ Callback no reconocido: {data}")
                await query.edit_message_text(f"⚠️ Opción no implementada: {data}")
                
        except Exception as e:
            print(f"❌ Error en callback: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await query.edit_message_text(f"❌ Error: {str(e)}")
            except:
                print("   ❌ No se pudo enviar mensaje de error")
                pass
    
    def _detect_intent_with_regex(self, user_message: str) -> Optional[Dict[str, Any]]:
        """Detectar intención usando patrones regex ANTES de llamar a la IA
        
        Esto hace el sistema más determinista para casos comunes
        """
        import re
        
        msg_lower = user_message.lower()
        
        # PATRÓN 1: "disco/álbum DE [artista]" (no similar)
        # Ejemplos: "recomiéndame un disco de tobogán andaluz"
        if not re.search(r'\b(similar|parecido|como)\s+(a\s+)?', msg_lower):
            # Solo si NO dice "similar"
            pattern_de = r'(?:disco|álbum|album)\s+de\s+([a-z][a-záéíóúñ\s]+?)(?:\s+para|\s*$|\?)'
            match = re.search(pattern_de, msg_lower)
            if match:
                artist = match.group(1).strip()
                print(f"🎯 REGEX: Detectado 'disco DE {artist}' → usar chat")
                return {
                    "action": "chat",
                    "params": {"question": user_message}
                }
        
        # PATRÓN 2: "similar a [artista]" o "parecido a [artista]"
        pattern_similar = r'\b(similar|parecido|como)\s+(a\s+)?([a-z][a-záéíóúñ\s]+?)(?:\s+para|\s*$|\?)'
        match = re.search(pattern_similar, msg_lower)
        if match:
            artist = match.group(3).strip()
            print(f"🎯 REGEX: Detectado 'similar a {artist}' → usar similar_to")
            return {
                "action": "recommend",
                "params": {"rec_type": "general", "similar_to": artist, "limit": 5}
            }
        
        # PATRÓN 3: "qué tengo de [artista]" o "qué álbumes de [artista]"
        pattern_tengo = r'(?:qué|que)\s+(?:tengo|teengo|álbumes|albums|discos)\s+de\s+([a-z][a-záéíóúñ\s]+?)(?:\s+tengo|\?|\s*$)'
        match = re.search(pattern_tengo, msg_lower)
        if match:
            artist = match.group(1).strip()
            print(f"🎯 REGEX: Detectado 'qué tengo de {artist}' → usar chat")
            return {
                "action": "chat",
                "params": {"question": user_message}
            }
        
        # PATRÓN 4: "playlist/música con/de [artistas]" (contiene comas o "y")
        # Detecta listas de artistas o descripciones de playlist
        pattern_playlist = r'\b(haz|crea|hacer|dame|genera)\s+(una\s+)?(playlist|lista)\s+(?:con|de)\s+(.+)'
        match = re.search(pattern_playlist, msg_lower)
        if match:
            description = match.group(4).strip()
            print(f"🎯 REGEX: Detectado petición de playlist: '{description}' → usar playlist")
            return {
                "action": "playlist",
                "params": {"description": description}
            }
        
        # PATRÓN 5: "música/canciones de [artistas]" con múltiples artistas
        if ',' in user_message or re.search(r'\s+y\s+', msg_lower):
            pattern_music = r'(?:música|canciones|temas)\s+(?:con|de)\s+(.+)'
            match = re.search(pattern_music, msg_lower)
            if match:
                artists_part = match.group(1)
                # Verificar si parece una lista de artistas (tiene comas o "y")
                if ',' in artists_part or ' y ' in artists_part:
                    print(f"🎯 REGEX: Detectado 'música de lista de artistas' → usar playlist")
                    return {
                        "action": "playlist",
                        "params": {"description": artists_part}
                    }
        
        # No se detectó patrón claro, dejar que la IA lo maneje
        return None
    
    @_check_authorization
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de texto con IA - VERSIÓN SIMPLIFICADA CON INTENT DETECTOR"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # Mensaje de espera
        waiting_msg = await update.message.reply_text("🤔 Analizando tu mensaje...")
        
        try:
            print(f"💬 Usuario {user_id}: {user_message}")
            
            # Obtener sesión conversacional
            session = self.conversation_manager.get_session(user_id)
            
            # Obtener estadísticas del usuario para contexto
            user_stats = None
            if self.music_service:
                try:
                    top_artists = await self.music_service.get_top_artists(limit=5)
                    if top_artists:
                        user_stats = {
                            'top_artists': [a.name for a in top_artists]
                        }
                except Exception as e:
                    print(f"⚠️ No se pudo obtener contexto: {e}")
            
            # Detectar intención usando EnhancedIntentDetector
            intent_data = await self.enhanced_intent_detector.detect_intent(
                user_message,
                session_context=session.get_context_for_ai(),
                user_stats=user_stats
            )

            
            intent = intent_data.get("intent")
            params = intent_data.get("params", {})
            confidence = intent_data.get("confidence", 0.5)
            
            print(f"🎯 Intención detectada: '{intent}' (confianza: {confidence})")
            print(f"📋 Parámetros: {params}")
            
            # Borrar mensaje de espera
            await waiting_msg.delete()
            
            # Guardar acción en sesión
            session.set_last_action(intent, params)
            
            # Ejecutar acción según la intención detectada
            # SOLO 6 intenciones posibles: playlist, buscar, recomendar, referencia, releases, conversacion
            
            if intent == "playlist":
                # Crear playlist M3U
                description = params.get("description", user_message)
                context.args = description.split()
                await self.playlist_command(update, context)
            
            elif intent == "buscar":
                # Buscar en biblioteca
                search_term = params.get("search_query", "")
                if search_term:
                    context.args = search_term.split()
                    await self.search_command(update, context)
                else:
                    await update.message.reply_text("❌ No especificaste qué buscar.")
            
            elif intent == "recomendar":
                # Recomendaciones con "similar a [artista]"
                similar_to = params.get("similar_to")
                if similar_to:
                    context.args = ["similar", similar_to, "__limit=5"]
                    await self.recommend_command(update, context)
                else:
                    # Fallback a conversación si no hay artista específico
                    await self._handle_conversational_query(update, user_message)
            
            elif intent == "recomendar_biblioteca":
                # Recomendaciones DE la biblioteca (redescubrimiento)
                print(f"📚 Intent: recomendar_biblioteca detectado")
                
                # Extraer parámetros
                genre = params.get("genre", params.get("genres", [""])[0] if "genres" in params else "")
                rec_type = params.get("type", "general")
                
                # Construir args para el comando
                args = ["biblioteca"]
                
                if rec_type and rec_type in ["album", "artist", "track"]:
                    args.append(rec_type)
                
                if genre:
                    args.append(genre)
                
                args.append("__limit=5")
                
                context.args = args
                print(f"   Llamando /recommend con args: {args}")
                await self.recommend_command(update, context)
            
            elif intent == "referencia":
                # Usuario hace referencia a algo anterior ("más de eso", "otro así")
                if session.last_recommendations:
                    last_artists = session.get_last_artists()
                    if last_artists:
                        await update.message.reply_text(f"🎵 Buscando más música similar a {last_artists[0]}...")
                        context.args = ["similar", last_artists[0], "__limit=5"]
                        await self.recommend_command(update, context)
                    else:
                        await self._handle_conversational_query(update, user_message)
                else:
                    await update.message.reply_text(
                        "🤔 No tengo referencia de qué música te gustó antes.\n"
                        "¿Puedes ser más específico?"
                    )
            
            elif intent == "releases":
                # Lanzamientos recientes y música nueva
                print(f"🆕 Intent: releases detectado")
                
                # Extraer parámetros
                artist = params.get("artist", "")
                time_period = params.get("time_period", "week")  # week, month, year
                
                # Construir query para el agente
                if artist:
                    agent_query = f"Muéstrame los lanzamientos recientes de {artist}"
                else:
                    agent_query = "Muéstrame los lanzamientos recientes de esta semana de artistas de mi biblioteca"
                
                await update.message.reply_text("🔍 Buscando lanzamientos recientes...")
                
                try:
                    # Usar el agente con contexto adaptativo
                    result = await self.agent.query(agent_query, user_id)
                    
                    if result.get('success') and result.get('answer'):
                        await update.message.reply_text(result['answer'], parse_mode='HTML')
                    else:
                        await update.message.reply_text(
                            "⚠️ No pude obtener los lanzamientos.\n\n"
                            "Asegúrate de que MusicBrainz esté configurado (ENABLE_MUSICBRAINZ=true)."
                        )
                except Exception as e:
                    print(f"❌ Error obteniendo lanzamientos: {e}")
                    await update.message.reply_text(f"❌ Error obteniendo lanzamientos: {str(e)}")
            
            else:
                # TODO LO DEMÁS va a conversación (DEFAULT)
                # Esto incluye: preguntas sobre stats, info, recomendaciones generales,
                # y CUALQUIER consulta natural del usuario
                await self._handle_conversational_query(update, user_message)
                
        except Exception as e:
            print(f"❌ Error en handle_message: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            try:
                await waiting_msg.edit_text(
                    f"❌ Error procesando tu mensaje: {str(e)}\n\n"
                    "💡 Puedes usar comandos directos:\n"
                    "• /recommend - Recomendaciones\n"
                    "• /search <término> - Buscar música\n"
                    "• /stats - Estadísticas\n"
                    "• /playlist <descripción> - Crear playlist"
                )
            except:
                await update.message.reply_text(
                    "❌ Hubo un error. Usa /help para ver los comandos disponibles."
                )
