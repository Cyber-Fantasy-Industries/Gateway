**Gateway** ist eine modulare KI-Agentenplattform, die FastAPI, Autogen 2 und Unreal Engine 5 kombiniert. Ziel ist ein orchestriertes Agentensystem mit WebSocket- und REST-Schnittstellen zur Live-Interaktion mit realen oder simulierten Systemen (z. B. UE5).

Gateway/
├── .dockerignore
├── .env
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── README.md
├── requirements.txt
├── run.py
├── .git/
├── .vscode/
├── backend/
│   ├── main.py
│   ├── __init__.py
│   ├── ag2/
│   ├── agent_core/
│   │   ├── __init__.py
│   │   ├── agent_blueprint.json
│   │   ├── agent_factory.py (not in use yet)
│   │   ├── core.py
│   │   ├── core_agents.json
│   │   ├── file_tools.py (not in use yet)
│   │   └── manager_factory.py (not in use yet)
│   ├── agent_config_list/
│   ├── history/
│       ├── __init__.py
│   │   ├── chats/
│   │   └── conferences/
│           ├── __init__.py
│           ├── main_lobby.py
│   ├── threads/
│       ├── __init__.py
│   │   └── main_lobby.json
│   |   └── {project_name}.json
│   └── routes/
│       ├── __init__.py
│       ├── agents.py
│       ├── conferences.py
│       ├── router_devtools.py
│       ├── settings.py
│       ├── system.py
│       └── websocket.py
├── config/
│   ├── admin.json
│   ├── default.json
│   ├── llm_config.json
│   ├── manager.json
│   ├── lobby_init.json
│   └── user.json
├── docs/
├── logs/
│   ├── watchdog
│   ├── server
├── utils/
│   └── logger.py
