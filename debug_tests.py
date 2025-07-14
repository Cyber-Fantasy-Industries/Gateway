import httpx

base = "http://localhost:8080"

def log_result(title, res: httpx.Response, expect_json=True):
    print(f"\n📡 {title}")
    print("  ↪️ Status:", res.status_code)
    try:
        if expect_json:
            print("  📦 Antwort:", res.json())
        else:
            print("  📄 Text:", res.text.strip())
    except Exception as e:
        print("  ⚠️ Fehler beim Parsen der Antwort:", str(e))
        print("  📄 Rohdaten:", res.text.strip())

client = httpx.Client(timeout=60.0)

# AGENTEN
# def test_create_agent():
#     res = client.post(f"{base}/api/agents/create", json={
#         "name": "debug-agent",
#         "profile": "default"
#     })
#     log_result("create_agent", res)

# def test_list_agents():
#     res = client.get(f"{base}/api/agents/status")
#     log_result("list_agents", res)

# def test_respond_agent():
#     res = client.post(f"{base}/api/agents/respond/debug-agent", json={
#         "message": "Was kannst du?"
#     })
#     log_result("respond_agent", res)

# def test_get_agent_settings():
#     res = client.get(f"{base}/api/agents/settings/debug-agent")
#     log_result("get_agent_settings", res)

# def test_delete_agent():
#     res = client.delete(f"{base}/api/agents/delete/debug-agent")
#     log_result("delete_agent", res)

# KONFERENZEN
# def test_start_conference():
#     res = client.post(f"{base}/api/conference/start", json={
#         "room": "debug-conf"
#     })
#     log_result("start_conference", res)

def test_lobby_say():
    res = client.post(f"{base}/api/system/lobby/say", json={
        "message": "Hallo Lobby!"
    })
    log_result("lobby_say", res)

def test_get_lobby():
    try:
        res = client.get(f"{base}/api/system/lobby")
        log_result("get_lobby", res)
    except Exception as e:
        print(f"❌ Fehler bei get_lobby: {e}")

def test_get_lobby_history():
    res = client.get(f"{base}/api/system/lobby/history")
    log_result("get_lobby_history", res)

# def test_get_conference_history():
#     res = client.get(f"{base}/api/conference/history", params={"room": "debug-conf"})
#     log_result("get_conference_history", res)

# def test_get_conference_list():
#     res = client.get(f"{base}/api/conference/list")
#     log_result("get_conference_list", res)

# SYSTEM
# def test_status_check():
#     res = client.get(f"{base}/status")
#     log_result("status_check", res)

def test_get_logs():
    res = client.get(f"{base}/api/system/logs")
    log_result("get_logs", res, expect_json=False)

# ✅ Optionale System-Reinitialisierung
def test_rebuild_system():
    res = client.post(f"{base}/api/system/rebuild")
    log_result("rebuild_system", res)

# ❌ Docker-APIs ausgeblendet, da nicht erreichbar:
def test_docker_build():
    res = client.post(f"{base}/build")
    log_result("docker_build", res)

def test_docker_restart():
    res = client.post(f"{base}/restart")
    log_result("docker_restart", res)

def test_docker_stop():
    res = client.post(f"{base}/stop")
    log_result("docker_stop", res)

def test_docker_cleanup():
    res = client.delete(f"{base}/cleanup")
    log_result("docker_cleanup", res)


def run_all():
    print("🚀 Starte vollständige Debug-API-Tests:")
    # test_create_agent()
    # test_list_agents()
    # test_respond_agent()
    # test_get_agent_settings()
    # test_start_conference()
    test_lobby_say()
    test_get_lobby()
    # test_get_conference_history()
    # test_get_conference_list()
    test_get_logs()
    # test_status_check()
    # test_delete_agent()
    test_rebuild_system()
    test_docker_build()
    test_docker_restart()
    test_docker_stop()
    test_docker_cleanup()

if __name__ == "__main__":
    run_all()
