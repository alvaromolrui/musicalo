"""
TelegramService: adaptador de Telegram sobre MusicAssistant.

Responsabilidades de este módulo:
  - Traducir Updates de Telegram en llamadas a MusicAssistant
  - Traducir AssistantResponse en mensajes/teclados de Telegram
  - Autorización de usuarios y tracking de analytics

Lo que NO hace este módulo:
  - Lógica de negocio (recomendaciones, búsqueda, playlists, etc.)
  - Llamadas directas a Navidrome/ListenBrainz/IA
"""
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import ContextTypes
from typing import Optional
import os
import time
from functools import wraps
from datetime import datetime

from core.music_assistant import MusicAssistant
from models.responses import AssistantAction, AssistantResponse, RecommendParams
from services.analytics_system import analytics_system


class TelegramService:
    def __init__(self):
        self.assistant = MusicAssistant()

        # Lista de usuarios permitidos (Telegram-specific)
        allowed_ids_str = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        if allowed_ids_str.strip():
            try:
                self.allowed_user_ids = [
                    int(uid.strip()) for uid in allowed_ids_str.split(",") if uid.strip()
                ]
                print(f"🔒 Bot configurado en modo privado para {len(self.allowed_user_ids)} usuario(s)")
            except ValueError as e:
                print(f"⚠️ Error parseando TELEGRAM_ALLOWED_USER_IDS: {e}")
                self.allowed_user_ids = []
        else:
            self.allowed_user_ids = []
            print("⚠️ Bot en modo público")
            print("💡 Para hacerlo privado, configura TELEGRAM_ALLOWED_USER_IDS en .env")

    # ------------------------------------------------------------------
    # Decoradores
    # ------------------------------------------------------------------

    def _check_authorization(func):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name

            if self.allowed_user_ids and user_id not in self.allowed_user_ids:
                print(f"🚫 Acceso denegado para usuario {username} (ID: {user_id})")
                await update.message.reply_text(
                    "🚫 <b>Acceso Denegado</b>\n\n"
                    "Este bot es privado y solo puede ser usado por usuarios autorizados.\n\n"
                    f"Tu ID de usuario es: <code>{user_id}</code>\n\n"
                    "Si crees que deberías tener acceso, contacta con el administrador del bot "
                    "y proporciona tu ID de usuario.",
                    parse_mode="HTML",
                )
                return
            return await func(self, update, context, *args, **kwargs)
        return wrapper

    def track_analytics(interaction_type: str):
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
                    duration_ms = (time.time() - start_time) * 1000
                    await analytics_system.track_interaction(
                        user_id=user_id,
                        interaction_type=interaction_type,
                        duration_ms=duration_ms,
                        success=success,
                        error_message=error_message,
                    )
            return wrapper
        return decorator

    # ------------------------------------------------------------------
    # Helpers de UI Telegram
    # ------------------------------------------------------------------

    def _actions_to_keyboard(self, actions: list) -> Optional[InlineKeyboardMarkup]:
        if not actions:
            return None
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(a.label, callback_data=a.id) for a in actions
        ]])

    async def _send_response(self, update: Update, response: AssistantResponse):
        """Envía un AssistantResponse como mensaje de Telegram."""
        keyboard = self._actions_to_keyboard(response.actions)
        await update.message.reply_text(
            response.text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    @_check_authorization
    @track_analytics("command")
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """🎵 <b>¡Bienvenido a Musicalo!</b>

Soy tu asistente personal de música con IA que entiende lenguaje natural. Puedes hablarme directamente o usar comandos.

<b>✨ Habla conmigo naturalmente:</b>
• "Recomiéndame música rock"
• "Busca Queen en mi biblioteca"
• "Muéstrame mis estadísticas"
• "¿Qué álbumes tengo de Pink Floyd?"
• "¿Qué estoy escuchando?"

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

¡Simplemente escríbeme lo que necesites! 🎶"""

        keyboard = [
            [KeyboardButton("🎵 Recomendaciones"), KeyboardButton("📚 Mi Biblioteca")],
            [KeyboardButton("📊 Estadísticas"), KeyboardButton("🔍 Buscar")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

    @_check_authorization
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """🎵 <b>Musicalo - Guía de Comandos</b>

<b>✨ Lenguaje Natural:</b>
Escríbeme directamente sin usar comandos:
• "Recomiéndame álbumes de rock"
• "Busca Queen"
• "Muéstrame mis estadísticas"
• "¿Qué artistas tengo en mi biblioteca?"
• "Crea una playlist de rock progresivo"
• "¿Qué estoy escuchando?"

<b>Comandos principales:</b>
• /recommend - Recomendaciones generales
• /recommend album - Recomendar álbumes
• /recommend artist - Recomendar artistas
• /recommend track - Recomendar canciones
• /recommend similar &lt;artista&gt; - Artistas similares
• /recommend biblioteca - Redescubrir tu biblioteca
• /playlist &lt;descripción&gt; - Crear playlist M3U 🎵
• /share &lt;nombre&gt; - Compartir música con enlace público 🔗
• /nowplaying - Ver qué se está reproduciendo ahora 🎧
• /library - Ver tu biblioteca musical
• /stats - Estadísticas de escucha
• /releases - Lanzamientos recientes de tus artistas 🆕
• /search &lt;término&gt; - Buscar en tu biblioteca

<b>Servicios:</b>
• ListenBrainz: Análisis de escucha y recomendaciones
• MusicBrainz: Metadatos detallados
• Navidrome: Tu biblioteca musical
• Gemini AI: Recomendaciones inteligentes

<b>💡 Tip:</b> Puedes preguntarme cualquier cosa sobre música directamente, sin usar comandos. ¡Prueba!"""
        await update.message.reply_text(help_text, parse_mode="HTML")

    @_check_authorization
    @track_analytics("recommendation")
    async def recommend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /recommend [tipo] [género/artista] [__limit=N] [__custom_prompt=...]
        Tipos: album | artist | track | biblioteca | similar
        """
        params = RecommendParams()

        # Extraer flags especiales inyectados por handle_message
        raw_args = list(context.args or [])
        filtered = []
        for arg in raw_args:
            if arg.startswith("__limit="):
                try:
                    params.limit = int(arg.split("=", 1)[1])
                except ValueError:
                    pass
            elif arg.startswith("__custom_prompt="):
                params.custom_prompt = arg.split("=", 1)[1]
            else:
                filtered.append(arg.lower())

        args = filtered

        # Flag de biblioteca
        if any(w in args for w in ["biblioteca", "library", "lib", "redescubrir"]):
            params.from_library_only = True
            args = [a for a in args if a not in ["biblioteca", "library", "lib", "redescubrir"]]

        # Tipo
        if any(w in args for w in ["album", "disco", "álbum"]):
            params.rec_type = "album"
            args = [a for a in args if a not in ["album", "disco", "álbum"]]
        elif any(w in args for w in ["artist", "artista", "banda", "grupo"]):
            params.rec_type = "artist"
            args = [a for a in args if a not in ["artist", "artista", "banda", "grupo"]]
        elif any(w in args for w in ["track", "song", "cancion", "canción", "tema"]):
            params.rec_type = "track"
            args = [a for a in args if a not in ["track", "song", "cancion", "canción", "tema"]]

        # Similar a
        for kw in ["similar", "like", "como", "parecido"]:
            if kw in args:
                idx = args.index(kw)
                if idx + 1 < len(args):
                    params.similar_to = " ".join(args[idx + 1:])
                break
        else:
            if args:
                params.genre_filter = " ".join(args)

        # Mensaje de estado
        if params.custom_prompt:
            status = f"🎨 Analizando tu petición: '{params.custom_prompt}'..."
        elif params.similar_to:
            status = f"🔍 Buscando música similar a '{params.similar_to}'..."
        elif params.rec_type == "album":
            status = "📀 Analizando álbumes..."
        elif params.rec_type == "artist":
            status = "🎤 Buscando artistas..."
        elif params.rec_type == "track":
            status = "🎵 Buscando canciones..."
        elif params.from_library_only:
            status = "📚 Analizando tu biblioteca para redescubrir música..."
        else:
            status = "🎵 Analizando tus gustos musicales..."

        await update.message.reply_text(status)

        try:
            if params.similar_to and not self.assistant.music_service:
                pass  # get_recommendations maneja el caso sin music_service para similar_to

            if not params.similar_to and not self.assistant.music_service:
                await update.message.reply_text(
                    "⚠️ No hay servicio de scrobbling configurado.\n\n"
                    "Por favor configura ListenBrainz (LISTENBRAINZ_USERNAME en .env) "
                    "para recibir recomendaciones personalizadas."
                )
                return

            recommendations = await self.assistant.get_recommendations(
                update.effective_user.id, params
            )

            if not recommendations:
                if params.similar_to:
                    await update.message.reply_text(
                        f"😔 No encontré artistas similares a '{params.similar_to}'\n\n"
                        "Intenta con un artista más conocido o usa /recommend para recomendaciones generales."
                    )
                else:
                    await update.message.reply_text(
                        "😔 No pude generar recomendaciones en este momento.\n\n"
                        "Intenta de nuevo más tarde o verifica tu configuración."
                    )
                return

            response = self.assistant._format_recommendations(
                recommendations,
                similar_to=params.similar_to,
                custom_prompt=params.custom_prompt,
                rec_type=params.rec_type,
                genre_filter=params.genre_filter,
            )

            # Guardar en sesión conversacional
            session = self.assistant.conversation_manager.get_session(update.effective_user.id)
            session.set_last_recommendations(recommendations)

            await self._send_response(update, response)

        except Exception as e:
            print(f"❌ Error en recommend_command: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error generando recomendaciones: {e}")

    @_check_authorization
    async def library_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📚 Analizando tu biblioteca musical...")
        try:
            response = await self.assistant._agent_query(
                "Muéstrame un resumen de mi biblioteca musical con recomendaciones",
                update.effective_user.id,
            )
            await self._send_response(update, response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error accediendo a la biblioteca: {e}")

    @_check_authorization
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        period_map = {
            "week": "esta semana", "month": "este mes", "year": "este año",
            "all": "de todo el tiempo", "all_time": "de todo el tiempo",
        }
        period = period_map.get((context.args or ["month"])[0].lower(), "este mes")
        await update.message.reply_text(f"📊 Analizando tus estadísticas de {period}...")
        try:
            response = await self.assistant._agent_query(
                f"Muéstrame mis estadísticas de escucha de {period}",
                update.effective_user.id,
            )
            await self._send_response(update, response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estadísticas: {e}")

    @_check_authorization
    async def releases_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Buscando lanzamientos recientes...")
        query = (
            f"Muéstrame los lanzamientos recientes de {' '.join(context.args)}"
            if context.args
            else "Muéstrame los lanzamientos recientes de esta semana de artistas de mi biblioteca"
        )
        try:
            response = await self.assistant._agent_query(query, update.effective_user.id)
            await self._send_response(update, response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo lanzamientos: {e}")

    @_check_authorization
    @track_analytics("search")
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "🔍 <b>Uso:</b> <code>/search &lt;término&gt;</code>\n\n"
                "Ejemplos:\n• <code>/search queen</code>\n• <code>/search bohemian rhapsody</code>",
                parse_mode="HTML",
            )
            return
        search_term = " ".join(context.args)
        await update.message.reply_text(f"🔍 Buscando '{search_term}' en tu biblioteca...")
        try:
            response = await self.assistant._agent_query(
                f"Busca '{search_term}' en mi biblioteca y dime qué tengo",
                update.effective_user.id,
            )
            await self._send_response(update, response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error en la búsqueda: {e}")

    @_check_authorization
    async def playlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "🎵 <b>Crear Playlist</b>\n\n"
                "<b>Uso:</b> <code>/playlist &lt;descripción&gt;</code>\n\n"
                "<b>Ejemplos:</b>\n"
                "• <code>/playlist rock progresivo de los 70s</code>\n"
                "• <code>/playlist música energética para correr</code>\n"
                "• <code>/playlist jazz suave</code>",
                parse_mode="HTML",
            )
            return
        description = " ".join(context.args)
        await update.message.reply_text(f"🎵 Creando playlist: <i>{description}</i>...", parse_mode="HTML")
        try:
            response = await self.assistant._agent_query(
                f"Crea una playlist de {description} con canciones de mi biblioteca",
                update.effective_user.id,
            )
            await self._send_response(update, response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error creando playlist: {e}")

    @_check_authorization
    async def share_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "🔗 <b>Compartir Música</b>\n\n"
                "<b>Uso:</b> <code>/share &lt;nombre&gt;</code>\n\n"
                "<b>Ejemplos:</b>\n"
                "• <code>/share The Dark Side of the Moon</code>\n"
                "• <code>/share Bohemian Rhapsody</code>\n"
                "• <code>/share Queen</code>",
                parse_mode="HTML",
            )
            return

        search_term = " ".join(context.args)
        await update.message.reply_text(f"🔍 Buscando '{search_term}' para compartir...")

        try:
            result = await self.assistant.create_share(search_term)

            if not result:
                await update.message.reply_text(
                    f"😔 No encontré '{search_term}' en tu biblioteca.\n\n"
                    f"💡 Intenta buscar primero con <code>/search {search_term}</code>",
                    parse_mode="HTML",
                )
                return

            text = (
                f"✅ <b>Enlace compartido creado</b>\n\n"
                f"{'📀' if result.share_type == 'álbum' else '🎵' if result.share_type == 'canción' else '🎤'} "
                f"{result.found_name}\n"
                f"📦 <b>{result.item_count}</b> {'canción' if result.item_count == 1 else 'canciones'}\n\n"
                f"🔗 <b>Enlace del share:</b>\n<code>{result.url}</code>\n\n"
                f"📋 Tipo: {result.share_type} · ID: <code>{result.id}</code>\n"
                f"✨ Enlace público sin autenticación"
            )
            if result.used_flexible_search:
                text += f"\n\nℹ️ <i>Búsqueda flexible activada para '{search_term}'</i>"

            await update.message.reply_text(text, parse_mode="HTML")

        except Exception as e:
            print(f"❌ Error en share_command: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"❌ Error creando enlace: {e}")

    @_check_authorization
    async def nowplaying_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🎵 Consultando reproducción actual...")
        try:
            response = await self.assistant._agent_query(
                "¿Qué estoy escuchando ahora?", update.effective_user.id
            )
            await self._send_response(update, response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo reproducción: {e}")

    @_check_authorization
    @track_analytics("analytics")
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        admin_ids = [
            int(uid.strip())
            for uid in os.getenv("TELEGRAM_ADMIN_USER_IDS", "").split(",")
            if uid.strip()
        ]
        if admin_ids and user_id not in admin_ids:
            await update.message.reply_text(
                "🚫 <b>Acceso Denegado</b>\n\nEste comando solo está disponible para administradores.",
                parse_mode="HTML",
            )
            return

        await update.message.reply_text("📊 Generando reporte de analytics...")
        try:
            insights = await self.assistant.get_analytics()
            if "error" in insights:
                await update.message.reply_text(f"❌ Error: {insights['error']}")
                return

            metrics = insights.get("metrics", {})
            performance = insights.get("performance", {})

            text = "📊 <b>Analytics del Sistema</b>\n\n"
            text += f"🕐 <b>Período:</b> Últimas {metrics.get('period_hours', 24)} horas\n"
            text += f"👥 <b>Usuarios únicos:</b> {metrics.get('unique_users', 0)}\n"
            text += f"🔄 <b>Total interacciones:</b> {metrics.get('total_interactions', 0)}\n"
            text += f"✅ <b>Tasa de éxito:</b> {metrics.get('success_rate', 0):.1f}%\n"
            text += f"⚡ <b>Tiempo promedio:</b> {metrics.get('average_duration_ms', 0):.0f}ms\n"
            text += f"💾 <b>Cache hit rate:</b> {metrics.get('cache_hit_rate', 0):.1f}%\n\n"

            interactions = metrics.get("interactions_by_type", {})
            if interactions:
                text += "📈 <b>Interacciones por tipo:</b>\n"
                for t, count in sorted(interactions.items(), key=lambda x: x[1], reverse=True):
                    text += f"• {t}: {count}\n"

            text += f"\n🕐 <i>Actualizado: {insights.get('timestamp', 'N/A')}</i>"
            await update.message.reply_text(text, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo analytics: {e}")

    @_check_authorization
    @track_analytics("insights")
    async def insights_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🧠 Analizando tus patrones de escucha...")
        try:
            insights = await self.assistant.get_insights(update.effective_user.id)
            if "error" in insights:
                await update.message.reply_text(f"❌ Error: {insights['error']}")
                return

            text = "🧠 <b>Insights de Aprendizaje Personalizado</b>\n\n"
            score = insights.get("personalization_score", 0)
            text += f"🎯 <b>Nivel de personalización:</b> {score:.1%}\n"

            preferences = insights.get("preferences", {})
            if preferences:
                text += "\n📊 <b>Preferencias detectadas:</b>\n"
                for feature, values in preferences.items():
                    if values:
                        text += f"• <b>{feature.title()}:</b> {', '.join([v[0] for v in values[:3]])}\n"

            patterns = insights.get("patterns", [])
            if patterns:
                text += "\n🔍 <b>Patrones detectados:</b>\n"
                for p in patterns:
                    text += f"• {p.get('type', '').replace('_', ' ').title()}: {p.get('confidence', 0):.1%}\n"

            suggestions = insights.get("improvement_suggestions", [])
            if suggestions:
                text += "\n💡 <b>Sugerencias:</b>\n"
                for s in suggestions:
                    text += f"• {s}\n"

            text += f"\n📈 Interacciones: {insights.get('total_feedback', 0)}"
            if score < 0.3:
                text += "\n\n💡 <i>Tip: Usa ❤️/👎 en las recomendaciones para mejorar la personalización</i>"

            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo insights: {e}")

    @_check_authorization
    @track_analytics("hybrid")
    async def hybrid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🎯 Generando recomendaciones híbridas avanzadas...")
        try:
            user_profile = await self.assistant.get_user_profile(update.effective_user.id)
            if not user_profile:
                await update.message.reply_text("❌ No se pudo obtener tu perfil. Usa /start primero.")
                return

            recommendations = await self.assistant.ai.generate_hybrid_recommendations(
                user_profile, update.effective_user.id, max_recommendations=10
            )
            if not recommendations:
                await update.message.reply_text("❌ No se pudieron generar recomendaciones híbridas.")
                return

            text = "🎯 <b>Recomendaciones Híbridas Avanzadas</b>\n\n"
            for i, rec in enumerate(recommendations[:5], 1):
                text += f"{i}. <b>{rec.track.title}</b> - {rec.track.artist}\n"
                text += f"   🎵 {rec.reasoning}\n"
                text += f"   📊 Confianza: {rec.confidence:.1%}\n"
                strategy_tags = [t for t in rec.tags if t.startswith("hybrid:")]
                if strategy_tags:
                    text += f"   🔧 Estrategia: {strategy_tags[0].split(':')[1]}\n"
                text += "\n"
            if len(recommendations) > 5:
                text += f"... y {len(recommendations) - 5} más\n"
            text += "\n💡 <i>Combinando múltiples estrategias de IA</i>"
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error generando recomendaciones híbridas: {e}")

    @_check_authorization
    @track_analytics("profile")
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🧠 Analizando tu perfil musical avanzado...")
        try:
            user_profile = await self.assistant.get_user_profile(update.effective_user.id)
            if not user_profile:
                await update.message.reply_text("❌ No se pudo obtener tu perfil.")
                return

            advanced_profile = await self.assistant.ai.analyze_advanced_user_profile(
                user_profile, update.effective_user.id
            )
            if "error" in advanced_profile:
                await update.message.reply_text(f"❌ Error: {advanced_profile['error']}")
                return

            text = "🧠 <b>Tu Perfil Musical Avanzado</b>\n\n"
            personality = advanced_profile.get("personality", {})
            if personality:
                text += "🎭 <b>Personalidad Musical:</b>\n"
                for trait, score in personality.get("traits", {}).items():
                    if score > 0.3:
                        text += f"• {trait.replace('_', ' ').title()}: {score:.1%}\n"
                text += f"\n🔍 <b>Descubrimiento:</b> {personality.get('discovery_rate', 0):.1%}\n"
                text += f"👥 <b>Influencia Social:</b> {personality.get('social_influence', 0):.1%}\n\n"

            prefs = advanced_profile.get("contextual_preferences", [])
            if prefs:
                text += "🎯 <b>Preferencias Contextuales:</b>\n"
                for p in prefs[:3]:
                    ctx = p["context"].replace("_", " ").title()
                    genres = ", ".join(p["preferred_genres"][:3])
                    text += f"• {ctx}: {genres}\n"
                text += "\n"

            li = advanced_profile.get("learning_insights", {})
            if li:
                text += f"📊 <b>Personalización:</b> {li.get('personalization_score', 0):.1%}\n"
                text += f"💬 <b>Interacciones:</b> {li.get('total_feedback', 0)}\n\n"

            mp = advanced_profile.get("music_preferences", {})
            if mp:
                text += "🎵 <b>Estadísticas Musicales:</b>\n"
                text += f"• Géneros únicos: {mp.get('genre_diversity', 0)}\n"
                text += f"• Artistas únicos: {mp.get('artist_diversity', 0)}\n"

            text += f"\n🕐 <i>Actualizado: {advanced_profile.get('last_updated', 'N/A')}</i>"
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error analizando perfil: {e}")

    @_check_authorization
    @track_analytics("discover")
    async def discover_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Descubriendo nueva música para ti...")
        try:
            user_profile = await self.assistant.get_user_profile(update.effective_user.id)
            if not user_profile:
                await update.message.reply_text("❌ No se pudo obtener tu perfil.")
                return

            recommendations = await self.assistant.ai.discover_new_music(
                user_profile, update.effective_user.id, "mixed"
            )
            if not recommendations:
                await update.message.reply_text("❌ No se pudieron generar descubrimientos.")
                return

            self.assistant.ai.track_user_activity(update.effective_user.id, "recommendation_given")

            text = "🔍 <b>Descubrimientos Musicales</b>\n\n"
            for i, rec in enumerate(recommendations[:5], 1):
                text += f"{i}. <b>{rec.track.title}</b> - {rec.track.artist}\n"
                text += f"   🎵 {rec.reasoning}\n"
                text += f"   📊 Confianza: {rec.confidence:.1%}\n"
                dtags = [t for t in rec.tags if t in ["discovery", "serendipity", "similar_artists", "genre_exploration"]]
                if dtags:
                    text += f"   🔍 Tipo: {', '.join(dtags)}\n"
                text += "\n"
            if len(recommendations) > 5:
                text += f"... y {len(recommendations) - 5} más\n"
            text += "\n💡 <i>Basados en tus gustos y patrones de escucha</i>"
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error descubriendo música: {e}")

    @_check_authorization
    @track_analytics("leaderboard")
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🏆 Obteniendo tabla de clasificación...")
        try:
            leaderboard = self.assistant.ai.get_leaderboard(10)
            if not leaderboard:
                await update.message.reply_text("❌ No hay datos de clasificación disponibles.")
                return

            text = "🏆 <b>Tabla de Clasificación Musicalo</b>\n\n"
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            for entry in leaderboard:
                rank = entry["rank"]
                medal = medals.get(rank, "🏅")
                text += f"{medal} <b>#{rank}</b> - Nivel {entry['level']} ({entry['experience_points']} pts)\n"
            text += f"\n💡 <i>Usa el bot más para subir en la clasificación</i>"
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo clasificación: {e}")

    @_check_authorization
    @track_analytics("health")
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🏥 Verificando estado de salud del sistema...")
        try:
            health_status = self.assistant.get_health()
            system_health = self.assistant.get_system_health()

            status = health_status.get("status", "unknown")
            health_score = health_status.get("health_score", 0)
            status_emoji = {"healthy": "✅", "degraded": "⚠️"}.get(status, "❌")

            text = "🏥 <b>Estado de Salud del Sistema</b>\n\n"
            text += f"{status_emoji} <b>Estado:</b> {status.title()}\n"
            text += f"📊 <b>Puntuación:</b> {health_score}/100\n\n"

            for svc, info in health_status.get("circuit_breakers", {}).items():
                state = info.get("state", "unknown")
                icon = {"OPEN": "🔴", "HALF_OPEN": "🟡"}.get(state, "🟢")
                text += f"{icon} {svc}: {state}\n"

            recent_errors = health_status.get("recent_errors", {})
            if recent_errors:
                text += f"\n📈 <b>Errores (24h):</b> {recent_errors.get('total_errors', 0)}\n"

            text += f"\n🕐 <i>Actualizado: {datetime.now().strftime('%H:%M:%S')}</i>"
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estado de salud: {e}")

    # ------------------------------------------------------------------
    # Callbacks de botones inline
    # ------------------------------------------------------------------

    @_check_authorization
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        print(f"🔘 Botón presionado: {data}")

        try:
            if data.startswith("like_"):
                await self.assistant.process_feedback(user_id, data.split("_", 1)[1], "like")
                await query.edit_message_text("❤️ ¡Gracias! He registrado que te gusta esta recomendación.")

            elif data.startswith("dislike_"):
                await self.assistant.process_feedback(user_id, data.split("_", 1)[1], "dislike")
                await query.edit_message_text("👎 Entendido. Evitaré recomendaciones similares.")

            elif data == "more_recommendations":
                await query.edit_message_text("🔄 Generando más recomendaciones...")
                result = await self.assistant._agent_query(
                    "Recomiéndame 5 canciones diferentes basándote en mis gustos", user_id
                )
                text = f"🎵 <b>Nuevas recomendaciones para ti:</b>\n\n{result.text}"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❤️ Me gusta", callback_data="like_rec"),
                     InlineKeyboardButton("👎 No me gusta", callback_data="dislike_rec")],
                    [InlineKeyboardButton("🔄 Más recomendaciones", callback_data="more_recommendations")],
                ])
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

            elif data.startswith("library_"):
                category = data.split("_", 1)[1]
                if category == "search":
                    await query.edit_message_text(
                        "🔍 Usa <code>/search &lt;término&gt;</code> para buscar música",
                        parse_mode="HTML",
                    )
                else:
                    await query.edit_message_text(f"📚 Cargando {category}...")
                    response = await self.assistant.get_library_items(category)
                    await query.edit_message_text(response.text, parse_mode="HTML")

            elif data == "daily_activity":
                await query.edit_message_text("📈 Calculando actividad diaria...")
                activity = await self.assistant.get_listening_activity(days=30)
                text = "📈 <b>Actividad de los últimos 30 días</b>\n\n"
                if activity:
                    text += f"📊 Días activos: {activity.get('total_days', 0)}\n"
                    text += f"📊 Promedio diario: {activity.get('avg_daily_listens', 0):.1f} escuchas\n"
                else:
                    text += "⚠️ No hay datos de actividad disponibles"
                await query.edit_message_text(text, parse_mode="HTML")

            elif data == "favorite_genres":
                await query.edit_message_text(
                    "🎯 <b>Géneros favoritos</b>\n\n⚠️ Funcionalidad en desarrollo",
                    parse_mode="HTML",
                )

            elif data == "refresh_stats":
                await query.edit_message_text("🔄 Actualizando estadísticas...")
                stats = await self.assistant.get_user_stats_summary()
                recent = await self.assistant.music_service.get_recent_tracks(limit=1) if self.assistant.music_service else []
                top_artists = await self.assistant.music_service.get_top_artists(limit=5) if self.assistant.music_service else []

                text = "📊 <b>Tus Estadísticas Musicales</b> (Actualizado)\n\n"
                text += f"🎵 <b>Total de escuchas:</b> {stats.get('total_listens', 'N/A')}\n"
                text += f"🎤 <b>Artistas únicos:</b> {stats.get('total_artists', 'N/A')}\n"
                text += f"📀 <b>Álbumes únicos:</b> {stats.get('total_albums', 'N/A')}\n"
                text += f"🎼 <b>Canciones únicas:</b> {stats.get('total_tracks', 'N/A')}\n\n"
                if top_artists:
                    text += "🏆 <b>Top 5 Artistas:</b>\n"
                    for i, a in enumerate(top_artists, 1):
                        text += f"{i}. {a.name} ({a.playcount} escuchas)\n"
                if recent:
                    text += f"\n⏰ <b>Última escucha:</b>\n{recent[0].artist} - {recent[0].name}\n"

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📈 Actividad diaria", callback_data="daily_activity")],
                    [InlineKeyboardButton("🎯 Géneros favoritos", callback_data="favorite_genres")],
                    [InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_stats")],
                ])
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

            elif data.startswith("stats_"):
                period = data.replace("stats_", "")
                period_names = {
                    "this_week": "Esta Semana", "this_month": "Este Mes",
                    "this_year": "Este Año", "last_week": "Semana Pasada",
                    "last_month": "Mes Pasado", "last_year": "Año Pasado",
                    "all_time": "Todo el Tiempo",
                }
                period_name = period_names.get(period, "Este Mes")
                await query.edit_message_text(f"📊 Calculando estadísticas de <b>{period_name}</b>...", parse_mode="HTML")

                response = await self.assistant.get_stats_for_period(period)
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Esta Semana", callback_data="stats_this_week"),
                     InlineKeyboardButton("📆 Este Mes", callback_data="stats_this_month")],
                    [InlineKeyboardButton("📋 Este Año", callback_data="stats_this_year"),
                     InlineKeyboardButton("🌟 Todo el Tiempo", callback_data="stats_all_time")],
                    [InlineKeyboardButton("⏮️ Mes Pasado", callback_data="stats_last_month"),
                     InlineKeyboardButton("⏮️ Año Pasado", callback_data="stats_last_year")],
                ])
                await query.edit_message_text(response.text, reply_markup=keyboard, parse_mode="HTML")

            elif data.startswith("play_"):
                await query.edit_message_text("🎵 Abriendo en Navidrome...\n\n⚠️ Funcionalidad en desarrollo")

            else:
                await query.edit_message_text(f"⚠️ Opción no implementada: {data}")

        except Exception as e:
            print(f"❌ Error en callback: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await query.edit_message_text(f"❌ Error: {e}")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Mensajes de texto libre
    # ------------------------------------------------------------------

    @_check_authorization
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        user_id = update.effective_user.id
        waiting_msg = await update.message.reply_text("🤔 Analizando tu mensaje...")

        try:
            print(f"💬 Usuario {user_id}: {user_message}")
            response = await self.assistant.chat(user_id, user_message)
            await waiting_msg.delete()
            await self._send_response(update, response)

        except Exception as e:
            print(f"❌ Error en handle_message: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await waiting_msg.edit_text(
                    f"❌ Error procesando tu mensaje: {e}\n\n"
                    "💡 Puedes usar comandos directos:\n"
                    "• /recommend - Recomendaciones\n"
                    "• /search <término> - Buscar música\n"
                    "• /stats - Estadísticas\n"
                    "• /playlist <descripción> - Crear playlist"
                )
            except Exception:
                await update.message.reply_text(
                    "❌ Hubo un error. Usa /help para ver los comandos disponibles."
                )
