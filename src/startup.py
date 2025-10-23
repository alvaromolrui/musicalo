"""
Startup script for Music Assistant.
Runs the main Telegram bot.
"""

import asyncio
import signal
import sys

from loguru import logger
from main import main as bot_main


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal, stopping services...")
    sys.exit(0)


async def main():
    """Main startup function."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/music_assistant.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days"
    )
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🎵 Starting Music Assistant...")
    
    try:
        # Run the main bot
        await bot_main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        logger.info("Music Assistant stopped")


if __name__ == "__main__":
    asyncio.run(main())
