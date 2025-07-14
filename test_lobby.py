# test_lobby.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from agent_core.core import initialize_lobby

if __name__ == "__main__":
    print("🧪 Starte Lobby-Test...")
    try:
        manager = initialize_lobby()
        print("✅ Lobby erfolgreich initialisiert:", manager)
    except Exception as e:
        print("❌ Fehler bei der Lobby-Initialisierung:")
        print(e)
