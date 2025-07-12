from fastapi import APIRouter
from backend.agent_core.core import initialize_lobby

router = APIRouter()

@router.get("/status")
def status():
    return {"status": "OK"}

@router.post("/rebuild")
def rebuild_system():
    """
    🔄 Logischer System-Rebuild: Lobby, Agenten, Speicher etc.
    """
    initialize_lobby()
    return {"success": True, "message": "System wurde neu initialisiert."}
