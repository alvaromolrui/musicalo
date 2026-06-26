"""
Endpoints de chat: POST /chat (síncrono) y WS /chat/stream (streaming).
"""
import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from api.auth import verify_api_key
from api.models import ChatRequest, ChatResponse, ActionItem
from core.music_assistant import MusicAssistant

router = APIRouter()


def _get_assistant(request) -> MusicAssistant:
    return request.app.state.assistant


@router.post("/", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(body: ChatRequest, request=None):
    """
    Envía un mensaje en lenguaje natural y recibe la respuesta completa.
    El campo user_id es el identificador de sesión (puede ser cualquier string único por usuario).
    """
    from fastapi import Request
    assistant: MusicAssistant = request.app.state.assistant
    response = await assistant.chat(int(body.user_id) if body.user_id.isdigit() else hash(body.user_id), body.message)
    return ChatResponse(
        text=response.text,
        actions=[ActionItem(id=a.id, label=a.label) for a in response.actions],
        success=response.success,
    )


@router.websocket("/stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket para chat con respuesta en streaming.

    Protocolo:
      Cliente → servidor: JSON { "user_id": "...", "message": "...", "api_key": "..." }
      Servidor → cliente: chunks de texto plano, terminando con el JSON { "done": true }
    """
    await websocket.accept()
    assistant: MusicAssistant = websocket.app.state.assistant

    import os
    expected_key = os.getenv("MUSICALO_API_KEY", "").strip()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "JSON inválido"}))
                continue

            # Autenticación por mensaje
            if expected_key and data.get("api_key") != expected_key:
                await websocket.send_text(json.dumps({"error": "API key inválida"}))
                await websocket.close(code=4001)
                return

            user_id_raw = data.get("user_id", "anonymous")
            user_id = int(user_id_raw) if str(user_id_raw).isdigit() else hash(user_id_raw)
            message = data.get("message", "")

            if not message:
                await websocket.send_text(json.dumps({"error": "message vacío"}))
                continue

            # Por ahora enviamos la respuesta completa al terminar.
            # Cuando MusicAgentService soporte streaming nativo, este endpoint
            # enviará chunks a medida que lleguen del modelo.
            response = await assistant.chat(user_id, message)
            actions = [{"id": a.id, "label": a.label} for a in response.actions]
            await websocket.send_text(response.text)
            await websocket.send_text(json.dumps({"done": True, "actions": actions, "success": response.success}))

    except WebSocketDisconnect:
        pass
