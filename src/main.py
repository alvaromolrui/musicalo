"""
Music Assistant - Main Telegram Bot Application.
Entry point for the AI-powered music library assistant.
"""

import asyncio
import sys
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from loguru import logger

from config import settings, is_user_allowed
from agent import MusicAgent


class MusicAssistantBot:
    """Main bot class for the Music Assistant."""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.agent: Optional[MusicAgent] = None
        
        # Conversation states
        self.SEARCHING = 1
    
    async def initialize(self):
        """Initialize the bot and its components."""
        try:
            # Initialize the AI agent
            self.agent = MusicAgent()
            await self.agent.initialize()
            
            # Initialize the Telegram application
            self.application = Application.builder().token(settings.telegram_bot_token).build()
            
            # Add handlers
            self._add_handlers()
            
            logger.info("Music Assistant bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def _add_handlers(self):
        """Add command and message handlers to the bot."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("sync", self.sync_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        
        # Conversation handler for search
        search_conversation = ConversationHandler(
            entry_points=[CommandHandler("search", self.search_command)],
            states={
                self.SEARCHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search_query)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_search)]
        )
        self.application.add_handler(search_conversation)
        
        # Message handler for general queries
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        if not is_user_allowed(user_id):
            await update.message.reply_text(
                "❌ Sorry, you don't have permission to use this bot.\n"
                "Contact the administrator to get access."
            )
            return
        
        welcome_message = (
            "🎵 **Welcome to Music Assistant!**\n\n"
            "I'm your AI-powered music library assistant. I can help you:\n\n"
            "• 🔍 Search your music library with natural language\n"
            "• 📊 Show your listening statistics\n"
            "• 🎧 Find similar artists and songs\n"
            "• 📈 Analyze your music preferences\n"
            "• 🎵 Discover new music from your collection\n\n"
            "Just type your questions naturally, like:\n"
            "• \"What are my most played artists this month?\"\n"
            "• \"Find me some indie rock albums\"\n"
            "• \"Show me songs similar to Radiohead\"\n\n"
            "Use /help to see all available commands."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Search Music", callback_data="search")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("🔄 Sync Library", callback_data="sync")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🎵 **Music Assistant Commands**\n\n"
            "**Basic Commands:**\n"
            "• `/start` - Welcome message and main menu\n"
            "• `/help` - Show this help message\n"
            "• `/sync` - Manually sync your music library\n"
            "• `/stats` - Show library and listening statistics\n"
            "• `/search` - Start interactive search\n"
            "• `/cancel` - Cancel current operation\n\n"
            "**Natural Language Queries:**\n"
            "Just type your questions naturally! Examples:\n"
            "• \"What indie rock do I have?\"\n"
            "• \"Show me my most played songs this week\"\n"
            "• \"Find albums from the 90s\"\n"
            "• \"What's similar to Pink Floyd?\"\n"
            "• \"Recommend something based on my taste\"\n\n"
            "**Tips:**\n"
            "• Be specific about time periods (this week, last month, 2023)\n"
            "• Mention genres, artists, or moods\n"
            "• Ask for recommendations or similar music\n"
            "• Request statistics about your listening habits"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def sync_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sync command."""
        user_id = update.effective_user.id
        
        if not is_user_allowed(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            await update.message.reply_text("🔄 Starting library synchronization...")
            
            # Trigger sync through the agent
            result = await self.agent.sync_library()
            
            if result.get("success"):
                message = (
                    f"✅ **Sync completed successfully!**\n\n"
                    f"📊 **Statistics:**\n"
                    f"• Artists: {result.get('artists', 0)}\n"
                    f"• Albums: {result.get('albums', 0)}\n"
                    f"• Songs: {result.get('songs', 0)}\n"
                    f"• Duration: {result.get('duration', 'Unknown')}"
                )
            else:
                message = f"❌ Sync failed: {result.get('error', 'Unknown error')}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Sync command failed: {e}")
            await update.message.reply_text(f"❌ Sync failed: {str(e)}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        user_id = update.effective_user.id
        
        if not is_user_allowed(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            await update.message.reply_text("📊 Gathering your music statistics...")
            
            # Get stats through the agent
            stats = await self.agent.get_library_stats()
            
            message = (
                f"📊 **Your Music Library Statistics**\n\n"
                f"🎵 **Library:**\n"
                f"• Artists: {stats.get('library', {}).get('artists', 0)}\n"
                f"• Albums: {stats.get('library', {}).get('albums', 0)}\n"
                f"• Songs: {stats.get('library', {}).get('songs', 0)}\n\n"
                f"🎧 **Listening Activity:**\n"
                f"• Total Plays: {stats.get('listening', {}).get('total_plays', 0)}\n"
                f"• This Week: {stats.get('listening', {}).get('week_plays', 0)}\n"
                f"• This Month: {stats.get('listening', {}).get('month_plays', 0)}\n\n"
                f"🏆 **Top Artists (This Month):**\n"
            )
            
            # Add top artists
            top_artists = stats.get('listening', {}).get('top_artists', [])
            for i, artist in enumerate(top_artists[:5], 1):
                name = artist.get('name', 'Unknown')
                plays = artist.get('play_count', 0)
                message += f"{i}. {name} ({plays} plays)\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Stats command failed: {e}")
            await update.message.reply_text(f"❌ Failed to get statistics: {str(e)}")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        user_id = update.effective_user.id
        
        if not is_user_allowed(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        await update.message.reply_text(
            "🔍 **Interactive Search**\n\n"
            "Type your search query and I'll help you find music in your library.\n\n"
            "Examples:\n"
            "• \"indie rock albums\"\n"
            "• \"songs from the 80s\"\n"
            "• \"artists similar to Radiohead\"\n\n"
            "Type /cancel to exit search mode."
        )
        
        return self.SEARCHING
    
    async def handle_search_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle search query in conversation mode."""
        query = update.message.text
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Process query through the agent
            response = await self.agent.process_query(query)
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
            # Ask for another search
            await update.message.reply_text(
                "🔍 Search for something else, or type /cancel to exit search mode."
            )
            
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            await update.message.reply_text(f"❌ Search failed: {str(e)}")
    
    async def cancel_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel search conversation."""
        await update.message.reply_text("❌ Search cancelled.")
        return ConversationHandler.END
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general text messages."""
        user_id = update.effective_user.id
        
        if not is_user_allowed(user_id):
            await update.message.reply_text("❌ Access denied.")
            return
        
        query = update.message.text
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Process query through the agent
            response = await self.agent.process_query(query)
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            await update.message.reply_text(f"❌ Sorry, I encountered an error: {str(e)}")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if not is_user_allowed(user_id):
            await query.edit_message_text("❌ Access denied.")
            return
        
        if query.data == "search":
            await query.edit_message_text(
                "🔍 **Search Mode**\n\n"
                "Type your search query and I'll help you find music in your library.\n\n"
                "Examples:\n"
                "• \"indie rock albums\"\n"
                "• \"songs from the 80s\"\n"
                "• \"artists similar to Radiohead\""
            )
        
        elif query.data == "stats":
            # Send typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            try:
                stats = await self.agent.get_library_stats()
                
                message = (
                    f"📊 **Your Music Library Statistics**\n\n"
                    f"🎵 **Library:**\n"
                    f"• Artists: {stats.get('library', {}).get('artists', 0)}\n"
                    f"• Albums: {stats.get('library', {}).get('albums', 0)}\n"
                    f"• Songs: {stats.get('library', {}).get('songs', 0)}\n\n"
                    f"🎧 **Listening Activity:**\n"
                    f"• Total Plays: {stats.get('listening', {}).get('total_plays', 0)}\n"
                    f"• This Week: {stats.get('listening', {}).get('week_plays', 0)}\n"
                    f"• This Month: {stats.get('listening', {}).get('month_plays', 0)}"
                )
                
                await query.edit_message_text(message, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Stats callback failed: {e}")
                await query.edit_message_text(f"❌ Failed to get statistics: {str(e)}")
        
        elif query.data == "sync":
            # Send typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            try:
                await query.edit_message_text("🔄 Starting library synchronization...")
                
                result = await self.agent.sync_library()
                
                if result.get("success"):
                    message = (
                        f"✅ **Sync completed successfully!**\n\n"
                        f"📊 **Statistics:**\n"
                        f"• Artists: {result.get('artists', 0)}\n"
                        f"• Albums: {result.get('albums', 0)}\n"
                        f"• Songs: {result.get('songs', 0)}\n"
                        f"• Duration: {result.get('duration', 'Unknown')}"
                    )
                else:
                    message = f"❌ Sync failed: {result.get('error', 'Unknown error')}"
                
                await query.edit_message_text(message, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Sync callback failed: {e}")
                await query.edit_message_text(f"❌ Sync failed: {str(e)}")
        
        elif query.data == "help":
            help_text = (
                "🎵 **Music Assistant Commands**\n\n"
                "**Basic Commands:**\n"
                "• `/start` - Welcome message and main menu\n"
                "• `/help` - Show this help message\n"
                "• `/sync` - Manually sync your music library\n"
                "• `/stats` - Show library and listening statistics\n"
                "• `/search` - Start interactive search\n\n"
                "**Natural Language Queries:**\n"
                "Just type your questions naturally! Examples:\n"
                "• \"What indie rock do I have?\"\n"
                "• \"Show me my most played songs this week\"\n"
                "• \"Find albums from the 90s\"\n"
                "• \"What's similar to Pink Floyd?\""
            )
            
            await query.edit_message_text(help_text, parse_mode='Markdown')
    
    async def run(self):
        """Run the bot."""
        try:
            await self.initialize()
            
            logger.info("Starting Music Assistant bot...")
            
            # Initialize the application
            await self.application.initialize()
            
            # Start the bot
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            # Keep the bot running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Bot failed to start: {e}")
            raise
        finally:
            # Cleanup
            if self.agent:
                await self.agent.cleanup()
            if self.application:
                await self.application.stop()
                await self.application.shutdown()


async def main():
    """Main entry point."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/music_assistant.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days"
    )
    
    # Create and run bot
    bot = MusicAssistantBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
