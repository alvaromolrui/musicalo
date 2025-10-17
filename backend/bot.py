import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv

from services.telegram_service import TelegramService

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class MusicAgentBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        self.telegram_service = TelegramService()
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN no está configurado")
        
        # Crear aplicación
        self.application = Application.builder().token(self.token).build()
        
        # Registrar handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Registrar todos los handlers del bot"""
        
        # Comandos
        self.application.add_handler(CommandHandler("start", self.telegram_service.start_command))
        self.application.add_handler(CommandHandler("help", self.telegram_service.help_command))
        self.application.add_handler(CommandHandler("recommend", self.telegram_service.recommend_command))
        self.application.add_handler(CommandHandler("playlist", self.telegram_service.playlist_command))
        self.application.add_handler(CommandHandler("library", self.telegram_service.library_command))
        self.application.add_handler(CommandHandler("stats", self.telegram_service.stats_command))
        self.application.add_handler(CommandHandler("search", self.telegram_service.search_command))
        
        # Callbacks de botones
        self.application.add_handler(CallbackQueryHandler(self.telegram_service.button_callback))
        
        # Mensajes de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.telegram_service.handle_message))
        
        # Manejar errores
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context):
        """Manejar errores del bot"""
        logger.error(f"Error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error inesperado. Intenta de nuevo más tarde."
            )
    
    async def setup_webhook(self):
        """Configurar webhook para recibir actualizaciones"""
        if self.webhook_url:
            webhook_url = f"{self.webhook_url}/webhook"
            try:
                # Verificar si el webhook ya está configurado
                webhook_info = await self.application.bot.get_webhook_info()
                if webhook_info.url == webhook_url:
                    logger.info(f"Webhook ya está configurado: {webhook_url}")
                    return
                
                # Configurar webhook
                await self.application.bot.set_webhook(url=webhook_url)
                logger.info(f"Webhook configurado: {webhook_url}")
            except Exception as e:
                if "Flood control exceeded" in str(e) or "429" in str(e):
                    logger.warning(f"Rate limit de Telegram alcanzado. El webhook probablemente ya está configurado.")
                    logger.info("Continuando con la configuración existente...")
                else:
                    logger.error(f"Error configurando webhook: {e}")
                    raise
        else:
            logger.info("Webhook URL no configurado, usando polling")
    
    async def remove_webhook(self):
        """Remover webhook"""
        await self.application.bot.delete_webhook()
        logger.info("Webhook removido")
    
    def run_polling(self):
        """Ejecutar bot en modo polling"""
        logger.info("Iniciando bot en modo polling...")
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    
    async def run_webhook(self, host="0.0.0.0", port=8000):
        """Ejecutar bot con webhook"""
        logger.info(f"Iniciando bot con webhook en {host}:{port}")
        
        await self.setup_webhook()
        
        # Configurar webhook server
        await self.application.initialize()
        await self.application.start()
        
        # Aquí podrías integrar con FastAPI para manejar webhooks
        # Por ahora, solo mostramos el mensaje
        logger.info("Bot iniciado con webhook. Integra con FastAPI para manejar actualizaciones.")
        
        try:
            # Mantener el bot corriendo
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Deteniendo bot...")
        finally:
            await self.application.stop()
            await self.application.shutdown()

def main():
    """Función principal para ejecutar el bot"""
    try:
        bot = MusicAgentBot()
        
        # Verificar modo de ejecución
        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        
        if webhook_url:
            # Modo webhook
            asyncio.run(bot.run_webhook())
        else:
            # Modo polling (para desarrollo)
            bot.run_polling()
            
    except Exception as e:
        logger.error(f"Error iniciando bot: {e}")
        raise

if __name__ == "__main__":
    main()
