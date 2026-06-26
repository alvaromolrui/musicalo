"""
Endpoints de música: recomendaciones, búsqueda, compartir, reproducción actual.
"""
from fastapi import APIRouter, Depends, Request, Query
from typing import Optional
from api.auth import verify_api_key
from api.models import (
    RecommendRequest, RecommendResponse, RecommendationItem,
    ShareRequest, ShareResponse,
    ChatResponse, ActionItem,
    FeedbackRequest,
)
from models.responses import RecommendParams
from core.music_assistant import MusicAssistant

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _assistant(request: Request) -> MusicAssistant:
    return request.app.state.assistant


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(body: RecommendRequest, request: Request):
    """Genera recomendaciones personalizadas."""
    assistant = _assistant(request)
    params = RecommendParams(
        rec_type=body.rec_type,
        genre_filter=body.genre_filter,
        similar_to=body.similar_to,
        limit=body.limit,
        custom_prompt=body.custom_prompt,
        from_library_only=body.from_library_only,
    )
    user_id = int(body.user_id) if body.user_id.isdigit() else hash(body.user_id)
    recommendations = await assistant.get_recommendations(user_id, params)

    response = assistant._format_recommendations(
        recommendations,
        similar_to=params.similar_to,
        custom_prompt=params.custom_prompt,
        rec_type=params.rec_type,
        genre_filter=params.genre_filter,
        from_library=params.from_library_only,
    )

    items = [
        RecommendationItem(
            title=rec.track.title,
            artist=rec.track.artist,
            album=rec.track.album or None,
            reason=rec.reason,
            confidence=rec.confidence,
            source=rec.source,
            url=rec.track.path or None,
        )
        for rec in recommendations
    ]

    return RecommendResponse(
        recommendations=items,
        text=response.text,
        actions=[ActionItem(id=a.id, label=a.label) for a in response.actions],
        success=response.success,
    )


@router.get("/search", response_model=ChatResponse)
async def search(
    request: Request,
    q: str = Query(..., description="Término de búsqueda"),
    user_id: str = Query("anonymous"),
):
    """Busca en la biblioteca musical."""
    assistant = _assistant(request)
    uid = int(user_id) if user_id.isdigit() else hash(user_id)
    response = await assistant._agent_query(
        f"Busca '{q}' en mi biblioteca y dime qué tengo", uid
    )
    return ChatResponse(text=response.text, success=response.success)


@router.post("/share", response_model=ShareResponse)
async def share(body: ShareRequest, request: Request):
    """Crea un enlace público compartible en Navidrome."""
    assistant = _assistant(request)
    result = await assistant.create_share(body.search_term)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No se encontró '{body.search_term}' en la biblioteca.")
    return ShareResponse(
        url=result.url,
        id=result.id,
        item_count=result.item_count,
        found_name=result.found_name,
        share_type=result.share_type,
        used_flexible_search=result.used_flexible_search,
    )


@router.get("/nowplaying", response_model=ChatResponse)
async def nowplaying(request: Request, user_id: str = Query("anonymous")):
    """Devuelve lo que se está reproduciendo actualmente."""
    assistant = _assistant(request)
    uid = int(user_id) if user_id.isdigit() else hash(user_id)
    response = await assistant._agent_query("¿Qué estoy escuchando ahora?", uid)
    return ChatResponse(text=response.text, success=response.success)


@router.get("/library", response_model=ChatResponse)
async def library(
    request: Request,
    category: str = Query("tracks", description="tracks | albums | artists"),
    limit: int = Query(15, ge=1, le=50),
):
    """Lista elementos de la biblioteca musical."""
    assistant = _assistant(request)
    response = await assistant.get_library_items(category, limit)
    return ChatResponse(text=response.text, success=response.success)


@router.post("/feedback")
async def feedback(body: FeedbackRequest, request: Request):
    """Registra feedback (like/dislike) sobre una recomendación."""
    assistant = _assistant(request)
    uid = int(body.user_id) if body.user_id.isdigit() else hash(body.user_id)
    await assistant.process_feedback(uid, body.track_id, body.feedback_type)
    return {"ok": True}
