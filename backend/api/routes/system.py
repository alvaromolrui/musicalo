"""
Endpoints de sistema: estadísticas, salud, analytics, insights.
"""
from fastapi import APIRouter, Depends, Request, Query
from api.auth import verify_api_key
from api.models import StatsResponse, HealthResponse, ChatResponse
from core.music_assistant import MusicAssistant

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _assistant(request: Request) -> MusicAssistant:
    return request.app.state.assistant


@router.get("/stats", response_model=StatsResponse)
async def stats(
    request: Request,
    period: str = Query("this_month", description="this_week | this_month | this_year | last_month | last_year | all_time"),
    user_id: str = Query("anonymous"),
):
    """Devuelve estadísticas de escucha para el periodo indicado."""
    assistant = _assistant(request)
    response = await assistant.get_stats_for_period(period)
    return StatsResponse(text=response.text, success=response.success)


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Estado de salud del sistema (circuit breakers, errores recientes)."""
    assistant = _assistant(request)
    status = assistant.get_health()
    return HealthResponse(
        status=status.get("status", "unknown"),
        health_score=status.get("health_score", 0),
        circuit_breakers=status.get("circuit_breakers", {}),
        recent_errors=status.get("recent_errors", {}),
    )


@router.get("/analytics")
async def analytics(request: Request):
    """Métricas de uso del sistema."""
    assistant = _assistant(request)
    return await assistant.get_analytics()


@router.get("/insights")
async def insights(request: Request, user_id: str = Query("anonymous")):
    """Insights de aprendizaje personalizado del usuario."""
    assistant = _assistant(request)
    uid = int(user_id) if user_id.isdigit() else hash(user_id)
    return await assistant.get_insights(uid)


@router.get("/releases", response_model=ChatResponse)
async def releases(
    request: Request,
    artist: str = Query(None, description="Filtrar por artista (opcional)"),
    user_id: str = Query("anonymous"),
):
    """Lanzamientos recientes de artistas en la biblioteca."""
    assistant = _assistant(request)
    uid = int(user_id) if user_id.isdigit() else hash(user_id)
    query = (
        f"Muéstrame los lanzamientos recientes de {artist}"
        if artist
        else "Muéstrame los lanzamientos recientes de esta semana de artistas de mi biblioteca"
    )
    response = await assistant._agent_query(query, uid)
    return ChatResponse(text=response.text, success=response.success)
