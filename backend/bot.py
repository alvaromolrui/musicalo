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
        self.application.add_handler(CommandHandler("releases", self.telegram_service.releases_command))
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
    
    def run_polling(self):
        """Ejecutar bot en modo polling"""
        logger.info("Iniciando bot en modo polling...")
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    
def main():
    """Función principal para ejecutar el bot"""
    try:
        bot = MusicAgentBot()
        # Ejecutar bot en modo polling
        bot.run_polling()
            
    except Exception as e:
        logger.error(f"Error iniciando bot: {e}")
        raise

if __name__ == "__main__":
    main()
