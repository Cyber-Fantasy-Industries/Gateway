from fastapi import APIRouter
from utils import docker_control

router = APIRouter()

@router.post("/start")
def start_container():
    """
    ▶️ Container starten
    """
    docker_control.run_cmd_live("docker-compose up -d", print)
    return {"success": True, "message": "Container gestartet."}

@router.post("/stop")
def stop_container():
    """
    ⏹ Container stoppen
    """
    docker_control.run_cmd_live("docker-compose stop", print)
    return {"success": True, "message": "Container gestoppt."}

@router.post("/restart")
def restart_container():
    """
    🔁 Container neustarten
    """
    docker_control.run_cmd_live("docker-compose restart", print)
    return {"success": True, "message": "Container neugestartet."}

@router.post("/build")
def build_image():
    """
    🔨 Neues Image bauen
    """
    docker_control.run_cmd_live("docker-compose build", print)
    return {"success": True, "message": "Image gebaut."}

@router.post("/rebuild")
def rebuild_image():
    """
    ♻️ Image neu bauen (mit vollständigem Cleanup)
    """
    docker_control.run_cmd_live("docker-compose down --rmi all --remove-orphans", print)
    docker_control.run_cmd_live("docker-compose build", print)
    docker_control.run_cmd_live("docker-compose up -d", print)
    return {"success": True, "message": "Image neu gebaut und Container gestartet."}

@router.delete("/cleanup")
def cleanup():
    """
    🧹 Entferne Container & Image
    """
    docker_control.run_cmd_live("docker-compose down --rmi all --volumes --remove-orphans", print)
    return {"success": True, "message": "Alles entfernt."}
