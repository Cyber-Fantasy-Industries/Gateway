from flask import Blueprint, Response
import os

log_bp = Blueprint("logs", __name__)

@log_bp.route("/api/logs", methods=["GET"])
def get_logs():
    log_path = os.path.join("history", "logs", "server.log")
    if not os.path.exists(log_path):
        return Response("📭 Noch keine Logs vorhanden.", mimetype="text/plain")

    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
        return Response(content, mimetype="text/plain")
