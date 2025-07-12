# backend/routes/conference.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import os, json
from backend.agent_core.core import build_agent, build_user_proxy, build_admin, build_manager_config, initialize_lobby
from backend.ag2.autogen import GroupChat, GroupChatManager
from loguru import logger

router = APIRouter(prefix="/api/conference", tags=["Conference"])

HISTORY_DIR = "/app/history/conferences"
os.makedirs(HISTORY_DIR, exist_ok=True)

# 📋 Request Models
class ConferenceStartRequest(BaseModel):
    room: str

class MessageRequest(BaseModel):
    message: str

# 📋 Response Models
class BasicResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class ConferenceHistory(BaseModel):
    success: bool
    history: List[dict]

class ConferenceList(BaseModel):
    success: bool
    rooms: List[str]

# 🚀 Konferenz starten
@router.post("/start", response_model=BasicResponse)
async def start_conference(request: ConferenceStartRequest):
    try:
        user_proxy = build_user_proxy()
        admin_agent = build_admin()

        group = GroupChat(
            agents=[user_proxy, admin_agent],
            messages=[{"role": "system", "content": "Conference started"}],
            max_round=10,
            speaker_selection_method="round_robin"
        )

        manager = GroupChatManager(
            groupchat=group,
            name="Manager",
            llm_config=build_manager_config()
        )

        history_path = os.path.join(HISTORY_DIR, f"{request.room}.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump({"messages": group.messages}, f, indent=2)

        logger.info(f"📢 Konferenz '{request.room}' erfolgreich gestartet.")
        return {"success": True, "message": f"Konferenz '{request.room}' gestartet."}
    except Exception as e:
        logger.exception("❌ Fehler beim Starten der Konferenz")
        raise HTTPException(status_code=500, detail=str(e))

# 💬 Nachricht in Lobby senden
@router.post("/lobby/say", response_model=BasicResponse)
async def say_to_lobby(request: MessageRequest):
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


# 📜 Lobby-Inhalt abrufen
@router.get("/lobby", response_model=dict)
async def get_lobby():
    try:
        lobby_path = "/app/threads/main_lobby.json"
        if not os.path.exists(lobby_path):
            raise HTTPException(status_code=404, detail="Lobby nicht gefunden.")
        with open(lobby_path, "r", encoding="utf-8") as f:
            lobby = json.load(f)
        return {"success": True, "lobby": lobby}
    except Exception as e:
        logger.exception("❌ Fehler beim Laden der Lobby")
        raise HTTPException(status_code=500, detail=str(e))


# 📜 Verlauf abrufen
@router.get("/history", response_model=dict)
async def get_conference_history():
    try:
        history_path = "/app/history/conferences/main_lobby.json"
        if not os.path.exists(history_path):
            logger.warning("📁 Kein Verlauf für Lobby gefunden.")
            raise HTTPException(status_code=404, detail="Kein Konferenzverlauf vorhanden.")

        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)

        logger.info("📜 Konferenzverlauf erfolgreich geladen.")
        return {"success": True, "history": history}
    except Exception as e:
        logger.exception("❌ Fehler beim Laden des Konferenzverlaufs")
        raise HTTPException(status_code=500, detail=str(e))


# 📜 Verfügbare Konferenzen
@router.get("/list", response_model=dict)
async def list_conferences():
    try:
        if not os.path.exists(HISTORY_DIR):
            logger.warning("📂 Verzeichnis für Konferenzverläufe nicht gefunden.")
            raise HTTPException(status_code=404, detail="Kein Konferenzverzeichnis vorhanden.")

        files = [
            f.replace(".json", "") for f in os.listdir(HISTORY_DIR)
            if f.endswith(".json")
        ]

        logger.info(f"📋 Verfügbare Konferenzen: {files}")
        return {"success": True, "conferences": files}
    except Exception as e:
        logger.exception("❌ Fehler beim Auflisten der Konferenzen")
        raise HTTPException(status_code=500, detail=str(e))

