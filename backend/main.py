"""
Musicalo - API para webhooks de Telegram (opcional)

Este archivo es opcional y solo se usa si quieres manejar webhooks de Telegram
a través de una API REST. Para uso normal, ejecuta directamente bot.py
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Musicalo Webhook API",
    description="API para manejar webhooks de Telegram Bot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Musicalo Webhook API está funcionando",
        "status": "active",
        "bot": "Usa /start en Telegram para comenzar"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "webhook-api"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint para recibir webhooks de Telegram"""
    try:
        # Obtener datos del webhook
        update_data = await request.json()
        logger.info(f"Webhook recibido: {update_data}")
        
        # Aquí podrías procesar el webhook directamente
        # o reenviarlo al bot principal
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bot/info")
async def bot_info():
    """Información del bot"""
    return {
        "bot_name": "Musicalo",
        "description": "Bot de Telegram para recomendaciones musicales con IA",
        "commands": [
            "/start - Iniciar bot",
            "/help - Ayuda",
            "/recommend - Recomendaciones",
            "/library - Biblioteca",
            "/stats - Estadísticas",
            "/search - Buscar música"
        ],
        "features": [
            "Recomendaciones con Google Gemini",
            "Integración con ListenBrainz",
            "Acceso a biblioteca Navidrome",
            "Análisis de patrones musicales"
        ]
    }

if __name__ == "__main__":
    logger.info("Iniciando API de webhooks (opcional)")
    logger.info("Para usar el bot, ejecuta: python bot.py")
    
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "localhost"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
