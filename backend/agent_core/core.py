import os
import json
from backend.ag2.autogen import ConversableAgent, UserProxyAgent, Agent, GroupChat, GroupChatManager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # = /app/backend
HISTORY_DIR = BASE_DIR / "history" / "conferences"
LOBBY_FILE = HISTORY_DIR / "main_lobby.json"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

AGENT_PROFILE_DIR = "config"
AGENTS_RUNTIME_DIR = "agents_config_list"
THREADS_DIR = "threads"
SYSTEM_PROFILES = {"user", "admin", "manager"}

# Klare, neutrale Systemnachricht im Default-Lobby-Setup:
DEFAULT_LOBBY = {
    "room": "main_lobby",
    "agents": ["user", "Admin"],
    "status": "open",
    "messages": [
        {"role": "system", "content": "Lobby gestartet", "name": "system"}
    ],
    "resources": []
}

def initialize_lobby():
    print("initialize_lobby", flush=True)
    return build_lobby_manager()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_agent_list_path():
    return os.path.join("agent_core", "agents_list.json")

def load_lobby_json():
    if not os.path.exists(LOBBY_FILE):
        default_lobby = load_default_lobby()
        save_lobby_json(default_lobby)
        return default_lobby.copy()
    with open(LOBBY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_default_lobby():
    path = os.path.join("config", "lobby_init.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_lobby_json(lobby):
    print("💾 Schreibe in Datei:", LOBBY_FILE, flush=True)
    print("💾 Inhalt:", lobby, flush=True)
    with open(LOBBY_FILE, "w", encoding="utf-8") as f:
        json.dump(lobby, f, indent=2)

def sync_lobby_manager_to_json():
    global lobby_manager
    print("📝 Syncing lobby to JSON...", flush=True)
    if not lobby_manager:
        print("❌ lobby_manager ist None – nichts zu speichern!", flush=True)
    else:
        print("📋 Aktuelle Nachrichten im Manager:", lobby_manager.groupchat.messages, flush=True)
    if not lobby_manager:
        return
    lobby = load_lobby_json()
    lobby["messages"] = lobby_manager.groupchat.messages
    save_lobby_json(lobby)

def get_lobby():
    print("get_lobby", flush=True)
    return load_lobby_json()

def get_lobby_history():
    print("get_lobby_history", flush=True)
    lobby = load_lobby_json()
    return lobby.get("messages", [])

# Manager-Bau ist jetzt strikt modular:
def build_manager_config():
    print("build_manager_config", flush=True)
    config = load_json(os.path.join(AGENT_PROFILE_DIR, "manager.json"))
    for entry in config.get("config_list", []):
        if entry.get("api_key") == "{{global}}":
            entry["api_key"] = os.getenv("OPENAI_API_KEY")
    return config

lobby_manager = None
def build_lobby_manager():
    print("🔎 build_lobby_manager() aufgerufen", flush=True)
    global lobby_manager
    if lobby_manager:
        return lobby_manager
    lobby = load_lobby_json()
    user_proxy = build_user_proxy()
    admin_agent = build_admin()
    group = GroupChat(
        agents=[user_proxy, admin_agent],
        messages=lobby.get("messages", []),
        max_round=10,
        speaker_selection_method="round_robin"
    )
    lobby_manager = GroupChatManager(
        groupchat=group,
        name="LobbyManager",
        llm_config=build_manager_config(),
        human_input_mode="NEVER",
        system_message="Dies ist der zentrale Lobby-Manager."
    )
    print("✅ LobbyManager initialisiert:", lobby_manager, flush=True)
    return lobby_manager

def get_lobby_manager():
    print("get_lobby_manager", flush=True)
    global lobby_manager
    if not lobby_manager:
        raise RuntimeError("Lobby-Manager wurde noch nicht initialisiert!")
    return lobby_manager

def load_agent_profile(profile_name: str):
    path = os.path.join(AGENT_PROFILE_DIR, f"{profile_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Agentenprofil '{profile_name}' nicht gefunden: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_user_proxy():
    print("building user", flush=True)
    config = load_agent_profile("user")
    # eval für Stringfunktion
    if isinstance(config.get("is_termination_msg"), str):
        config["is_termination_msg"] = eval(config["is_termination_msg"])
    return UserProxyAgent(**config)

def build_admin():
    print("building admin", flush=True)
    config = load_agent_profile("admin")
    # system_message erweitern mit Kontext aus der Lobby
    lobby_context = load_lobby_json()
    context_info = (
        f"\n[Kontextinformationen]\n"
        f"Raum: {lobby_context.get('room')}\n"
        f"Status: {lobby_context.get('status')}\n"
        f"Aktive Agenten: {', '.join(lobby_context.get('agents', []))}\n"
        f"Ressourcen: {lobby_context.get('resources')}\n"
    )
    base_msg = config.get("system_message", "")
    config["system_message"] = f"{base_msg.strip()}{context_info}"
    llm_config = config.get("llm_config", {})
    for entry in llm_config.get("config_list", []):
        if entry.get("api_key") == "{{global}}":
            entry["api_key"] = os.getenv("OPENAI_API_KEY")
    config["llm_config"] = llm_config
    print("🔬 ADMIN-LLM-CONFIG:", config["llm_config"])
    print("🔬 ADMIN-API-KEY:", config["llm_config"]["config_list"][0].get("api_key"))
    return ConversableAgent(**config)

def default_agent_config(name: str):
    print("default_agent_config", flush=True)
    blueprint_path = os.path.join("agent_core", "agent_blueprint.json")
    default_path = os.path.join("config", "default.json")
    template = load_json(blueprint_path)
    if os.path.exists(default_path):
        defaults = load_json(default_path)
        def merge(d1, d2):
            for k, v in d2.items():
                if isinstance(v, dict) and k in d1:
                    merge(d1[k], v)
                else:
                    d1[k] = v
        merge(template, defaults)
    template["name"] = name
    return template

def build_agent(agent_name: str) -> Agent:
    path = os.path.join(AGENTS_RUNTIME_DIR, f"{agent_name}.json")
    if os.path.exists(path):
        config = load_json(path)
    else:
        config = load_agent_profile(agent_name)
    llm_config = config.get("llm_config", {})
    for entry in llm_config.get("config_list", []):
        if entry.get("api_key") == "{{global}}":
            entry["api_key"] = os.getenv("OPENAI_API_KEY")
    config["llm_config"] = llm_config
    return ConversableAgent(**config)