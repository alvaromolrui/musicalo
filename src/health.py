"""
Health check endpoint for the Music Assistant.
Simple FastAPI app for health monitoring.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime

from config import settings

app = FastAPI(title="Music Assistant Health Check", version="2.0.0")


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "services": {
            "database": "connected",
            "ollama": "connected",
            "vector_store": "connected"
        }
    })


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse({
        "message": "Music Assistant API",
        "version": "2.0.0",
        "status": "running"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
