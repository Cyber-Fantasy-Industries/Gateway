from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Literal, cast, Dict
from loguru import logger
from zep_cloud.client import AsyncZep
from zep_cloud.core.api_error import ApiError
from backend.memory.memory_zep_thread import ZepThreadMemory
from backend.captain_hub import CaptainHub, HubPolicy
from backend.orchestration.zep_adapter import ZepMemoryAdapter, PersistTarget
from backend.memory.memory import ZepMemory


@dataclass
class RuntimeState:
    zep_client: Any
    user_id: str
    thread_id: Optional[str]
    lobby: Any              # Hub-Chat-Facade
    memory: Optional[Any]   # volle ZepMemory-Fassade (REST /api/memory/*)
    mem_thread: Optional[Any]  # ZepThreadMemory (für scope:"thread")
    hub: Optional[Any]
    orch_nested: bool
    persist_cfg: dict


_RUNTIME: Optional[RuntimeState] = None


async def _ensure_user(client: AsyncZep, user_id: str) -> None:
    try:
        await client.user.get(user_id)
        logger.info("✅ User {} bestätigt", user_id)
    except ApiError as e:
        if getattr(e, "status_code", None) == 404:
            await client.user.add(user_id=user_id)
            logger.info("➕ User {} neu angelegt", user_id)
        else:
            raise


async def _ensure_thread(client: AsyncZep, desired_id: str, user_id: str) -> str:
    t = None
    try:
        t = await client.thread.create(thread_id=desired_id, user_id=user_id)
        logger.info("🧵 Thread {} neu erstellt", desired_id)
    except ApiError as e:
        if getattr(e, "status_code", None) in (400, 409):
            logger.debug("🔄 Thread {} existiert bereits – hole bestehende Daten", desired_id)
            try:
                t = await client.thread.get(thread_id=desired_id)
            except Exception as ge:
                logger.warning("⚠️ Bestehender Thread {} konnte nicht geladen werden: {}", desired_id, ge)
                t = None
        else:
            raise
    canonical_tid = (
        getattr(t, "thread_id", None)
        or getattr(t, "uuid", None)
        or getattr(t, "id", None)
        or desired_id
    )
    if t is None:
        logger.warning("⚠️ Fallback: benutze gewünschte Thread-ID {} als kanonische ID", canonical_tid)
    else:
        logger.info("🔑 Kanonische Thread-ID: {}", canonical_tid)
    return canonical_tid


async def ensure_runtime() -> RuntimeState:
    """Initialisiert ZEP-Client, stellt User/Thread sicher und baut Hub + Chat-Facade (idempotent)."""
    global _RUNTIME
    if _RUNTIME is not None:
        logger.debug("ensure_runtime: Reuse bestehender Runtime (thread_id={!r})", _RUNTIME.thread_id)
        return _RUNTIME

    logger.info("🔧 ensure_runtime: Initialisierung startet …")
    key_present = bool(os.getenv("OPENAI_API_KEY"))
    logger.info("🔑 OPENAI_API_KEY present in server: {}", key_present)
    if not key_present:
        logger.warning("⚠️ Kein OPENAI_API_KEY im Uvicorn-Prozess. Setze ihn in docker-compose.yml unter 'gateway.environment' und restart den Service.")
    # ZEP-Client
    api_key = os.environ["ZEP_API_KEY"]
    base = _sanitized_base()
    client = AsyncZep(api_key=api_key, base_url=base) if base else AsyncZep(api_key=api_key)
    logger.info("🌐 ZEP-Client init {}", base or "<default>")

    # User/Thread
    user_id = os.getenv("ZEP_USER_ID") or os.getenv("GATEWAY_USER_ID", "local_Aaron")
    desired_tid = os.getenv("ZEP_THREAD_ID") or f"thread_{user_id}"
    logger.info("👤 user_id={} | 🧵 thread_id={} (desired)", user_id, desired_tid)
    await _ensure_user(client, user_id)
    canonical_tid = await _ensure_thread(client, desired_tid, user_id)

    # ZEP-Memory: Thread-Fassade (für Hub/Chat) + volle REST-Fassade (add/query)
    logger.info("🏗️ Initialisiere ZEP-Memory …")
    mem_thread = ZepThreadMemory(client=client, user_id=user_id, thread_id=canonical_tid)
    mem_full   = ZepMemory(     client=client, user_id=user_id, thread_id=canonical_tid)
    try:
        await mem_full.ensure_thread()  # sichert Thread für REST-Endpunkte
        logger.info("🧠 Memory (REST) mit Thread-ID {} synchronisiert", canonical_tid)
    except Exception as e:
        logger.warning("⚠️ Memory-Ensure (REST) schlug fehl: {}", e)

    # Orchestrator-Konfig
    orch_nested = os.getenv("ORCH_NESTED", "false").lower() == "true"
    persist_cfg = {
        "workcell": os.getenv("ORCH_PERSIST_WORKCELL", "inmem"),
        "orchestrator": os.getenv("ORCH_PERSIST_ORCH", "graph"),
        "agent_st": os.getenv("ORCH_PERSIST_AGENT_ST", "inmem"),
    }
    tm_raw = (os.getenv("THREAD_MODE", "isolated") or "isolated").lower()
    thread_mode: Literal["isolated", "shared"] = cast(Literal["isolated", "shared"], "shared" if tm_raw == "shared" else "isolated")

    targets: Dict[str, PersistTarget] = {
        "workcell": cast(PersistTarget, persist_cfg["workcell"]),
        "orch":     cast(PersistTarget, persist_cfg["orchestrator"]),
        "agent_st": cast(PersistTarget, persist_cfg["agent_st"]),
    }

    # Sync-Memory-Adapter
    if mem_thread is None:
        raise RuntimeError("ZEP-Memory fehlt – Adapter kann nicht gebaut werden.")
    mem_adapter = ZepMemoryAdapter(zep_facade=mem_thread, thread_mode=thread_mode, targets=targets)
    
    # Router laden – ohne Fallback
    from backend.captain_spoke_registry import RealRouter, load_default_spokes
    router_obj = RealRouter(load_default_spokes())
    logger.info("🔌 RealRouter aktiv (registry-basiert).")

    # 👉 jetzt ist router_obj garantiert gebunden:
    logger.info("🧩 Router: {}", type(router_obj).__name__)

    # Hub + Chat-Facade: Hub bauen, core2-Lobby anhängen, Fassade bereitstellen
    hub = CaptainHub(router=router_obj, memory=mem_adapter, policy=HubPolicy(persist_workcell=targets["workcell"]))

    hub_lobby = hub.build_chat_facade(zep_facade=mem_thread, user_id=user_id, thread_id=canonical_tid)


    # # Optionalen Sync-Chat-Hook bereitstellen, damit der Fallback "reden" kann
    # try:
    #     chat_obj = getattr(hub, "chat", None)
    #     # akzeptiere reply ODER converse
    #     chat_call = getattr(chat_obj, "reply", None) or getattr(chat_obj, "converse", None)
    #     if callable(chat_call) and not hasattr(hub, "chat_reply_sync"):
    #         import asyncio, inspect, json
    #         from typing import Optional

    #         def _chat_sync(text: str) -> Optional[str]:
    #             """
    #             Ruft hub.chat.reply|converse(text) auf.
    #             - async → asyncio.run(...)
    #             - sync  → direkt
    #             Normalisiert Rückgaben auf str|None (dict → dict['reply'] oder JSON).
    #             """
    #             try:
    #                 res = chat_call(text)  # kann sync oder coroutine sein

    #                 if inspect.iscoroutine(res):
    #                     # lokale Typen-Imports -> Pylance-freundlich
    #                     from typing import cast, Coroutine, Any
    #                     coro = cast(Coroutine[Any, Any, object], res)
    #                     out = asyncio.run(coro)
    #                 else:
    #                     out = res

    #                 # Normalisierung
    #                 if out is None:
    #                     return None
    #                 if isinstance(out, dict):
    #                     rep = out.get("reply")
    #                     if isinstance(rep, str):
    #                         return rep
    #                     # notfalls das Dict als JSON zurückgeben
    #                     return json.dumps(out, ensure_ascii=False)
    #                 if isinstance(out, str):
    #                     return out
    #                 return str(out)
    #             except Exception:
    #                 return None

    #         setattr(hub, "chat_reply_sync", _chat_sync)
    #         logger.info("🔗 Chat-Bridge aktiviert (hub.chat_reply_sync).")
    # except Exception as e:
    #     logger.warning("Chat-Bridge konnte nicht aktiviert werden: {}", e)

    # nachdem router_obj feststeht (RealRouter oder _NullRouter)
    logger.info("🧩 Router: {}", type(router_obj).__name__)

    # direkt nach Hub- und Facade-Bau
    logger.info(
        "🟩 CaptainHub aktiv – Chat-Facade bereit (user_id={}, thread_id={})",
        user_id, canonical_tid
    )

    _RUNTIME = RuntimeState(
        zep_client=client,
        user_id=user_id,
        thread_id=canonical_tid,
        lobby=hub_lobby,   # Hub-Chat-Facade als primäre Lobby nach außen
        memory=mem_full,   # volle Autogen-kompatible Fassade für REST (/api/memory/*)
        mem_thread=mem_thread,
        hub=hub,
        orch_nested=orch_nested,
        persist_cfg=persist_cfg,
    )
    logger.info("✅ ensure_runtime: bereit (thread_id={!r}; nested={})", canonical_tid, orch_nested)
    return _RUNTIME


def _sanitized_base() -> Optional[str]:
    raw = (os.getenv("ZEP_BASE_URL", "") or os.getenv("ZEP_API_BASE_URL", "") or "").strip()
    if not raw:
        return None
    base = raw.rstrip("/")
    if base.endswith("/api/v2"):
        base = base[:-7]
    elif base.endswith("/api"):
        base = base[:-4]
    return base or None


__all__ = ["RuntimeState", "ensure_runtime"]
