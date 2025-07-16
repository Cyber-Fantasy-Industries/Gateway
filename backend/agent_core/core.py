import os
import json
from backend.ag2.autogen import ConversableAgent, UserProxyAgent, GroupChat, GroupChatManager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
LOBBY_HISTORY = BASE_DIR / "history" / "conferences" / "main_lobby.json"
LOBBY_INIT = CONFIG_DIR / "lobby_init.json"
LOBBY_HISTORY.parent.mkdir(parents=True, exist_ok=True)

# Singleton Manager
lobby_manager = None

def initialize_lobby():
    global lobby_manager

    # 1. Lade initiale Nachrichten aus lobby_init.json
    if LOBBY_INIT.exists():
        with open(LOBBY_INIT, encoding="utf-8") as f:
            lobby_init = json.load(f)
        messages = lobby_init.get("messages", [])
    else:
        messages = [{"role": "system", "content": "Lobby gestartet", "name": "system"}]

    # 2. Admin laden
    with open(CONFIG_DIR / "admin.json", encoding="utf-8") as f:
        admin_config = json.load(f)
    admin_agent = ConversableAgent(
        name=admin_config["name"],
        system_message=admin_config["system_message"],
        description=admin_config.get("description"),
        human_input_mode=admin_config.get("human_input_mode", "NEVER"),
        default_auto_reply=admin_config.get("default_auto_reply"),
        max_consecutive_auto_reply=admin_config.get("max_consecutive_auto_reply"),
        llm_config=admin_config["llm_config"],
        code_execution_config=admin_config.get("code_execution_config"),
    )

    # 3. User laden
    with open(CONFIG_DIR / "user.json", encoding="utf-8") as f:
        user_config = json.load(f)
    is_termination_msg = user_config.get("is_termination_msg")
    if isinstance(is_termination_msg, str):
        is_termination_msg = eval(is_termination_msg)
    user_agent = UserProxyAgent(
        name=user_config["name"],
        description=user_config.get("description"),
        is_termination_msg=is_termination_msg
    )
    print("ADMIN:", type(admin_agent))
    print("USER:", type(user_agent))
    # 4. GroupChat & Manager erzeugen
    groupchat = GroupChat(
        agents=[user_agent, admin_agent],
        messages=messages,  # <---- Hier landen die initialen Nachrichten!
        max_round=10,
        speaker_selection_method="auto"
    )
    lobby_manager = GroupChatManager(
        groupchat=groupchat,
        name="LobbyManager",
        llm_config=admin_config["llm_config"],
        human_input_mode="NEVER",
        system_message="Dies ist der zentrale Lobby-Manager."
    )

    return lobby_manager


# core.py
def get_lobby_manager():
    global lobby_manager
    if lobby_manager is None:
        lobby_manager = initialize_lobby()
    return lobby_manager


def sync_lobby_manager_to_json():
    global lobby_manager
    if lobby_manager is None:
        return
    messages = lobby_manager.groupchat.messages
    with open(LOBBY_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, indent=2)

def get_lobby():
    if LOBBY_HISTORY.exists():
        with open(LOBBY_HISTORY, encoding="utf-8") as f:
            return json.load(f)
    else:
        return {"messages": []}

def get_lobby_history():
    lobby = get_lobby()
    return lobby.get("messages", [])

def load_agent_profile():
    print()
def build_user_proxy():
    print()
def build_admin(): 
    print()
def build_manager_config():
    print()
