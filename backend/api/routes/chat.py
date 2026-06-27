"""
Endpoints de chat: POST /chat (síncrono) y POST /chat/stream (SSE).
"""
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from api.auth import verify_api_key
from api.models import ChatRequest, ChatResponse, ActionItem
from core.music_assistant import MusicAssistant

router = APIRouter()


def _uid(raw: str) -> int:
    return int(raw) if raw.isdigit() else hash(raw)


@router.post("/", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(body: ChatRequest, request: Request):
    """
    Envía un mensaje en lenguaje natural y recibe la respuesta completa.
    El campo user_id es el identificador de sesión (puede ser cualquier string único por usuario).
    """
    assistant: MusicAssistant = request.app.state.assistant
    response = await assistant.chat(_uid(body.user_id), body.message)
    return ChatResponse(
        text=response.text,
        actions=[ActionItem(id=a.id, label=a.label) for a in response.actions],
        success=response.success,
    )


@router.post("/stream", dependencies=[Depends(verify_api_key)])
async def chat_stream(body: ChatRequest, request: Request):
    """
    Server-Sent Events para chat con respuesta en streaming visual.

    Emite dos eventos SSE:
      data: {"type": "text",  "content": "<respuesta completa>"}
      data: {"type": "done",  "actions": [...], "success": true/false}

    En el futuro, cuando MusicAgentService soporte streaming nativo de Gemini,
    este endpoint emitirá múltiples eventos "token" en lugar de un único "text".
    """
    assistant: MusicAssistant = request.app.state.assistant

    async def generate():
        try:
            response = await assistant.chat(_uid(body.user_id), body.message)
            actions = [{"id": a.id, "label": a.label} for a in response.actions]
            yield f"data: {json.dumps({'type': 'text', 'content': response.text})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'actions': actions, 'success': response.success})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
