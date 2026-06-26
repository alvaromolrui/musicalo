"""Pydantic models para los endpoints de la API REST."""
from pydantic import BaseModel, Field
from typing import Optional


# --- Request models ---

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Identificador de sesión del usuario")
    message: str = Field(..., description="Mensaje en lenguaje natural")


class RecommendRequest(BaseModel):
    user_id: str
    rec_type: str = Field("general", description="general | album | artist | track")
    genre_filter: Optional[str] = None
    similar_to: Optional[str] = None
    limit: int = Field(5, ge=1, le=20)
    custom_prompt: Optional[str] = None
    from_library_only: bool = False


class ShareRequest(BaseModel):
    search_term: str = Field(..., description="Nombre de álbum, artista o canción")


class FeedbackRequest(BaseModel):
    user_id: str
    track_id: str
    feedback_type: str = Field(..., description="like | dislike")


# --- Response models ---

class ActionItem(BaseModel):
    id: str
    label: str


class ChatResponse(BaseModel):
    text: str
    actions: list[ActionItem] = []
    success: bool = True


class RecommendationItem(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    reason: str
    confidence: float
    source: Optional[str] = None
    url: Optional[str] = None


class RecommendResponse(BaseModel):
    recommendations: list[RecommendationItem]
    text: str
    actions: list[ActionItem] = []
    success: bool = True


class ShareResponse(BaseModel):
    url: str
    id: str
    item_count: int
    found_name: str
    share_type: str
    used_flexible_search: bool = False


class StatsResponse(BaseModel):
    text: str
    success: bool = True


class HealthResponse(BaseModel):
    status: str
    health_score: int
    circuit_breakers: dict = {}
    recent_errors: dict = {}
