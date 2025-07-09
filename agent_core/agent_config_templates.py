import os
import json
#from autogen import config_list_from_json

AGENT_PROFILE_DIR = "config" 



def load_agent_profile(profile_name: str):
    """
    Lädt ein Agentenprofil aus einer JSON-Datei.
    Unterstützt Platzhalter '"{{load_from_file}}"' für LLM-Konfigurationsimport.
    """
    path = os.path.join(AGENT_PROFILE_DIR, f"{profile_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Agentenprofil '{profile_name}' nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # # Dynamisches Nachladen der API-Keys
    # if (
    #     "llm_config" in config
    #     and config["llm_config"].get("config_list") == "{{load_from_file}}"
    # ):
    #     config["llm_config"]["config_list"] = config_list_from_json("config/llm_config.json")

    return config


def default_agent_config(name: str):
    import os, json

    base = os.path.join("config", "default.json")
    blueprint = os.path.join("agent_core", "agent_blueprint.json")

    with open(blueprint, "r", encoding="utf-8") as f:
        template = json.load(f)

    if os.path.exists(base):
        with open(base, "r", encoding="utf-8") as f:
            defaults = json.load(f)
        # Rekursives Merge
        def merge(d1, d2):
            for k, v in d2.items():
                if isinstance(v, dict) and k in d1:
                    merge(d1[k], v)
                else:
                    d1[k] = v
        merge(template, defaults)

    template["name"] = name
    return template


def user_agent_config():
    return load_agent_profile("user")


def operator_agent_config():
    return load_agent_profile("admin")


def get_agent_list_path():
    return os.path.join("agent_core", "agents_list.json")
