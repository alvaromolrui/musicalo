from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from typing import List, Dict, Any, Optional
import os
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

Soy tu asistente personal de música que utiliza IA para recomendarte canciones basadas en tus gustos reales.

**Comandos disponibles:**
/recommend - Obtener recomendaciones personalizadas
/library - Explorar tu biblioteca musical
/stats - Ver estadísticas de escucha
/search <término> - Buscar música en tu biblioteca
/help - Mostrar ayuda

**¿Cómo funciona?**
Analizo tu actividad en ListenBrainz y tu biblioteca de Navidrome para sugerirte música que realmente te gustará.

¡Escribe /recommend para empezar! 🎶
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

**Comandos principales:**
• `/recommend` - Obtener recomendaciones basadas en IA
• `/library` - Ver tu biblioteca musical
• `/stats` - Estadísticas de escucha
• `/search <término>` - Buscar canciones, artistas o álbumes

**Ejemplos:**
• `/search queen` - Buscar Queen
• `/search bohemian rhapsody` - Buscar canción específica

**Botones interactivos:**
• ❤️ - Me gusta esta recomendación
• 👎 - No me gusta
• 🔄 - Más recomendaciones
• 🎵 - Reproducir en Navidrome

**Configuración necesaria:**
• ListenBrainz: Para análisis de escucha
• Navidrome: Para tu biblioteca musical
• Gemini AI: Para recomendaciones inteligentes

¿Necesitas ayuda con la configuración? Escribe /setup
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def recommend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /recommend - Generar recomendaciones"""
        await update.message.reply_text("🎵 Analizando tus gustos musicales...")
        
        try:
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
            
            # Generar recomendaciones
            print(f"🎯 Generando recomendaciones para {len(recent_tracks)} tracks y {len(top_artists)} artistas...")
            recommendations = await self.ai.generate_recommendations(user_profile, limit=5)
            print(f"✅ Recomendaciones generadas: {len(recommendations)}")
            
            if not recommendations:
                print("❌ No se generaron recomendaciones")
                await update.message.reply_text(
                    "😔 No pude generar recomendaciones en este momento.\n\n"
                    "Intenta de nuevo más tarde o verifica tu configuración."
                )
                return
            
            print(f"📝 Primera recomendación: {recommendations[0].artist} - {recommendations[0].title}")
            
            # Mostrar recomendaciones
            text = "🎵 **Tus recomendaciones personalizadas:**\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                text += f"**{i}.** {rec.artist} - {rec.title}\n"
                if rec.album:
                    text += f"   📀 {rec.album}\n"
                text += f"   💡 {rec.reason}\n"
                if rec.source:
                    text += f"   🔗 Fuente: {rec.source}\n"
                text += f"   🎯 {int(rec.score * 100)}% match\n\n"
            
            # Botones de interacción
            keyboard = [
                [InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{recommendations[0].track_id}"),
                 InlineKeyboardButton("👎 No me gusta", callback_data=f"dislike_{recommendations[0].track_id}")],
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
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones inline"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            if data.startswith("like_"):
                track_id = data.split("_")[1]
                await query.edit_message_text("❤️ ¡Gracias! He registrado que te gusta esta recomendación.")
                
            elif data.startswith("dislike_"):
                track_id = data.split("_")[1]
                await query.edit_message_text("👎 Entendido. Evitaré recomendaciones similares.")
                
            elif data == "more_recommendations":
                await query.edit_message_text("🔄 Generando más recomendaciones...")
                # Aquí podrías llamar a recommend_command nuevamente
                
            elif data.startswith("play_"):
                track_id = data.split("_")[1]
                # Aquí podrías generar un enlace a Navidrome
                await query.edit_message_text("🎵 Abriendo en Navidrome...")
                
            elif data.startswith("library_"):
                category = data.split("_")[1]
                await query.edit_message_text(f"📚 Cargando {category}...")
                # Implementar lógica real aquí
                
            elif data == "daily_activity":
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
                else:
                    await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                
            elif data == "favorite_genres":
                await query.edit_message_text("🎯 Analizando géneros favoritos...")
                await query.edit_message_text("🎯 **Géneros favoritos**\n\n⚠️ Funcionalidad en desarrollo")
                
            elif data == "refresh_stats":
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
                else:
                    await query.edit_message_text("⚠️ No hay servicio de scrobbling configurado")
                    
            elif data.startswith("search_"):
                parts = data.split("_")
                category = parts[1]
                term = "_".join(parts[2:])
                await query.edit_message_text(f"🔍 Mostrando {category} para '{term}'...")
                
        except Exception as e:
            print(f"❌ Error en callback: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de texto del usuario"""
        text = update.message.text.lower()
        
        if "recomendaciones" in text or "recomendar" in text:
            await self.recommend_command(update, context)
        elif "biblioteca" in text or "música" in text:
            await self.library_command(update, context)
        elif "estadísticas" in text or "stats" in text:
            await self.stats_command(update, context)
        elif "buscar" in text or "search" in text:
            await update.message.reply_text(
                "🔍 Para buscar música, usa el comando:\n"
                "`/search <término>`\n\n"
                "Ejemplo: `/search queen`"
            )
        else:
            await update.message.reply_text(
                "🤔 No entendí tu mensaje.\n\n"
                "Usa /help para ver los comandos disponibles."
            )
