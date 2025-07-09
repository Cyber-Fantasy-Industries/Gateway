import os
import json
import logging
from flask import Blueprint, jsonify, request
from config.agent_config_templates import load_agent_profile
# import openai
# from openai import OpenAI

settings_bp = Blueprint("settings", __name__)

# 🔹 Neue Speicherlogik für einzelne Agenten
AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agents_config_list"))

# 📋 Alle Agenten auflisten
@settings_bp.route("/api/agents/status")
def get_agents_status():
    result = []
    if not os.path.exists(AGENTS_DIR):
        os.makedirs(AGENTS_DIR)
    for filename in os.listdir(AGENTS_DIR):
        if filename.endswith(".json"):
            path = os.path.join(AGENTS_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                result.append({
                    "name": config.get("name", filename.replace(".json", "")),
                    "status": config.get("status", "idle")
                })
    return jsonify(result)

# # ➕ Neuen Agenten anlegen
# @settings_bp.route("/api/agents/create", methods=["POST"])
# def create_agent():
#     try:
#         data = request.get_json()
#         name = data.get("name")
#         profile = data.get("profile", "default")
#         if not name:
#             raise ValueError("Kein Name übergeben")

#         agent_config = load_agent_profile(profile)
#         agent_config["name"] = name

#         if not os.path.exists(AGENTS_DIR):
#             os.makedirs(AGENTS_DIR)

#         path = os.path.join(AGENTS_DIR, f"{name}.json")
#         with open(path, "w", encoding="utf-8") as f:
#             json.dump(agent_config, f, indent=2)

#         gui_log_queue.put(f"📥 Agent {name} erstellt")
#         return jsonify({"success": True, "message": f"Agent {name} gespeichert."})
#     except Exception as e:
#         gui_log_queue.put(f"❌ Fehler beim Erstellen des Agenten: {str(e)}")
#         logging.exception("Fehler beim Erstellen des Agenten")
#         return jsonify({"success": False, "error": str(e)}), 500

# ❌ Agent löschen
@settings_bp.route("/api/agents/delete/<name>", methods=["DELETE"])
def delete_agent(name):
    path = os.path.join(AGENTS_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
    return jsonify({ "success": True })

# # 💬 Agent antwortet
# @settings_bp.route("/api/agents/respond/<name>", methods=["POST"])
# def respond_agent(name):
#     try:
#         data = request.get_json()
#         message = data.get("message")
#         if not message:
#             return jsonify({ "success": False, "message": "Keine Nachricht erhalten" }), 400

#         path = os.path.join(AGENTS_DIR, f"{name}.json")
#         if not os.path.exists(path):
#             return jsonify({ "success": False, "message": "Agent nicht gefunden" }), 404

#         with open(path, "r", encoding="utf-8") as f:
#             agent = json.load(f)

#         llm = agent.get("llm_config", {})
#         api_key = llm.get("config_list", [{}])[0].get("api_key", "").strip()
#         if api_key == "{{global}}" or not api_key:
#             api_key = os.getenv("OPENAI_API_KEY")
#         if not api_key:
#             return jsonify({ "success": False, "message": "Kein gültiger API-Key gesetzt." }), 403

#         openai.api_key = api_key
#         model = llm.get("model", "gpt-3.5-turbo")
#         temperature = llm.get("temperature", 0.7)
#         max_tokens = llm.get("max_tokens", 2048)
#         system_msg = agent.get("system_message", "You are a helpful assistant.")
#         client = OpenAI(api_key=api_key)
#         response = client.chat.completions.create(
#             model=model,
#             messages=[
#                 { "role": "system", "content": system_msg },
#                 { "role": "user", "content": message }
#             ],
#             temperature=temperature,
#             max_tokens=max_tokens
#         )
#         reply = response.choices[0].message.content
#         return jsonify({ "success": True, "reply": reply })
#     except Exception as e:
#         logging.exception("Fehler bei Agentenantwort")
#         return jsonify({ "success": False, "message": str(e)}), 500

# ⚙️ Agenten-Settings vollständig abrufen
@settings_bp.route("/api/agents/settings/<name>", methods=["GET"])
def get_agent_settings(name):
    path = os.path.join(AGENTS_DIR, f"{name}.json")
    if not os.path.exists(path):
        return jsonify({}), 404

    with open(path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))
