**Gateway** ist eine modulare KI-Agentenplattform, die FastAPI, Autogen 2 und Unreal Engine 5 kombiniert. Ziel ist ein orchestriertes Agentensystem mit WebSocket- und REST-Schnittstellen zur Live-Interaktion mit realen oder simulierten Systemen (z. B. UE5).

Gateway/
├── .dockerignore
├── .env
├── app.pyw                 # (deprecated)
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── quick_setup_gateway.py
├── README.md
├── rebuild.py
├── requirements.txt
├── run_gateway.bat
├── wipe.py
├── .git/
├── .vs/
├── .vscode/
├── backend/
│   ├── main.py
│   ├── __init__.py
│   ├── ag2/
│   ├── agent_core/
│   │   ├── __init__.py
│   │   ├── agent_blueprint.json
│   │   ├── agent_factory/
│   │   ├── core.py
│   │   ├── core_agents.json
│   │   ├── file_tools.py
│   │   └── manager_factory.py
│   ├── agent_config_list/
│   ├── history/
│   │   ├── chats/
│   │   └── conferences/
│   ├── threads/
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
│   └── user.json
├── docs/
├── logs/
│   ├── watchdog
│   ├── server
│   ├── docker
│   └── gateway.log
├── utils/
│   ├── docker_control.py
│   └── logger.py
