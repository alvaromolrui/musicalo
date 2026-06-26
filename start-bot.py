#!/usr/bin/env python3
"""
Musicalo — script de inicio.

START_MODE (variable de entorno):
  telegram  (por defecto) — solo bot de Telegram
  api                     — solo API REST (uvicorn en PORT, por defecto 8000)
  both                    — Telegram + API REST simultáneamente
"""
import sys
import os
import asyncio
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

MODE = os.getenv("START_MODE", "telegram").lower()
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")


def run_telegram():
    from bot import main
    print("📱 Modo: Telegram bot")
    main()


async def run_api():
    import uvicorn
    print(f"🌐 Modo: API REST en http://{HOST}:{PORT}")
    config = uvicorn.Config("api.main:app", host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_both():
    """Ejecuta Telegram bot y API REST en el mismo event loop."""
    import uvicorn
    from bot import MusicAgentBot

    print(f"🎵 Modo: Telegram + API REST en http://{HOST}:{PORT}")

    bot = MusicAgentBot()
    application = bot.application

    config = uvicorn.Config("api.main:app", host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)

    async with application:
        await application.start()
        await application.updater.start_polling()
        await server.serve()          # bloquea hasta Ctrl+C
        await application.updater.stop()
        await application.stop()


if __name__ == "__main__":
    print("🎵 Iniciando Musicalo...")
    print("-" * 50)

    try:
        if MODE == "telegram":
            run_telegram()
        elif MODE == "api":
            asyncio.run(run_api())
        elif MODE == "both":
            asyncio.run(run_both())
        else:
            print(f"❌ START_MODE desconocido: '{MODE}'. Usa: telegram | api | both")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Musicalo detenido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
