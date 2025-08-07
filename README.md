**Gateway** ist eine modulare KI-Agentenplattform, die FastAPI, Autogen 2 und Unreal Engine 5 kombiniert. Ziel ist ein orchestriertes Agentensystem mit WebSocket- und REST-Schnittstellen zur Live-Interaktion mit realen oder simulierten Systemen (z. B. UE5).

Gateway/
├── README.md
├── LICENSE
├── CHANGELOG
├── .dockerignore
├── .gitignore
├── .env
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py # runs docker, builds image, starts container, opens cmd, starts app
├── app.py
├── pyproject.toml
├── .git/
├── .venv/
├── .vscode/
├── src/
├── backend/
│   ├── main.py
│   ├── globals.py│
│   ├── __init__.py
│   ├── ag2/
│   ├── agent_core/
│   │   ├── __init__.py
│   │   ├── cluster.py 
│   │   ├── # core.py
│   │   ├── # agent_blueprint.json
│   │   ├── # agent_factory.py 
│   │   ├── # core.py
│   │   ├── # core_agents.json
│   │   ├── # file_tools.py 
│   │   └── # manager_factory.py 
│   ├── # agent_config_list/
│   ├── history/
│       ├── __init__.py
│   │   ├── chats/
│   │   └── conferences/
│           ├── __init__.py
│           ├── # main_lobby.py
│   ├── threads/
│       ├── __init__.py
│   │   └── # main_lobby.json
│   |   └── # {project_name}.json
│   └── routes/
│       ├── __init__.py
│       ├── # agents.py
│       ├── # conferences.py
│       ├── # router_devtools.py
│       ├── # settings.py
│       ├── # system.py
│       └── # websocket.py
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
