import asyncio
from backend.agent_core.cluster import build_cluster
async def run_cli_chat():
    cluster = await build_cluster()
    brain = cluster["brain"]
    hub_manager = cluster["hub_manager"]
    messages = []
    print("Starte interaktiven Multi-Turn-Chat (exit/quit zum Beenden):")
    while True:
        try:
            user_msg = input("User: ")
        except EOFError:
            print("Kein Input verfügbar (Container/Daemon-Modus).")
            break
        if user_msg.strip().lower() in ("exit", "quit"):
            print("Beende Chat.")
            break
        messages.append({"role": "user", "content": user_msg})

        # → MEMORY: Persistiere die User-Message und lade Kontext vor jedem Agenten-Turn!
        await brain.memory.persist_user_message(user_msg)
        context = await brain.memory.fetch_context()
        await brain.memory.debug_fetch_all_messages()
        # → Jetzt erst den Agenten-Response starten (ggf. async-Variante nehmen)
        # Wenn dein hub_manager.run async ist, await darauf:
        response = hub_manager.run(message=user_msg, messages=messages)
        output = response.process() if hasattr(response, "process") else response
        messages.append({"role": "assistant", "content": str(output)})
        print("System:", output)


if __name__ == "__main__":
    asyncio.run(run_cli_chat())


