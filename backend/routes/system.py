# AG2 API-Handler und Lobby-Logik: Clean Refactoring

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from backend.agent_core.core import (
    get_lobby_manager, sync_lobby_manager_to_json,
    initialize_lobby, get_lobby, get_lobby_history
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["System"])

class MessageRequest(BaseModel):
    message: str

@router.post("/lobby/say")
def say_to_lobby(request: MessageRequest):
    try:
        manager = get_lobby_manager()
        user_msg = {
            "role": "user",    # Muss da bleiben!
            "name": "user",
            "content": request.message
        }

        user_agent = next(a for a in manager.groupchat.agents if a.name.lower() == "user")
        # Die History enthält beim Lobby-Bau bereits die System-Nachricht.
        # Wir hängen keine weitere System-Nachricht mehr an!
        manager.groupchat.append(user_msg, user_agent)
        print("🚩 Nach Append: Aktuelle Nachrichten:", manager.groupchat.messages)

        # AG2-Style: Events programmatisch verarbeiten (kein .process() im API-Kontext!)
        response = manager.run(n_round=1, user_input=False)
        print("--- Verlauf nach .run() ---")
        for msg in manager.groupchat.messages:
            print(msg)
        print("--- Agentenliste ---")
        for a in manager.groupchat.agents:
            print(a.name, type(a))
        # Fange alle Eingabe-Events ab
        for event in getattr(response, 'events', []):
            if getattr(event, "type", None) == "input_request":
                # Beende oder antworte automatisch, z.B. "exit" oder "yes"
                if hasattr(event.content, "respond"):
                    event.content.respond("exit")
                continue
            # Sonstige Events: Optional loggen/auswerten
        # Finde letzte Admin-Antwort
        messages = manager.groupchat.messages
        for m in reversed(messages):
            if m.get("name", "").lower() == "admin":
                print("Admin-Nachricht gefunden:", m)
                if m.get("role") != "assistant":
                    print("WARNUNG: Admin-Role ist nicht 'assistant' sondern:", m.get("role"))
                admin_reply = m["content"]
                break
        else:
            admin_reply = None

        sync_lobby_manager_to_json()
        print("🟢 Aktuelle Nachrichten:", manager.groupchat.messages)
        logger.info(f"🟢 Aktuelle Nachrichten: {manager.groupchat.messages}")
        return {
            "success": True,
            "reply": admin_reply
        }


    except Exception as e:
        import traceback
        print("❌ EXCEPTION:\n", traceback.format_exc())
        logger.exception("Fehler in /lobby/say")
        raise HTTPException(status_code=500, detail="Interner Serverfehler")

@router.get("/status")
def status():
    return {"status": "OK"}

# @router.post("/rebuild")
# def rebuild_system():
#     initialize_lobby()
#     return {"success": True, "message": "System wurde neu initialisiert."}

# @router.get("/lobby")
# def lobby_info():
#     return get_lobby()

# @router.get("/lobby/history")
# def lobby_history():
#     return {"messages": get_lobby_history()}
