import os
import json
from backend.ag2.autogen import ConversableAgent, UserProxyAgent, Agent, GroupChat, GroupChatManager
from utils.logger import logger

HISTORY_DIR = os.path.join("history", "conferences")

AGENT_PROFILE_DIR = "config"
AGENTS_RUNTIME_DIR = "agents_config_list"
THREADS_DIR = "threads"
SYSTEM_PROFILES = {"user", "admin", "manager"}
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🧠 Agentenprofil laden (nur aus /config)
def load_agent_profile(profile_name: str):
    path = os.path.join(AGENT_PROFILE_DIR, f"{profile_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Agentenprofil '{profile_name}' nicht gefunden: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# 🧱 Blueprint mit Default-Profil
def default_agent_config(name: str):
    blueprint_path = os.path.join("agent_core", "agent_blueprint.json")
    default_path = os.path.join("config", "default.json")

    with open(blueprint_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as f:
            defaults = json.load(f)
        def merge(d1, d2):
            for k, v in d2.items():
                if isinstance(v, dict) and k in d1:
                    merge(d1[k], v)
                else:
                    d1[k] = v
        merge(template, defaults)

    template["name"] = name
    return template

# 🔧 Einzelne Konfigs direkt laden
def user_agent_config():
    return load_agent_profile("user")

def operator_agent_config():
    return load_agent_profile("admin")

def get_agent_list_path():
    return os.path.join("agent_core", "agents_list.json")

# 🧠 Agenteninstanz aus Profil erzeugen
def build_agent(agent_name: str) -> Agent:
    if agent_name == "user":
        return build_user_proxy()
    elif agent_name == "admin":
        return build_admin()

    # Erst eigene Agenten, dann Fallback auf readonly-Profile
    runtime_path = os.path.join(AGENTS_RUNTIME_DIR, f"{agent_name}.json")
    if os.path.exists(runtime_path):
        with open(runtime_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = load_agent_profile(agent_name)

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

def build_user_proxy():
    config = load_agent_profile("user")
    return UserProxyAgent(**config)

def build_admin():
    config = load_agent_profile("admin")
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

def build_manager_config():
    config = load_json(os.path.join(AGENT_PROFILE_DIR, "manager.json"))
    for entry in config.get("config_list", []):
        if entry.get("api_key") == "{{global}}":
            entry["api_key"] = os.getenv("OPENAI_API_KEY")
        # DEBUG: Zeige alle Keys!
        print("🔍 LLM-Konfigurationseintrag:", entry)
    return config




# 🔁 Lobby-Manager erzeugen
lobby_manager = None
from dotenv import load_dotenv
import os
def initialize_lobby():
    load_dotenv()
    print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
    print("OPENAI_PROJECT_ID:", os.getenv("OPENAI_PROJECT_ID"))
    print("OPENAI_ORG_ID:", os.getenv("OPENAI_ORG_ID"))
    """
    🧠 Initialisiert oder lädt die zentrale Main-Lobby mit Admin und UserProxy.
    """
    global lobby_manager
    if lobby_manager:
        return lobby_manager

    try:
        user_proxy = build_user_proxy()
        admin_agent = build_admin()

        history_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "history", "conferences", "main_lobby.json"))
        messages = [{"role": "system", "content": "Lobby gestartet"}]

        # ⏪ Falls Datei existiert: Verlauf einlesen
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                messages = old_data.get("messages", messages)

        # 🧑‍💼 GroupChat + Manager erzeugen
        group = GroupChat(
            agents=[user_proxy, admin_agent],
            messages=messages,
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
        
        # Test-Nachricht über den Manager (run_chat)
        try:
            # Übergebe ein dict-Array als Chatverlauf
            result = lobby_manager.run_chat(
            messages=[{"role": "user", "content": "Test"}]
        )
            logger.info(f"Testnachricht geschickt, Antwort: {result}")
        except Exception as ex:
            logger.warning(f"Konnte Testnachricht nicht schicken: {ex}")
        try:
            lobby_manager.run()
        except Exception as ex:
            logger.warning(f"Konnte run() nicht aufrufen: {ex}")
        try:
            result = lobby_manager.initiate_chat(
                recipient=admin_agent,
                message="Dies ist eine Testnachricht an den Admin.",
                clear_history=False
            )
            logger.info(f"Testnachricht geschickt, Antwort: {result}")
        except Exception as ex:
            logger.warning(f"Konnte Testnachricht nicht schicken: {ex}")
        # 💾 Aktuellen Zustand abspeichern
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump({"messages": group.messages}, f, indent=2)

        logger.info("✅ Lobby erfolgreich initialisiert.")
        return lobby_manager

    except Exception as e:
        logger.exception("❌ Fehler bei Lobby-Initialisierung")
        raise RuntimeError(f"Fehler beim Initialisieren der Lobby: {str(e)}")


# 📦 Hilfsfunktionen
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

