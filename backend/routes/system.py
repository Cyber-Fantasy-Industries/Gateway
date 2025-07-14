# system.py
from fastapi import APIRouter, HTTPException, Body
from backend.agent_core.core import initialize_lobby
from pydantic import BaseModel
import os, json
from loguru import logger
from fastapi.responses import JSONResponse
router = APIRouter(prefix="/api/system", tags=["System"])

class MessageRequest(BaseModel):
    message: str

@router.get("/status")
def status():
    return {"status": "OK"}

@router.post("/rebuild")
def rebuild_system():
    initialize_lobby()
    return {"success": True, "message": "System wurde neu initialisiert."}

@router.post("/lobby/say")
def say_to_lobby(request: MessageRequest):
    try:
        lobby_manager = initialize_lobby()
        response = lobby_manager.run(
            message={"role": "user", "content": request.message},
            max_turns=1,
            clear_history=False
        )
        messages = lobby_manager.groupchat.messages
        assistant_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "assistant"),
            "Keine Antwort"
        )
        with open("/app/history/conferences/main_lobby.json", "w", encoding="utf-8") as f:
            json.dump({"messages": messages}, f, indent=2)
        logger.info(f"💬 Lobby-Antwort: {assistant_msg[:100]}")
        return {"success": True, "message": assistant_msg}
    except Exception as e:
        logger.exception("❌ Fehler beim Lobby-Dialog")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lobby")
def get_lobby():
    try:
        lobby = initialize_lobby()
        messages = lobby.chat_messages if hasattr(lobby, "chat_messages") else []
        return {
            "room": "main_lobby",
            "status": "open",
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Lobby: {str(e)}")

@router.get("/lobby/history")
def get_lobby_history():
    try:
        history_path = "/app/history/conferences/main_lobby.json"
        if not os.path.exists(history_path):
            raise HTTPException(status_code=404, detail="Kein Lobby-Verlauf vorhanden.")
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
