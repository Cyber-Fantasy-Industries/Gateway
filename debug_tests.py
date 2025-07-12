import httpx

base = "http://localhost:8080"

def log_result(title, res: httpx.Response):
    print(f"\n\U0001F4E1 {title}")
    print("  \u21AA\ufe0f Status:", res.status_code)
    try:
        print("  📦 Antwort:", res.json())
    except Exception as e:
        print("  ⚠️ Fehler beim Parsen der Antwort:", str(e))
        print("  📄 Text:", res.text)

def test_create_agent():
    res = httpx.post(f"{base}/api/agents/create", json={
        "name": "debug-agent",
        "profile": "default"
    })
    log_result("create_agent", res)

def test_create_agent_invalid():
    res = httpx.post(f"{base}/api/agents/create", json={})
    log_result("create_agent_invalid (422 expected)", res)

def test_list_agents():
    res = httpx.get(f"{base}/api/agents/status")
    log_result("list_agents", res)

def test_start_conference():
    res = httpx.post(f"{base}/api/conference/start", json={
        "room": "debug-conf",
        "agents": ["debug-agent"]
    })
    log_result("start_conference", res)

def test_start_conference_missing_field():
    res = httpx.post(f"{base}/api/conference/start", json={})
    log_result("start_conference_missing_field (422 expected)", res)

def test_respond_agent():
    try:
        res = httpx.post(
            f"{base}/api/agents/respond/debug-agent",
            json={"message": "Was kannst du?"},
            timeout=10.0
        )
        log_result("respond_agent", res)
    except httpx.ReadTimeout:
        print("\u23f0 Timeout: Agent hat nicht rechtzeitig geantwortet.")
    except Exception as e:
        print("\u274c Fehler bei respond_agent:", e)

def test_respond_agent_missing_message():
    res = httpx.post(f"{base}/api/agents/respond/debug-agent", json={})
    log_result("respond_agent_missing_message (422 expected)", res)

def test_lobby_say():
    res = httpx.post(f"{base}/api/conference/lobby/say", json={
        "message": "Hallo Lobby!"
    })
    log_result("lobby_say", res)

def test_lobby_say_missing():
    res = httpx.post(f"{base}/api/conference/lobby/say", json={})
    log_result("lobby_say_missing (422 expected)", res)

def test_get_lobby():
    res = httpx.get(f"{base}/api/conference/lobby")
    log_result("get_lobby", res)

def test_get_conference_history():
    res = httpx.get(f"{base}/api/conference/history", params={"room": "debug-conf"})
    log_result("get_conference_history", res)

def test_get_conference_history_missing_param():
    res = httpx.get(f"{base}/api/conference/history")
    log_result("get_conference_history_missing_param (422 expected)", res)

def test_get_conference_list():
    res = httpx.get(f"{base}/api/conference/list")
    log_result("get_conference_list", res)

def test_get_logs():
    res = httpx.get(f"{base}/api/system/logs")
    print("\n\U0001F4E1 get_logs")
    print("  \u21AA\ufe0f Status:", res.status_code)
    print("  📄 Text:", res.text)

def test_delete_agent():
    res = httpx.delete(f"{base}/api/agents/delete/debug-agent")
    log_result("delete_agent", res)

def test_delete_agent_invalid():
    res = httpx.delete(f"{base}/api/agents/delete/UNKNOWN")
    log_result("delete_agent_invalid (should fail silently or 404)", res)

def test_status_check():
    res = httpx.get(f"{base}/status")
    log_result("status_check", res)

def test_get_agent_settings():
    res = httpx.get(f"{base}/api/agents/settings/debug-agent")
    log_result("get_agent_settings", res)

def test_get_agent_settings_invalid():
    res = httpx.get(f"{base}/api/agents/settings/UNKNOWN")
    log_result("get_agent_settings_invalid (404 expected)", res)

def test_system_wipe():
    res = httpx.post(f"{base}/api/system/wipe")
    log_result("system_wipe", res)

def test_system_rebuild():
    res = httpx.post(f"{base}/api/system/rebuild")
    log_result("system_rebuild", res)

def run_all():
    print("\U0001F680 Starte Debug-API-Tests:")
    test_create_agent()
    test_create_agent_invalid()
    test_list_agents()
    test_start_conference()
    test_start_conference_missing_field()
    test_respond_agent()
    test_respond_agent_missing_message()
    test_lobby_say()
    test_lobby_say_missing()
    test_get_lobby()
    test_get_conference_history()
    test_get_conference_history_missing_param()
    test_get_conference_list()
    test_get_logs()
    test_delete_agent()
    test_delete_agent_invalid()
    test_status_check()
    test_get_agent_settings()
    test_get_agent_settings_invalid()
    test_system_wipe()
    test_system_rebuild()

if __name__ == "__main__":
    run_all()
