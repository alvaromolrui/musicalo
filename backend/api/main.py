"""
FastAPI application — punto de entrada de la API REST de Musicalo.

El objeto MusicAssistant se inicializa una vez en el lifespan y se almacena
en app.state.assistant, accesible desde todos los routers.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.music_assistant import MusicAssistant
from api.routes import chat, music, system

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando MusicAssistant...")
    assistant = MusicAssistant()
    await assistant.initialize()
    app.state.assistant = assistant
    logger.info("MusicAssistant listo")
    yield
    logger.info("API detenida")


app = FastAPI(
    title="Musicalo API",
    description="API REST para el asistente musical Musicalo. Consume MusicAssistant directamente.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router,   prefix="/chat",   tags=["chat"])
app.include_router(music.router,  prefix="/music",  tags=["music"])
app.include_router(system.router, prefix="/system", tags=["system"])


@app.get("/", tags=["root"])
async def root():
    return {"service": "Musicalo API", "version": "2.0.0", "docs": "/docs"}


@app.get("/ping", tags=["root"])
async def ping():
    """Health check básico sin autenticación."""
    return {"ok": True}
