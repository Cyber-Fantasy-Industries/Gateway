workforce_manager/

├── agent_core/                     # 🧠 Rollen- und Agentenlogik
│   ├── base_agent.py
│   ├── agent_blueprint.json
│   ├── user_proxy.py
│   └── role_profiles.json
├── chat_engine/                    # 💬 Interaktion & Kommunikation
│   ├── group_chat.py
│   ├── group_chat_manager.py
│   └── conference_room.py
├── threads/
    ├── main_lobby.json
    ├── {lobby_name}.json
├── evaluation/                     # ✅ Feedback, Konsens, Risiko
│   ├── consensus_checker.py
│   ├── risk_assessor.py
│   ├── uat_simulation.py
│   └── refinement_controller.py
├── execution/                      # ⚙️ Umsetzung, Testing
│   ├── code_executor.py
│   ├── dependency_manager.py
│   ├── preliminary_tester.py
│   ├── integration_tester.py
│   └── deployment_handler.py
├── tests/                      # ⚙️ Umsetzung, Testing
│   ├── test_autogen_connection.py
│   ├── test_main_lobby.py
├── task_engine/                    # 🧩 Subtask-Struktur & Phasenablauf
│   ├── task_parser.py
│   ├── phase_handler.py
│   ├── status_tracker.py
│   └── task_repository.json
├── history/
    ├── chats/
    ├── conferences/
        ├── __init__
└── web_dashboard/
    ├── routes/
    │   ├── agents_routes.py
    │   ├── conference_routes.py
    │   ├── index_routes.py
    │   ├── log_routes.py
    │   ├── settings_routes.py
    │   └── ws_reload.py
    ├── static/
    │   ├── css/
    │   │   └── style.css
    │   └── js/
    │       └── main.mjs
    │       └── agents.js
    │       └── conference.js
    │       └── chat.js
    │       └── logs.js
    │       └── modal.js
    │       └── tabs.js
    │       └── ws.js
    ├── templates/
    │   └── base.html
    └── __init__.py
│
├── utils/
│ ├── init.py
│ ├── docker_control.py # Alle Docker-Kommandos (Build, Start, Stop, Logs, etc.)
│ ├── logger.py # Logging-Setup und globale Log-Queue
│ └── env_loader.py # Hilfsfunktion zum Laden von .env-Dateien
│
├── backend/
│ ├── init.py
│ └── main.py # Flask-Server für die Anwendung im Container
│
├── app.pyw
├── wipe.py
├── rebuild.py
├── requirements.txt                 
├── docker_composer.yaml
├── .dockerignore
├── .env
└── README.md 