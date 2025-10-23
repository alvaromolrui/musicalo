"""
Startup script for Music Assistant.
Runs both the health check API and the main bot.
"""

import asyncio
import signal
import sys
from multiprocessing import Process

import uvicorn
from loguru import logger

from health import app as health_app
from main import main as bot_main


def run_health_api():
    """Run the health check API server."""
    try:
        uvicorn.run(
            health_app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False
        )
    except Exception as e:
        logger.error(f"Health API failed: {e}")


def run_bot():
    """Run the main bot."""
    try:
        asyncio.run(bot_main())
    except Exception as e:
        logger.error(f"Bot failed: {e}")


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
    
    # Start health API in a separate process
    health_process = Process(target=run_health_api)
    health_process.start()
    
    # Wait a moment for the health API to start
    await asyncio.sleep(2)
    
    try:
        # Run the main bot
        await bot_main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        # Clean up
        if health_process.is_alive():
            health_process.terminate()
            health_process.join(timeout=5)
            if health_process.is_alive():
                health_process.kill()
        
        logger.info("Music Assistant stopped")


if __name__ == "__main__":
    asyncio.run(main())
