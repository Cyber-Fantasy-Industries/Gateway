import os,json
from flask import Blueprint, request, jsonify
from ag2.autogen import ConversableAgent, UserProxyAgent, Agent, GroupChat, GroupChatManager

conference_bp = Blueprint("conference", __name__)
lobby_manager = None
# Basisverzeichnis
HISTORY_DIR = "/app/history/conferences"
CONFIG_DIR = "/app/config"

os.makedirs(HISTORY_DIR, exist_ok=True)

# JSON-Lader
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_agent_config(agent_name):
    agent_path = os.path.join(CONFIG_DIR, f"{agent_name}.json")
    if not os.path.exists(agent_path):
        raise FileNotFoundError(f"Agent-Konfiguration nicht gefunden: {agent_path}")

    config = load_json(agent_path)
    # Falls du auch {{global}} für den Key ersetzen willst:
    for entry in config.get("config_list", []):
        if entry.get("api_key") == "{{global}}":
            entry["api_key"] = os.getenv("OPENAI_API_KEY")
    return config

# UserProxy-Agent laden
def build_user_proxy():
    user_path = os.path.join(CONFIG_DIR, "user.json")
    config = load_json(user_path)
    return UserProxyAgent(**config)

# Admin-Agent laden
def build_admin():
    admin_path = os.path.join(CONFIG_DIR, "admin.json")
    config = load_json(admin_path)
    return ConversableAgent(
        name=config.get("name", "Admin"),
        system_message=config.get("system_message", "Du bist ein erfahrener Assistent."),
        description=config.get("description", ""),
        human_input_mode=config.get("human_input_mode", "TERMINATE"),
        max_consecutive_auto_reply=config.get("max_consecutive_auto_reply", 3),
        default_auto_reply=config.get("default_auto_reply", "Bitte präzisieren Sie Ihre Anfrage."),
        is_termination_msg=config.get("is_termination_msg", None),
        llm_config=config.get("llm_config", {}),
        code_execution_config=config.get("code_execution_config", {})
    )

def build_agent(agent_name):
    config = load_agent_config(agent_name)

    if agent_name.lower() == "user":
        return UserProxyAgent(**config)

    return ConversableAgent(
        name=config.get("name", agent_name),
        system_message=config.get("system_message", "Assistent."),
        description=config.get("description", ""),
        human_input_mode=config.get("human_input_mode", "ALWAYS"),
        max_consecutive_auto_reply=config.get("max_consecutive_auto_reply", 3),
        default_auto_reply=config.get("default_auto_reply", "Bitte präzisieren Sie Ihre Anfrage."),
        is_termination_msg=config.get("is_termination_msg", None),
        llm_config=config.get("llm_config", {}),
        code_execution_config=config.get("code_execution_config", {})
    )


# Manager-Config laden
def build_manager_config():
    mgr_path = os.path.join(CONFIG_DIR, "manager.json")
    config = load_json(mgr_path)
    for entry in config.get("config_list", []):
        if entry.get("api_key") == "{{global}}":
            entry["api_key"] = os.getenv("OPENAI_API_KEY")
    return config

# Konferenz initialisieren
@conference_bp.route("/api/conference/start", methods=["POST"])
def start_conference():
    data = request.get_json(force=True)
    room = data.get("room")
    if not room:
        return jsonify({"success": False, "message": "Kein Raumname übergeben."}), 400

    user_proxy = build_user_proxy()
    admin_agent = build_admin()

    group = GroupChat(
        agents=[user_proxy, admin_agent],
        messages=[
            {"role": "system", "content": "Conference started"}
        ],
        max_round=10,
        speaker_selection_method="round_robin"
    )

    manager = GroupChatManager(
        groupchat=group,
        name="Manager",
        llm_config=build_manager_config()
    )

    history_path = os.path.join(HISTORY_DIR, f"{room}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({"messages": group.messages}, f, indent=2)

    return jsonify({"success": True, "message": f"Konferenz '{room}' gestartet."})


# Nachricht senden
def initialize_lobby():
    global lobby_manager

    if lobby_manager is not None:
        print("✅ LobbyManager bereits initialisiert.")
        return lobby_manager

    print("✅ Initialisiere LobbyManager...")

    lobby_data = load_json("/app/threads/main_lobby.json")
    agent_names = lobby_data.get("agents", [])

    agents: list[Agent] = [build_agent(name) for name in agent_names]

    group = GroupChat(
        agents=agents,
        messages=[{"role": "system", "content": "Lobby gestartet"}],
        max_round=5,
        speaker_selection_method="round_robin"
    )

    lobby_manager = GroupChatManager(
        groupchat=group,
        name="LobbyManager",
        llm_config=build_manager_config(),
        human_input_mode="NEVER",
        system_message="Dies ist der Lobby-Manager."
    )

    print("✅ LobbyManager wurde initialisiert.")
    print("Lobby-Agenten:", [a.name for a in agents])
    return lobby_manager

from web_dashboard.routes.ws_reload import broadcast_chat_message

@conference_bp.route("/api/conference/lobby/say", methods=["POST"])
def say_to_lobby():
    data = request.get_json(force=True)
    message = data.get("message")
    if not message or not message.strip():
        return jsonify({"success": False, "message": "Keine Nachricht übergeben."}), 400

    if lobby_manager is None:
        return jsonify({"success": False, "message": "LobbyManager nicht initialisiert."}), 500

    response = lobby_manager.run(
        message={"role": "user", "content": message},
        max_turns=1,
        clear_history=False
    )

    # Die History enthält jetzt User- und Admin-Antwort
    messages = lobby_manager.groupchat.messages
    for msg in messages:
        if msg.get("role") == "user" and msg.get("name", "").lower() != "user":
            msg["role"] = "assistant"

    # Letzte Admin-Antwort rausholen:
    assistant_msg = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "assistant"),
        "Keine Antwort"
    )

    # Verlauf speichern
    with open("/app/history/conferences/main_lobby.json", "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, indent=2)

    # Append-Log
    with open("/app/history/conferences/main_lobby.log", "a", encoding="utf-8") as logf:
        for msg in messages[-2:]:
            logf.write(f"{msg['role']}: {msg['content']}\n")

    # 🟢 NEU: Die letzten beiden Nachrichten per WebSocket broadcasten
    # Du kannst auch nur die letzte nehmen, hier sende ich beide:
    for msg in messages[-2:]:
        broadcast_chat_message(json.dumps(msg))

    return jsonify({
        "success": True,
        "reply": assistant_msg,
        "messages": messages
    })







@conference_bp.route("/api/conference/lobby", methods=["GET"])
def get_lobby():
    lobby_path = os.path.join("/app/threads", "main_lobby.json")
    if not os.path.exists(lobby_path):
        return jsonify({"success": False, "message": "Lobby nicht gefunden."}), 404
    with open(lobby_path, "r", encoding="utf-8") as f:
        lobby = json.load(f)
    return jsonify({"success": True, "lobby": lobby})


# Verlauf abrufen
@conference_bp.route("/api/conference/history", methods=["GET"])
def get_conference_history():
    room = request.args.get("room")
    if not room:
        return jsonify({"success": False, "message": "Room erforderlich."}), 400

    history_path = os.path.join(HISTORY_DIR, f"{room}.json")
    if not os.path.exists(history_path):
        return jsonify({"success": True, "history": []})

    # Prüfen, ob die Datei leer ist
    if os.path.getsize(history_path) == 0:
        return jsonify({"success": True, "history": []})

    with open(history_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify({"success": True, "history": data.get("messages", [])})


@conference_bp.route("/api/conference/list", methods=["GET"])
def list_conferences():
    files = [f[:-5] for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    return jsonify({"success": True, "rooms": files})
