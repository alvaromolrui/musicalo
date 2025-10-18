from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from typing import List, Dict, Any, Optional
import os
import json
import random
import google.generativeai as genai
from models.schemas import Recommendation, Track, LastFMTrack, LastFMArtist
from services.navidrome_service import NavidromeService
from services.listenbrainz_service import ListenBrainzService
from services.lastfm_service import LastFMService
from services.ai_service import MusicRecommendationService
from services.playlist_service import PlaylistService
from services.music_agent_service import MusicAgentService
from services.conversation_manager import ConversationManager
from services.intent_detector import IntentDetector
from services.system_prompts import SystemPrompts
from functools import wraps
from datetime import datetime

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
        
        # Detectar qué servicio de scrobbling usar
        # PRIORIDAD: ListenBrainz > Last.fm (ListenBrainz tiene mejor API y sin límites)
        self.lastfm = None
        if os.getenv("LISTENBRAINZ_USERNAME"):
            self.music_service = self.listenbrainz
            self.music_service_name = "ListenBrainz"
            print("✅ Usando ListenBrainz para datos de escucha")
            # Mantener Last.fm disponible para descubrimiento si está configurado
            if os.getenv("LASTFM_API_KEY") and os.getenv("LASTFM_USERNAME"):
                self.lastfm = LastFMService()
                print("✅ Last.fm también disponible para descubrimiento")
        elif os.getenv("LASTFM_API_KEY") and os.getenv("LASTFM_USERNAME"):
            self.lastfm = LastFMService()
            self.music_service = self.lastfm
            self.music_service_name = "Last.fm"
            print("✅ Usando Last.fm para datos de escucha")
        else:
            self.music_service = None
            self.music_service_name = None
            print("⚠️ No hay servicio de scrobbling configurado (Last.fm o ListenBrainz)")
    
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

<b>🎨 Sé específico en tus peticiones:</b>
Puedes dar todos los detalles que quieras:
• "Rock progresivo de los 70s con sintetizadores"
• "Música energética para hacer ejercicio"
• "Jazz suave para estudiar"
• "Metal melódico con voces limpias"

<b>📝 Comandos disponibles:</b>
/recommend - Obtener recomendaciones personalizadas
/playlist &lt;descripción&gt; - Crear playlist M3U 🎵
/library - Explorar tu biblioteca musical
/stats - Ver estadísticas de escucha
/search &lt;término&gt; - Buscar música en tu biblioteca
/help - Mostrar ayuda

<b>¿Cómo funciona?</b>
Analizo tu actividad en Last.fm/ListenBrainz y tu biblioteca de Navidrome para sugerirte música que realmente te gustará.

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
• /library - Ver tu biblioteca musical
• /stats - Estadísticas de escucha
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

<b>Búsqueda:</b>
• /search queen - Buscar Queen
• /search bohemian rhapsody - Buscar canción

<b>Playlists:</b>
• /playlist rock de los 80s - Playlist de rock ochentero
• /playlist jazz suave - Música jazz relajante
• /playlist 20 canciones de Queen - Playlist con cantidad específica

<b>Botones interactivos:</b>
• ❤️ Me gusta / 👎 No me gusta
• 🔄 Más recomendaciones (genera nuevas)
• 📚 Ver más (biblioteca)
• 📊 Actualizar (estadísticas)

<b>Servicios:</b>
• Last.fm: Análisis de escucha y descubrimiento
• Navidrome: Tu biblioteca musical
• Gemini AI: Recomendaciones inteligentes

<b>💡 Tip:</b> Puedes preguntarme cualquier cosa sobre música directamente, sin usar comandos. ¡Prueba!"""
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    @_check_authorization
    async def recommend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /recommend - Generar recomendaciones
        
        Uso:
        - /recommend → Recomendaciones generales
        - /recommend album → Solo álbumes
        - /recommend artist → Solo artistas
        - /recommend track → Solo canciones
        - /recommend rock → Recomendaciones de rock
        - /recommend album metal → Álbumes de metal
        """
        # Parsear argumentos
        rec_type = "general"  # general, album, artist, track
        genre_filter = None
        similar_to = None  # Para búsquedas "similar a..."
        recommendation_limit = 5  # Por defecto
        custom_prompt = None  # Para descripciones específicas
        
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
        if custom_prompt:
            await update.message.reply_text(f"🎨 Analizando tu petición: '{custom_prompt}'...")
        elif similar_to:
            await update.message.reply_text(f"🔍 Buscando música similar a '{similar_to}'...")
        elif rec_type == "album":
            await update.message.reply_text(f"📀 Analizando álbumes{f' de {genre_filter}' if genre_filter else ''}...")
        elif rec_type == "artist":
            await update.message.reply_text(f"🎤 Buscando artistas{f' de {genre_filter}' if genre_filter else ''}...")
        elif rec_type == "track":
            await update.message.reply_text(f"🎵 Buscando canciones{f' de {genre_filter}' if genre_filter else ''}...")
        else:
            await update.message.reply_text("🎵 Analizando tus gustos musicales...")
        
        try:
            recommendations = []
            
            # Si es una búsqueda "similar a...", usar Last.fm directamente
            if similar_to:
                print(f"🎯 Usando límite: {recommendation_limit} para similares")
                
                if self.lastfm:
                    print(f"🔍 Buscando similares a '{similar_to}' en Last.fm (tipo: {rec_type})...")
                    # Buscar más artistas de los necesarios por si algunos no tienen álbumes/tracks
                    search_limit = max(30, recommendation_limit * 5)
                    similar_artists = await self.lastfm.get_similar_artists(similar_to, limit=search_limit)
                    
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
                            
                            # Obtener datos específicos según el tipo
                            if rec_type == "album":
                                top_albums = await self.lastfm.get_artist_top_albums(similar_artist.name, limit=1)
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
                                top_tracks = await self.lastfm.get_artist_top_tracks(similar_artist.name, limit=1)
                                if top_tracks:
                                    track_data = top_tracks[0]
                                    title = track_data.name
                                    artist_url = track_data.url if track_data.url else artist_url
                                    reason = f"🎵 Canción top de artista similar a {similar_to}"
                                else:
                                    title = f"Música de {similar_artist.name}"
                                    reason = f"🎵 Similar a {similar_to}"
                            
                            else:
                                title = similar_artist.name
                                reason = f"🎯 Similar a {similar_to}"
                            
                            track = Track(
                                id=f"lastfm_similar_{similar_artist.name.replace(' ', '_')}",
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
                                source="Last.fm",
                                tags=[]
                            )
                            recommendations.append(recommendation)
                    else:
                        await update.message.reply_text(f"😔 No encontré artistas similares a '{similar_to}'")
                        return
                else:
                    await update.message.reply_text("⚠️ Necesitas configurar Last.fm para buscar similares.")
                    return
            
            else:
                # Búsqueda normal basada en tu perfil
                # Verificar que haya servicio de scrobbling configurado
                if not self.music_service:
                    await update.message.reply_text(
                        "⚠️ No hay servicio de scrobbling configurado.\n\n"
                        "Por favor configura Last.fm o ListenBrainz para recibir recomendaciones personalizadas."
                    )
                    return
                
                # Obtener datos del usuario
                recent_tracks = await self.music_service.get_recent_tracks(limit=20)
                top_artists = await self.music_service.get_top_artists(limit=10)
                
                if not recent_tracks:
                    await update.message.reply_text(
                        f"⚠️ No se encontraron escuchas recientes en {self.music_service_name}.\n\n"
                        "Asegúrate de tener escuchas registradas para recibir recomendaciones personalizadas."
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
                if custom_prompt:
                    print(f"🎯 Generando recomendaciones con prompt personalizado: {custom_prompt}")
                else:
                    print(f"🎯 Generando recomendaciones (tipo: {rec_type}, género: {genre_filter}) para {len(recent_tracks)} tracks y {len(top_artists)} artistas...")
                
                recommendations = await self.ai.generate_recommendations(
                    user_profile, 
                    limit=recommendation_limit,
                    recommendation_type=rec_type,
                    genre_filter=genre_filter,
                    custom_prompt=custom_prompt
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
                    text += f"   🌐 <a href=\"{rec.track.path}\">Ver en Last.fm</a>\n"
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
        """Comando /library - Mostrar biblioteca"""
        await update.message.reply_text("📚 Cargando tu biblioteca musical...")
        
        try:
            # Obtener estadísticas de la biblioteca
            tracks = await self.navidrome.get_tracks(limit=10)
            albums = await self.navidrome.get_albums(limit=10)
            artists = await self.navidrome.get_artists(limit=10)
            
            text = "📚 <b>Tu Biblioteca Musical</b>\n\n"
            
            # Estadísticas generales
            text += f"🎵 <b>Canciones recientes:</b>\n"
            for track in tracks[:5]:
                text += f"• {track.artist} - {track.title}\n"
            
            text += f"\n📀 <b>Álbumes recientes:</b>\n"
            for album in albums[:5]:
                text += f"• {album.artist} - {album.name}\n"
            
            text += f"\n🎤 <b>Artistas recientes:</b>\n"
            for artist in artists[:5]:
                text += f"• {artist.name}\n"
            
            # Botones de navegación
            keyboard = [
                [InlineKeyboardButton("🎵 Ver más canciones", callback_data="library_tracks")],
                [InlineKeyboardButton("📀 Ver más álbumes", callback_data="library_albums")],
                [InlineKeyboardButton("🎤 Ver más artistas", callback_data="library_artists")],
                [InlineKeyboardButton("🔍 Buscar", callback_data="library_search")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error accediendo a la biblioteca: {str(e)}")
    
    @_check_authorization
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats - Mostrar estadísticas
        
        Uso:
        - /stats → Estadísticas de este mes (por defecto)
        - /stats week → Estadísticas de esta semana
        - /stats month → Estadísticas de este mes
        - /stats year → Estadísticas de este año
        - /stats last_week → Estadísticas de la semana pasada
        - /stats last_month → Estadísticas del mes pasado
        - /stats last_year → Estadísticas del año pasado
        - /stats all_time → Estadísticas de todo el tiempo
        """
        # Mapeo de argumentos a rangos de ListenBrainz
        range_mapping = {
            "week": "this_week",
            "this_week": "this_week",
            "month": "this_month",
            "this_month": "this_month",
            "year": "this_year",
            "this_year": "this_year",
            "last_week": "last_week",
            "lastweek": "last_week",
            "last_month": "last_month",
            "lastmonth": "last_month",
            "last_year": "last_year",
            "lastyear": "last_year",
            "all": "all_time",
            "all_time": "all_time",
            "alltime": "all_time"
        }
        
        # Emojis para cada rango
        range_emojis = {
            "this_week": "📅",
            "this_month": "📆",
            "this_year": "📋",
            "last_week": "⏮️",
            "last_month": "⏮️",
            "last_year": "⏮️",
            "all_time": "🌟"
        }
        
        # Nombres en español
        range_names = {
            "this_week": "Esta Semana",
            "this_month": "Este Mes",
            "this_year": "Este Año",
            "last_week": "Semana Pasada",
            "last_month": "Mes Pasado",
            "last_year": "Año Pasado",
            "all_time": "Todo el Tiempo"
        }
        
        # Detectar rango solicitado
        period = "this_month"  # Por defecto: mes actual
        if context.args:
            arg = context.args[0].lower()
            period = range_mapping.get(arg, "this_month")
        
        emoji = range_emojis.get(period, "📊")
        range_name = range_names.get(period, "Este Mes")
        
        await update.message.reply_text(f"{emoji} Calculando tus estadísticas de <b>{range_name}</b>...")
        
        try:
            # Verificar que haya servicio de scrobbling configurado
            if not self.music_service:
                await update.message.reply_text(
                    "⚠️ No hay servicio de scrobbling configurado.\n\n"
                    "Por favor configura Last.fm o ListenBrainz para ver tus estadísticas."
                )
                return
            
            # Obtener estadísticas del periodo especificado
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
            
            # Top álbumes (solo ListenBrainz)
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
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error obteniendo estadísticas: {str(e)}")
    
    @_check_authorization
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /search - Buscar música"""
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
        
        search_term = " ".join(context.args)
        await update.message.reply_text(f"🔍 Buscando '{search_term}' en tu biblioteca...")
        
        try:
            # Buscar en la biblioteca
            results = await self.navidrome.search(search_term, limit=10)
            
            if not results['tracks'] and not results['albums'] and not results['artists']:
                await update.message.reply_text(f"😔 No se encontraron resultados para '{search_term}'")
                return
            
            text = f"🔍 <b>Resultados para '{search_term}':</b>\n\n"
            
            # Mostrar canciones
            if results['tracks']:
                text += "🎵 <b>Canciones:</b>\n"
                for track in results['tracks'][:5]:
                    text += f"• {track.artist} - {track.title}\n"
                text += "\n"
            
            # Mostrar álbumes
            if results['albums']:
                text += "📀 <b>Álbumes:</b>\n"
                for album in results['albums'][:5]:
                    text += f"• {album.artist} - {album.name}\n"
                text += "\n"
            
            # Mostrar artistas
            if results['artists']:
                text += "🎤 <b>Artistas:</b>\n"
                for artist in results['artists'][:5]:
                    text += f"• {artist.name}\n"
            
            # Botones de acción
            keyboard = []
            if results['tracks']:
                keyboard.append([InlineKeyboardButton("🎵 Ver más canciones", callback_data=f"search_tracks_{search_term}")])
            if results['albums']:
                keyboard.append([InlineKeyboardButton("📀 Ver más álbumes", callback_data=f"search_albums_{search_term}")])
            if results['artists']:
                keyboard.append([InlineKeyboardButton("🎤 Ver más artistas", callback_data=f"search_artists_{search_term}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
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
        
        description = " ".join(context.args)
        await update.message.reply_text(f"🎵 Creando playlist: <i>{description}</i>...", parse_mode='HTML')
        
        try:
            # 1. Intentar generar playlist PRIMERO desde la biblioteca local
            print(f"🎵 Generando playlist con: {description}")
            print(f"📚 PASO 1: Intentando generar desde biblioteca local...")
            
            # El límite será ajustado automáticamente por generate_library_playlist
            # si detecta una cantidad en la descripción
            library_recommendations = await self.ai.generate_library_playlist(
                description,
                limit=20  # Límite por defecto aumentado de 15 a 20
            )
            
            recommendations = library_recommendations
            library_count = len(library_recommendations)
            
            print(f"✅ Obtenidas {library_count} recomendaciones de biblioteca")
            
            # Las playlists SIEMPRE son 100% de tu biblioteca local
            # No se agregan canciones externas de Last.fm
            
            if not recommendations:
                # Obtener información de debug para ayudar al usuario
                try:
                    # Obtener algunos géneros disponibles para mostrar
                    sample_tracks = await self.ai.navidrome.get_tracks(limit=50)
                    available_genres = set()
                    for track in sample_tracks:
                        if track.genre:
                            available_genres.add(track.genre)
                    
                    genres_list = list(available_genres)[:10]  # Primeros 10 géneros
                    genres_text = ", ".join(genres_list) if genres_list else "No detectados"
                    
                    await update.message.reply_text(
                        f"😔 No encontré suficiente música en tu biblioteca que coincida con esos criterios.\n\n"
                        f"🔍 <b>Debug info:</b>\n"
                        f"• Géneros detectados en tu biblioteca: {genres_text}\n"
                        f"• Total de canciones en muestra: {len(sample_tracks)}\n\n"
                        f"💡 <b>Intenta:</b>\n"
                        f"• Hacer la descripción más general\n"
                        f"• Mencionar artistas que tengas en tu biblioteca\n"
                        f"• Usar géneros que tengas disponibles\n"
                        f"• Probar: <code>/playlist rock</code> o <code>/playlist pop</code>",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    await update.message.reply_text(
                        "😔 No encontré suficiente música en tu biblioteca que coincida con esos criterios.\n\n"
                        "💡 Intenta:\n"
                        "• Hacer la descripción más general\n"
                        "• Mencionar artistas que tengas en tu biblioteca\n"
                        "• Usar géneros que tengas disponibles"
                    )
                return
            
            print(f"🎵 TOTAL: {len(recommendations)} canciones de tu biblioteca local")
            
            # 3. Crear playlist directamente en Navidrome
            playlist_name = f"Musicalo - {description[:50]}"
            tracks = [rec.track for rec in recommendations]
            song_ids = [track.id for track in tracks if track.id]
            
            if not song_ids:
                await update.message.reply_text(
                    "❌ No se pudieron obtener los IDs de las canciones para crear la playlist."
                )
                return
            
            # Crear playlist en Navidrome
            playlist_id = await self.ai.navidrome.create_playlist(playlist_name, song_ids)
            
            if not playlist_id:
                await update.message.reply_text(
                    "❌ Error al crear la playlist en Navidrome."
                )
                return
            
            # 4. Mostrar preview
            text = f"🎵 <b>Playlist creada en Navidrome:</b> {playlist_name}\n\n"
            text += f"📝 {description}\n\n"
            text += f"📚 <b>{library_count} canciones de tu biblioteca local</b>\n\n"
            text += f"🎼 <b>Canciones ({len(tracks)}):</b>\n"
            
            for i, track in enumerate(tracks[:10], 1):
                text += f"{i}. {track.artist} - {track.title}\n"
            
            if len(tracks) > 10:
                text += f"\n...y {len(tracks) - 10} más\n"
            
            text += f"\n✅ <b>La playlist está disponible en Navidrome</b>"
            text += f"\n🆔 Playlist ID: <code>{playlist_id}</code>"
            
            # Enviar mensaje con resultado
            await update.message.reply_text(text, parse_mode='HTML')
            print(f"✅ Playlist creada en Navidrome con ID: {playlist_id}")
        
        except Exception as e:
            print(f"❌ Error creando playlist: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error creando playlist: {str(e)}")
    
    @_check_authorization
    async def _handle_conversational_query(self, update: Update, user_message: str):
        """Manejar consultas conversacionales usando el agente musical"""
        try:
            print(f"💬 Consulta conversacional: {user_message}")
            
            user_id = update.effective_user.id
            
            # USAR EL AGENTE MUSICAL con soporte conversacional
            # El agente buscará en biblioteca + Last.fm automáticamente
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
                await query.edit_message_text("❤️ ¡Gracias! He registrado que te gusta esta recomendación.")
                print("   ✅ Like procesado")
                
            elif data.startswith("dislike_"):
                print("   ➜ Procesando 'dislike'")
                track_id = data.split("_", 1)[1]
                await query.edit_message_text("👎 Entendido. Evitaré recomendaciones similares.")
                print("   ✅ Dislike procesado")
                
            elif data == "more_recommendations":
                print("   ➜ Procesando 'more_recommendations'")
                await query.edit_message_text("🔄 Generando más recomendaciones...")
                
                # Obtener datos del usuario y generar nuevas recomendaciones
                if self.music_service:
                    recent_tracks = await self.music_service.get_recent_tracks(limit=20)
                    top_artists = await self.music_service.get_top_artists(limit=10)
                    
                    from models.schemas import UserProfile
                    user_profile = UserProfile(
                        recent_tracks=recent_tracks,
                        top_artists=top_artists,
                        favorite_genres=[],
                        mood_preference="",
                        activity_context=""
                    )
                    
                    recommendations = await self.ai.generate_recommendations(user_profile, limit=5)
                    
                    if recommendations:
                        text = "🎵 <b>Nuevas recomendaciones para ti:</b>\n\n"
                        
                        for i, rec in enumerate(recommendations, 1):
                            text += f"<b>{i}.</b> {rec.track.artist} - {rec.track.title}\n"
                            if rec.track.album:
                                text += f"   📀 {rec.track.album}\n"
                            text += f"   💡 {rec.reason}\n"
                            if rec.source:
                                text += f"   🔗 Fuente: {rec.source}\n"
                            text += f"   🎯 {int(rec.confidence * 100)}% match\n\n"
                        
                        keyboard = [
                            [InlineKeyboardButton("❤️ Me gusta", callback_data="like_rec"),
                             InlineKeyboardButton("👎 No me gusta", callback_data="dislike_rec")],
                            [InlineKeyboardButton("🔄 Más recomendaciones", callback_data="more_recommendations")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                    else:
                        await query.edit_message_text("😔 No pude generar más recomendaciones en este momento.")
                else:
                    await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                
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
            
            # Detectar intención usando IntentDetector
            intent_data = await self.intent_detector.detect_intent(
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
            # SOLO 5 intenciones posibles: playlist, buscar, recomendar, referencia, conversacion
            
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
