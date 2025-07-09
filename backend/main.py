# main.py
import sys, json
import os
import time
import traceback
from flask import Flask

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "web_dashboard", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "..", "web_dashboard", "templates")

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    static_url_path="/static",
    template_folder=TEMPLATES_DIR
)

app.debug = True

@app.route("/status")
def status():
    return "OK", 200

if __name__ == "__main__":

    try:
        print("✅ Initialisiere Anwendung...")

        # Alle problematischen Imports hier drinnen!
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

        from flask_cors import CORS
        from web_dashboard.routes.index_routes import index_bp
        from web_dashboard.routes.agents_routes import agents_bp
        from web_dashboard.routes.log_routes import log_bp
        from web_dashboard.routes.settings_routes import settings_bp
        from web_dashboard.routes.ws_reload import sock as ws_sock
        from web_dashboard.routes.conference_routes import conference_bp, initialize_lobby
        import threading

        CORS(app)
        HISTORY_DIR = "/app/history/conferences"

        # Routen registrieren
        
        #app.register_blueprint(agents_bp)
        app.register_blueprint(log_bp)
        app.register_blueprint(settings_bp)
        app.register_blueprint(conference_bp)
        app.register_blueprint(index_bp)
        app.register_blueprint(agents_bp)
        ws_sock.init_app(app)
        
        print("✅ Prüfe Lobby-History-Datei...")
        lobby_history_path = os.path.join(HISTORY_DIR, "main_lobby.json")
        if not os.path.exists(lobby_history_path):
            with open(lobby_history_path, "w", encoding="utf-8") as f:
                json.dump({"messages": []}, f, indent=2)
        print("✅ Lobby-History-Datei OK.")
        from web_dashboard.routes.ws_reload import start_watcher
        threading.Thread(target=start_watcher, daemon=True).start()
        initialize_lobby()
        
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
        

    except Exception as e:
        print("❌ Fehler beim Initialisieren:")
        traceback.print_exc()


