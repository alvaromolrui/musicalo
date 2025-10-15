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

class TelegramService:
    def __init__(self):
        self.navidrome = NavidromeService()
        self.listenbrainz = ListenBrainzService()
        self.ai = MusicRecommendationService()
        
        # Detectar qué servicio de scrobbling usar
        self.lastfm = None
        if os.getenv("LASTFM_API_KEY") and os.getenv("LASTFM_USERNAME"):
            self.lastfm = LastFMService()
            self.music_service = self.lastfm
            self.music_service_name = "Last.fm"
            print("✅ Usando Last.fm para datos de escucha")
        elif os.getenv("LISTENBRAINZ_USERNAME"):
            self.music_service = self.listenbrainz
            self.music_service_name = "ListenBrainz"
            print("✅ Usando ListenBrainz para datos de escucha")
        else:
            self.music_service = None
            self.music_service_name = None
            print("⚠️ No hay servicio de scrobbling configurado (Last.fm o ListenBrainz)")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Bienvenida del bot"""
        welcome_text = """
🎵 **¡Bienvenido a Music Agent!**

Soy tu asistente personal de música con IA que entiende lenguaje natural. Puedes hablarme directamente o usar comandos.

**✨ Nuevo: Habla conmigo naturalmente**
Ya no necesitas recordar comandos. Escribe lo que quieras:
• "Recomiéndame música rock"
• "Busca Queen en mi biblioteca"
• "Muéstrame mis estadísticas"
• "¿Qué es el jazz?"

**📝 Comandos disponibles:**
/recommend - Obtener recomendaciones personalizadas
/library - Explorar tu biblioteca musical
/stats - Ver estadísticas de escucha
/search <término> - Buscar música en tu biblioteca
/ask <pregunta> - Pregunta directa a la IA 🤖
/help - Mostrar ayuda

**¿Cómo funciona?**
Analizo tu actividad en Last.fm/ListenBrainz y tu biblioteca de Navidrome para sugerirte música que realmente te gustará.

¡Simplemente escríbeme lo que necesites! 🎶
        """
        
        keyboard = [
            [KeyboardButton("🎵 Recomendaciones"), KeyboardButton("📚 Mi Biblioteca")],
            [KeyboardButton("📊 Estadísticas"), KeyboardButton("🔍 Buscar")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Ayuda detallada"""
        help_text = """
🎵 **Music Agent - Guía de Comandos**

**✨ Lenguaje Natural (NUEVO):**
Ahora puedes escribirme directamente sin usar comandos:
• "Recomiéndame álbumes de rock"
• "Busca Queen"
• "Muéstrame mis estadísticas"
• "¿Qué artistas tengo en mi biblioteca?"
• "¿Qué es el blues?"

**Comandos principales:**
• `/recommend` - Recomendaciones generales
• `/recommend album` - Recomendar álbumes
• `/recommend artist` - Recomendar artistas
• `/recommend track` - Recomendar canciones
• `/library` - Ver tu biblioteca musical
• `/stats` - Estadísticas de escucha
• `/search <término>` - Buscar en tu biblioteca
• `/ask <pregunta>` - Pregunta directa a la IA
• `/prompt <texto>` - Enviar prompt personalizado

**Recomendaciones con filtros:**
• `/recommend rock` - Música de rock
• `/recommend album jazz` - Álbumes de jazz
• `/recommend artist metal` - Artistas de metal
• `/recommend track pop` - Canciones pop

**Recomendaciones similares:**
• `/recommend similar albertucho` - Artistas similares
• `/recommend like extremoduro` - Música parecida
• `/recommend como marea` - Alternativa en español

**Preguntas a la IA:**
• `/ask ¿Qué es el rock progresivo?`
• `/prompt Dame ideas para una playlist`
• `/ask Explícame la historia del jazz`
• `/prompt Recomienda bandas de metal melódico`

**Búsqueda:**
• `/search queen` - Buscar Queen
• `/search bohemian rhapsody` - Buscar canción

**Botones interactivos:**
• ❤️ Me gusta / 👎 No me gusta
• 🔄 Más recomendaciones (genera nuevas)
• 📚 Ver más (biblioteca)
• 📊 Actualizar (estadísticas)

**Servicios:**
• Last.fm: Análisis de escucha y descubrimiento
• Navidrome: Tu biblioteca musical
• Gemini AI: Recomendaciones inteligentes

¿Necesitas ayuda con la configuración? Escribe /setup
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
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
        
        # Extraer límite si está en los args (viene de handle_message)
        if context.args and any(arg.startswith("__limit=") for arg in context.args):
            for arg in context.args[:]:
                if arg.startswith("__limit="):
                    try:
                        recommendation_limit = int(arg.split("=")[1])
                        context.args.remove(arg)
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
        if similar_to:
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
                print(f"🎯 Generando recomendaciones (tipo: {rec_type}, género: {genre_filter}) para {len(recent_tracks)} tracks y {len(top_artists)} artistas...")
                recommendations = await self.ai.generate_recommendations(
                    user_profile, 
                    limit=recommendation_limit,
                    recommendation_type=rec_type,
                    genre_filter=genre_filter
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
            if similar_to:
                text = f"🎯 **Música similar a '{similar_to}':**\n\n"
            elif rec_type == "album":
                text = f"📀 **Álbumes recomendados{f' de {genre_filter}' if genre_filter else ''}:**\n\n"
            elif rec_type == "artist":
                text = f"🎤 **Artistas recomendados{f' de {genre_filter}' if genre_filter else ''}:**\n\n"
            elif rec_type == "track":
                text = f"🎵 **Canciones recomendadas{f' de {genre_filter}' if genre_filter else ''}:**\n\n"
            else:
                text = "🎵 **Tus recomendaciones personalizadas:**\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                # Formato diferente según el tipo de recomendación
                if rec_type == "album":
                    # Para álbumes: mostrar prominentemente el nombre del álbum
                    text += f"**{i}. 📀 {rec.track.title}**\n"
                    text += f"   🎤 Artista: {rec.track.artist}\n"
                elif rec_type == "artist":
                    # Para artistas: solo el nombre del artista
                    text += f"**{i}. 🎤 {rec.track.artist}**\n"
                else:
                    # Para canciones y general: formato estándar
                    text += f"**{i}.** {rec.track.artist} - {rec.track.title}\n"
                    if rec.track.album:
                        text += f"   📀 {rec.track.album}\n"
                
                text += f"   💡 {rec.reason}\n"
                if rec.source:
                    text += f"   🔗 Fuente: {rec.source}\n"
                # Agregar enlace si existe (está en el campo path)
                if rec.track.path:
                    text += f"   🌐 [Ver en Last.fm]({rec.track.path})\n"
                text += f"   🎯 {int(rec.confidence * 100)}% match\n\n"
            
            # Botones de interacción (callback_data limitado a 64 bytes)
            keyboard = [
                [InlineKeyboardButton("❤️ Me gusta", callback_data="like_rec"),
                 InlineKeyboardButton("👎 No me gusta", callback_data="dislike_rec")],
                [InlineKeyboardButton("🔄 Más recomendaciones", callback_data="more_recommendations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            print("✅ Recomendaciones enviadas correctamente")
            
        except Exception as e:
            print(f"❌ Error en recommend_command: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error generando recomendaciones: {str(e)}")
    
    async def library_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /library - Mostrar biblioteca"""
        await update.message.reply_text("📚 Cargando tu biblioteca musical...")
        
        try:
            # Obtener estadísticas de la biblioteca
            tracks = await self.navidrome.get_tracks(limit=10)
            albums = await self.navidrome.get_albums(limit=10)
            artists = await self.navidrome.get_artists(limit=10)
            
            text = "📚 **Tu Biblioteca Musical**\n\n"
            
            # Estadísticas generales
            text += f"🎵 **Canciones recientes:**\n"
            for track in tracks[:5]:
                text += f"• {track.artist} - {track.title}\n"
            
            text += f"\n📀 **Álbumes recientes:**\n"
            for album in albums[:5]:
                text += f"• {album.artist} - {album.name}\n"
            
            text += f"\n🎤 **Artistas recientes:**\n"
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
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error accediendo a la biblioteca: {str(e)}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats - Mostrar estadísticas"""
        await update.message.reply_text("📊 Calculando tus estadísticas musicales...")
        
        try:
            # Verificar que haya servicio de scrobbling configurado
            if not self.music_service:
                await update.message.reply_text(
                    "⚠️ No hay servicio de scrobbling configurado.\n\n"
                    "Por favor configura Last.fm o ListenBrainz para ver tus estadísticas."
                )
                return
            
            # Obtener estadísticas
            user_stats = await self.music_service.get_user_stats() if hasattr(self.music_service, 'get_user_stats') else {}
            recent_tracks = await self.music_service.get_recent_tracks(limit=100)
            top_artists = await self.music_service.get_top_artists(limit=10)
            
            text = "📊 **Tus Estadísticas Musicales**\n\n"
            
            # Estadísticas generales
            text += f"🎵 **Total de escuchas:** {user_stats.get('total_listens', 'N/A')}\n"
            text += f"🎤 **Artistas únicos:** {user_stats.get('total_artists', 'N/A')}\n"
            text += f"📀 **Álbumes únicos:** {user_stats.get('total_albums', 'N/A')}\n"
            text += f"🎼 **Canciones únicas:** {user_stats.get('total_tracks', 'N/A')}\n\n"
            
            # Top artistas
            text += f"🏆 **Top 5 Artistas:**\n"
            for i, artist in enumerate(top_artists[:5], 1):
                text += f"{i}. {artist.name} ({artist.playcount} escuchas)\n"
            
            # Actividad reciente
            if recent_tracks:
                text += f"\n⏰ **Última escucha:**\n"
                last_track = recent_tracks[0]
                text += f"{last_track.artist} - {last_track.name}\n"
            
            # Botones adicionales
            keyboard = [
                [InlineKeyboardButton("📈 Actividad diaria", callback_data="daily_activity")],
                [InlineKeyboardButton("🎯 Géneros favoritos", callback_data="favorite_genres")],
                [InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estadísticas: {str(e)}")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /search - Buscar música"""
        if not context.args:
            await update.message.reply_text(
                "🔍 **Uso:** `/search <término>`\n\n"
                "Ejemplos:\n"
                "• `/search queen`\n"
                "• `/search bohemian rhapsody`\n"
                "• `/search the beatles`"
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
            
            text = f"🔍 **Resultados para '{search_term}':**\n\n"
            
            # Mostrar canciones
            if results['tracks']:
                text += "🎵 **Canciones:**\n"
                for track in results['tracks'][:5]:
                    text += f"• {track.artist} - {track.title}\n"
                text += "\n"
            
            # Mostrar álbumes
            if results['albums']:
                text += "📀 **Álbumes:**\n"
                for album in results['albums'][:5]:
                    text += f"• {album.artist} - {album.name}\n"
                text += "\n"
            
            # Mostrar artistas
            if results['artists']:
                text += "🎤 **Artistas:**\n"
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
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error en la búsqueda: {str(e)}")
    
    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ask o /prompt - Enviar prompts personalizados a la IA
        
        Uso:
        - /ask ¿Qué características tiene el rock progresivo?
        - /prompt Dame ideas para una playlist de estudio
        - /ask Explícame la diferencia entre jazz y blues
        """
        if not context.args:
            await update.message.reply_text(
                "🤖 **Uso:** `/ask <tu pregunta o prompt>`\n\n"
                "También puedes usar `/prompt <tu prompt>`\n\n"
                "**Ejemplos:**\n"
                "• `/ask ¿Qué características tiene el rock progresivo?`\n"
                "• `/prompt Dame ideas para una playlist de estudio`\n"
                "• `/ask Explícame la historia del punk rock`\n"
                "• `/prompt Recomiéndame bandas de metal melódico`\n"
                "• `/ask ¿Cuál es la diferencia entre jazz y blues?`\n\n"
                "💡 Puedes preguntar sobre música, géneros, artistas, historia musical, o pedirle a la IA que te ayude con cualquier tema relacionado con música.",
                parse_mode='Markdown'
            )
            return
        
        # Construir el prompt del usuario
        user_prompt = " ".join(context.args)
        
        # Enviar mensaje de espera
        await update.message.reply_text(f"🤖 Procesando tu pregunta...\n\n_{user_prompt}_", parse_mode='Markdown')
        
        try:
            # Opcional: Agregar contexto del usuario si está disponible
            context_info = ""
            if self.music_service:
                try:
                    # Obtener datos del usuario para dar contexto a la IA
                    recent_tracks = await self.music_service.get_recent_tracks(limit=5)
                    top_artists = await self.music_service.get_top_artists(limit=5)
                    
                    if recent_tracks or top_artists:
                        context_info = "\n\nContexto del usuario para personalizar tu respuesta:\n"
                        if top_artists:
                            context_info += f"Top artistas: {', '.join([artist.name for artist in top_artists[:3]])}\n"
                        if recent_tracks:
                            context_info += f"Escuchas recientes: {', '.join([f'{track.artist}' for track in recent_tracks[:3]])}\n"
                except Exception as e:
                    print(f"⚠️ No se pudo obtener contexto del usuario: {e}")
                    context_info = ""
            
            # Enviar prompt a Gemini
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Construir prompt completo
            full_prompt = f"""Eres un experto asistente musical que ayuda a los usuarios con preguntas sobre música, géneros, artistas, historia musical y recomendaciones.

Pregunta del usuario: {user_prompt}
{context_info}

Proporciona una respuesta útil, informativa y amigable. Si la pregunta es sobre recomendaciones de música específica, intenta ser específico con nombres de artistas, álbumes o canciones."""
            
            print(f"🤖 Enviando prompt a Gemini: {user_prompt}")
            
            # Generar respuesta
            response = model.generate_content(full_prompt)
            ai_response = response.text
            
            print(f"✅ Respuesta de Gemini recibida (longitud: {len(ai_response)})")
            
            # Si la respuesta es muy larga, dividirla en varios mensajes
            max_length = 4000  # Telegram tiene un límite de ~4096 caracteres
            
            if len(ai_response) <= max_length:
                # Enviar respuesta completa (sin parse_mode para evitar errores de formato)
                await update.message.reply_text(
                    f"🤖 Respuesta:\n\n{ai_response}"
                )
            else:
                # Dividir la respuesta en partes
                parts = []
                current_part = ""
                
                for line in ai_response.split('\n'):
                    if len(current_part) + len(line) + 1 > max_length:
                        parts.append(current_part)
                        current_part = line + '\n'
                    else:
                        current_part += line + '\n'
                
                if current_part:
                    parts.append(current_part)
                
                # Enviar cada parte
                for i, part in enumerate(parts):
                    if i == 0:
                        await update.message.reply_text(
                            f"🤖 Respuesta (Parte {i+1}/{len(parts)}):\n\n{part}"
                        )
                    else:
                        await update.message.reply_text(
                            f"Parte {i+1}/{len(parts)}:\n\n{part}"
                        )
            
            print("✅ Respuesta enviada correctamente")
            
        except Exception as e:
            print(f"❌ Error en ask_command: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                f"❌ Error al procesar tu pregunta: {str(e)}\n\n"
                "Verifica que la API de Gemini esté configurada correctamente."
            )
    
    async def _handle_conversational_query(self, update: Update, user_message: str):
        """Manejar consultas conversacionales de forma inteligente usando IA y APIs"""
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            
            # Obtener TODOS los datos disponibles del usuario
            recent_tracks = []
            top_artists = []
            user_stats = {}
            
            if self.music_service:
                try:
                    recent_tracks = await self.music_service.get_recent_tracks(limit=20)
                    top_artists = await self.music_service.get_top_artists(limit=10)
                    if hasattr(self.music_service, 'get_user_stats'):
                        user_stats = await self.music_service.get_user_stats()
                except Exception as e:
                    print(f"Error obteniendo datos del usuario: {e}")
            
            # Construir contexto rico con TODOS los datos
            context_data = "DATOS DISPONIBLES DEL USUARIO:\n\n"
            
            if recent_tracks:
                context_data += "Últimas 20 canciones escuchadas:\n"
                for i, track in enumerate(recent_tracks, 1):
                    context_data += f"{i}. {track.artist} - {track.name}\n"
                context_data += "\n"
            
            if top_artists:
                context_data += "Top 10 artistas favoritos:\n"
                for i, artist in enumerate(top_artists, 1):
                    context_data += f"{i}. {artist.name} ({artist.playcount} escuchas)\n"
                context_data += "\n"
            
            if user_stats:
                context_data += "Estadísticas globales:\n"
                context_data += f"- Total de escuchas: {user_stats.get('total_listens', 'N/A')}\n"
                context_data += f"- Artistas únicos: {user_stats.get('total_artists', 'N/A')}\n"
                context_data += f"- Álbumes únicos: {user_stats.get('total_albums', 'N/A')}\n"
                context_data += f"- Canciones únicas: {user_stats.get('total_tracks', 'N/A')}\n"
            
            # Prompt conversacional INTELIGENTE
            chat_prompt = f"""Eres un asistente musical inteligente y conversacional. 

El usuario te preguntó: "{user_message}"

Tienes acceso a estos datos reales del usuario:

{context_data}

INSTRUCCIONES:
1. Analiza la pregunta del usuario y responde de forma natural y conversacional
2. USA LOS DATOS REALES proporcionados arriba para responder
3. Si preguntan por recomendaciones similares a un artista, busca en sus top artistas o escuchas recientes para dar contexto
4. Si preguntan por "discos" o "álbumes", menciona álbumes específicos de los artistas que escucha
5. Sé específico, usa nombres reales de artistas y canciones de los datos
6. Si no tienes la información exacta pero tienes datos relacionados, ofrece alternativas útiles
7. Responde en español, de forma amigable y directa
8. NO uses formatos de lista largos si la pregunta es específica
9. Si preguntan por algo similar a un artista que NO está en los datos, sugiere artistas que SÍ escucha que podrían ser similares

Respuesta natural y conversacional:"""
            
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(chat_prompt)
            
            response_text = response.text.strip()
            
            # Enviar respuesta conversacional
            await update.message.reply_text(f"🎵 {response_text}")
            print(f"✅ Respuesta conversacional enviada")
            
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
                        text = "🎵 **Nuevas recomendaciones para ti:**\n\n"
                        
                        for i, rec in enumerate(recommendations, 1):
                            text += f"**{i}.** {rec.track.artist} - {rec.track.title}\n"
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
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
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
                    text = "🎵 **Canciones de tu biblioteca:**\n\n"
                    for i, track in enumerate(tracks[:15], 1):
                        text += f"{i}. {track.artist} - {track.title}\n"
                    await query.edit_message_text(text, parse_mode='Markdown')
                    
                elif category == "albums":
                    albums = await self.navidrome.get_albums(limit=20)
                    text = "📀 **Álbumes de tu biblioteca:**\n\n"
                    for i, album in enumerate(albums[:15], 1):
                        text += f"{i}. {album.artist} - {album.name}\n"
                    await query.edit_message_text(text, parse_mode='Markdown')
                    
                elif category == "artists":
                    artists = await self.navidrome.get_artists(limit=20)
                    text = "🎤 **Artistas de tu biblioteca:**\n\n"
                    for i, artist in enumerate(artists[:15], 1):
                        text += f"{i}. {artist.name}\n"
                    await query.edit_message_text(text, parse_mode='Markdown')
                    
                elif category == "search":
                    await query.edit_message_text("🔍 Usa el comando `/search <término>` para buscar música", parse_mode='Markdown')
                else:
                    await query.edit_message_text(f"📚 Cargando {category}...\n\n⚠️ Funcionalidad en desarrollo")
                
                print("   ✅ Library procesado")
                
            elif data == "daily_activity":
                print("   ➜ Procesando 'daily_activity'")
                await query.edit_message_text("📈 Calculando actividad diaria...")
                if self.music_service:
                    activity = await self.music_service.get_listening_activity(days=30) if hasattr(self.music_service, 'get_listening_activity') else {}
                    text = "📈 **Actividad de los últimos 30 días**\n\n"
                    if activity:
                        daily_listens = activity.get("daily_listens", {})
                        text += f"📊 Total de días activos: {activity.get('total_days', 0)}\n"
                        text += f"📊 Promedio diario: {activity.get('avg_daily_listens', 0):.1f} escuchas\n"
                    else:
                        text += "⚠️ No hay datos de actividad disponibles"
                    await query.edit_message_text(text, parse_mode='Markdown')
                    print("   ✅ Daily activity procesado")
                else:
                    await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                    print("   ⚠️ No hay servicio configurado")
                
            elif data == "favorite_genres":
                print("   ➜ Procesando 'favorite_genres'")
                text = "🎯 **Géneros favoritos**\n\n⚠️ Funcionalidad en desarrollo"
                await query.edit_message_text(text, parse_mode='Markdown')
                print("   ✅ Favorite genres procesado")
                
            elif data == "refresh_stats":
                print("   ➜ Procesando 'refresh_stats'")
                await query.edit_message_text("🔄 Actualizando estadísticas...")
                # Recalcular estadísticas
                if self.music_service:
                    user_stats = await self.music_service.get_user_stats() if hasattr(self.music_service, 'get_user_stats') else {}
                    recent_tracks = await self.music_service.get_recent_tracks(limit=100)
                    top_artists = await self.music_service.get_top_artists(limit=10)
                    
                    text = "📊 **Tus Estadísticas Musicales** (Actualizado)\n\n"
                    text += f"🎵 **Total de escuchas:** {user_stats.get('total_listens', 'N/A')}\n"
                    text += f"🎤 **Artistas únicos:** {user_stats.get('total_artists', 'N/A')}\n"
                    text += f"📀 **Álbumes únicos:** {user_stats.get('total_albums', 'N/A')}\n"
                    text += f"🎼 **Canciones únicas:** {user_stats.get('total_tracks', 'N/A')}\n\n"
                    
                    text += f"🏆 **Top 5 Artistas:**\n"
                    for i, artist in enumerate(top_artists[:5], 1):
                        text += f"{i}. {artist.name} ({artist.playcount} escuchas)\n"
                    
                    if recent_tracks:
                        text += f"\n⏰ **Última escucha:**\n"
                        last_track = recent_tracks[0]
                        text += f"{last_track.artist} - {last_track.name}\n"
                    
                    keyboard = [
                        [InlineKeyboardButton("📈 Actividad diaria", callback_data="daily_activity")],
                        [InlineKeyboardButton("🎯 Géneros favoritos", callback_data="favorite_genres")],
                        [InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_stats")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
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
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de texto con IA - Interpreta intención y ejecuta acciones"""
        user_message = update.message.text
        
        # Mensaje de espera
        waiting_msg = await update.message.reply_text("🤔 Analizando tu mensaje...")
        
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            
            # Usar un modelo simple sin function calling - más robusto
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Obtener contexto del usuario para personalizar
            context_info = ""
            if self.music_service:
                try:
                    top_artists = await self.music_service.get_top_artists(limit=3)
                    if top_artists:
                        context_info = f"\nArtistas favoritos del usuario: {', '.join([a.name for a in top_artists[:3]])}"
                except Exception as e:
                    print(f"⚠️ No se pudo obtener contexto: {e}")
            
            # Crear el prompt para la IA - respuesta en JSON
            prompt = f"""Eres un asistente musical inteligente. Analiza el siguiente mensaje del usuario y decide qué acción tomar.

Mensaje del usuario: "{user_message}"
{context_info}

Acciones disponibles:
1. "recommend" - Para recomendar música, álbumes, artistas o canciones
   - Parámetros: 
     * rec_type (general/album/artist/track)
     * genre_filter (opcional, solo para géneros musicales)
     * similar_to (opcional, nombre de artista/álbum para buscar similares)
     * limit (número de resultados: 1, 3, 5, etc. Por defecto 5)
2. "search" - Para buscar música específica en su biblioteca
   - Parámetros: search_term (término de búsqueda)
3. "stats" - Para ver estadísticas de escucha completas (mensaje largo)
4. "library" - Para explorar su biblioteca musical completa (mensaje largo)
5. "chat" - Para CUALQUIER pregunta conversacional sobre música del usuario o recomendaciones complejas
   - Usar cuando pregunte: "cuál es mi última canción", "recomiéndame algo como...", "qué álbumes tengo de..."
   - Parámetros: question (la pregunta del usuario)
6. "question" - Para responder preguntas GENERALES sobre teoría musical, historia, géneros
   - Usar cuando pregunte: "qué es el jazz", "quién inventó el rock"
   - Parámetros: question (la pregunta del usuario)
7. "unknown" - Cuando NO sepas qué acción tomar o el mensaje sea muy complejo/ambiguo
   - Se manejará conversacionalmente con todos los datos del usuario

IMPORTANTE:
- Si el usuario menciona un artista/álbum específico como referencia (ej: "como Pink Floyd", "similar a", "parecido a"), usa "similar_to" con el nombre del artista
- Si pide "un disco" o "álbum" (singular) usa limit=1 y rec_type="album"
- Si pide "discos" o "álbumes" (plural) usa limit=5 y rec_type="album"
- "disco" y "álbum" SIEMPRE significan rec_type="album"
- Si menciona un género musical (rock, jazz, etc) SIN referencia específica, usa "genre_filter"
- Si menciona una referencia específica (artista/álbum), NO uses genre_filter, usa "similar_to"

Responde SOLO con un objeto JSON en este formato exacto (sin markdown, sin explicaciones):
{{"action": "nombre_accion", "params": {{"parametro": "valor"}}}}

Ejemplos:
- "recomiéndame un disco" → {{"action": "recommend", "params": {{"rec_type": "album", "limit": 1}}}}
- "recomiéndame discos de rock" → {{"action": "recommend", "params": {{"rec_type": "album", "genre_filter": "rock", "limit": 5}}}}
- "recomiéndame un disco como Dark Side of the Moon de Pink Floyd" → {{"action": "recommend", "params": {{"rec_type": "album", "similar_to": "Pink Floyd", "limit": 1}}}}
- "recomiéndame un disco de algún grupo similar a Cala vento" → {{"action": "recommend", "params": {{"rec_type": "album", "similar_to": "Cala vento", "limit": 1}}}}
- "artistas similares a Queen" → {{"action": "recommend", "params": {{"rec_type": "artist", "similar_to": "Queen", "limit": 5}}}}
- "busca Queen" → {{"action": "search", "params": {{"search_term": "Queen"}}}}
- "cuál es mi última canción" → {{"action": "chat", "params": {{"question": "cuál es mi última canción"}}}}
- "qué artista he escuchado más" → {{"action": "chat", "params": {{"question": "qué artista he escuchado más"}}}}
- "mis estadísticas" → {{"action": "stats", "params": {{}}}}
- "¿qué es el jazz?" → {{"action": "question", "params": {{"question": "¿qué es el jazz?"}}}}
- "quién inventó el rock" → {{"action": "question", "params": {{"question": "quién inventó el rock"}}}}

Responde AHORA con el JSON:"""
            
            # Generar respuesta
            print(f"🤖 Usuario escribió: {user_message}")
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Limpiar la respuesta si tiene markdown
            if response_text.startswith("```"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            print(f"🤖 Respuesta de IA: {response_text}")
            
            # Parsear JSON
            try:
                action_data = json.loads(response_text)
                action = action_data.get("action", "")
                params = action_data.get("params", {})
                
                print(f"🤖 Acción detectada: {action} con params: {params}")
                
                # Borrar mensaje de espera
                await waiting_msg.delete()
                
                # Ejecutar la acción correspondiente
                if action == "recommend":
                    rec_type = params.get("rec_type", "general")
                    genre_filter = params.get("genre_filter")
                    similar_to = params.get("similar_to")
                    limit = params.get("limit", 5)
                    
                    # Fallback: si el mensaje menciona "disco" o "álbum" y rec_type no está definido, forzar a "album"
                    if rec_type == "general" and any(word in user_message.lower() for word in ["disco", "discos", "álbum", "album", "albumes", "álbumes"]):
                        rec_type = "album"
                        print(f"🔧 Forzando rec_type='album' porque el mensaje menciona disco/álbum")
                    
                    # Construir los argumentos para recommend_command
                    context.args = []
                    
                    # Si hay una referencia específica (similar_to), usarla
                    if similar_to:
                        # IMPORTANTE: Añadir el tipo primero si no es general
                        if rec_type and rec_type != "general":
                            context.args.append(rec_type)
                        context.args.append("similar")
                        context.args.append(similar_to)
                    else:
                        # Si no, usar tipo y género
                        if rec_type and rec_type != "general":
                            context.args.append(rec_type)
                        if genre_filter:
                            context.args.append(genre_filter)
                    
                    # Agregar límite como argumento especial al final
                    context.args.append(f"__limit={limit}")
                    
                    await self.recommend_command(update, context)
                    
                elif action == "search":
                    search_term = params.get("search_term", "")
                    if search_term:
                        context.args = search_term.split()
                        await self.search_command(update, context)
                    else:
                        await update.message.reply_text("❌ No especificaste qué buscar.")
                    
                elif action == "stats":
                    await self.stats_command(update, context)
                    
                elif action == "library":
                    await self.library_command(update, context)
                    
                elif action == "chat":
                    # Respuesta conversacional sobre la música del usuario
                    await self._handle_conversational_query(update, user_message)
                    
                elif action == "unknown" or not action:
                    # Si la IA no sabe qué hacer, intentar respuesta conversacional
                    await self._handle_conversational_query(update, user_message)
                    
                elif action == "question":
                    question = params.get("question", user_message)
                    context.args = question.split()
                    await self.ask_command(update, context)
                
                else:
                    await update.message.reply_text(
                        f"🤔 No entendí bien tu mensaje.\n\n"
                        f"Puedes usar:\n"
                        f"• /recommend - Para recomendaciones\n"
                        f"• /search <término> - Para buscar\n"
                        f"• /stats - Para estadísticas\n"
                        f"• /help - Para ver todos los comandos"
                    )
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"   Respuesta recibida: {response_text}")
                await waiting_msg.edit_text(
                    f"🤔 No pude entender tu mensaje correctamente.\n\n"
                    f"💡 Intenta con:\n"
                    f"• /recommend - Para recomendaciones\n"
                    f"• /search <término> - Para buscar\n"
                    f"• /stats - Para estadísticas"
                )
                
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
                    "• /ask <pregunta> - Preguntar sobre música"
                )
            except:
                await update.message.reply_text(
                    "❌ Hubo un error. Usa /help para ver los comandos disponibles."
                )
