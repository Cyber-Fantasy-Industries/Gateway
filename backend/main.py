from loguru import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.agents import router as agents_router
from backend.routes.conference import router as conference_router
from backend.routes.settings import router as settings_router
from backend.routes.websocket import router as websocket_router
from backend.routes.system import router as system_router
#from backend.routes.chat_api import router as chat_router
from backend.routes.memory_api import router as memory_router
from backend.routes.websocket import start_watcher
from contextlib import asynccontextmanager
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.agent_core.bootstrap import ensure_runtime
# nur die Chat-Funktionen hier importieren; das Router-Objekt wird unten
# bedarfsweise (ORCH_ENABLED) nachgeladen, um Redundanz zu vermeiden
from backend.routes.orch_api import orch_chat, ChatIn
import os
import time

# ──────────────────────────────────────────────────────────────────────────────
# Basis-Zeitzone (deterministische Logs & Schedules in Containern)
# ──────────────────────────────────────────────────────────────────────────────
tzset = getattr(time, "tzset", None)
if callable(tzset):
    tzset()

os.environ.setdefault("TZ", "Europe/Berlin")

tzset = getattr(time, "tzset", None)
if callable(tzset):
    tzset()


# ──────────────────────────────────────────────────────────────────────────────
# Konfiguration: Docker-freundlich, per ENV justierbar
# ──────────────────────────────────────────────────────────────────────────────
LOG_PATH = os.getenv("LOG_PATH", "logs")
LOG_ROTATION = os.getenv("LOG_ROTATION", "25 MB")
LOG_RETENTION = os.getenv("LOG_RETENTION")  # None → keine Retention
LOG_DIAGNOSE = os.getenv("LOG_DIAGNOSE", "true").lower() == "true"

CORS_ALLOW_ORIGINS_RAW = os.getenv("CORS_ALLOW_ORIGINS", "*")
if CORS_ALLOW_ORIGINS_RAW.strip() == "*":
    CORS_ALLOW_ORIGINS = ["*"]
    # Wildcard + Credentials ist per Spezifikation nicht zulässig → deaktivieren
    CORS_ALLOW_CREDENTIALS = False
else:
    CORS_ALLOW_ORIGINS = [o.strip() for o in CORS_ALLOW_ORIGINS_RAW.split(",") if o.strip()]
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

# ──────────────────────────────────────────────────────────────────────────────
# Logging-Setup
# ──────────────────────────────────────────────────────────────────────────────
os.makedirs(LOG_PATH, exist_ok=True)
logger.add(
    os.path.join(LOG_PATH, "server.log"),
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION if LOG_RETENTION else None,
    backtrace=True,
    diagnose=LOG_DIAGNOSE,
)
logger.info("📦 Gateway-Modul importiert — warte auf Lifespan-Start …")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startet Runtime & Watcher; sorgt für sauberen Shutdown in finally."""
    logger.info("🚀 Starte Gateway Runtime …")
    runtime = await ensure_runtime()

    # SSOT in app.state – Variablennamen bleiben stabil
    app.state.zep_client  = runtime.zep_client
    app.state.user_id     = runtime.user_id
    app.state.thread_id   = runtime.thread_id       # wieder explizit setzen (abhängig von Routen)
    app.state.lobby       = runtime.lobby
    app.state.memory      = runtime.memory
    app.state.runtime     = runtime  # optional, praktisch für Routen
    app.state.mem_thread  = getattr(runtime, "mem_thread", None)
    if app.state.mem_thread is None:
        # kein heimlicher Fallback: lieber hart und früh scheitern
        raise RuntimeError("mem_thread fehlt – Thread-Scope ist aktiviert, kann aber nicht arbeiten.")
    app.state.hub         = getattr(runtime, "hub", None)
    app.state.persist_cfg = getattr(runtime, "persist_cfg", {})
    app.state.orch_nested = getattr(runtime, "orch_nested", False)

    # Adapter robust auflösen: runtime.adapter → hub.zep_adapter (Fallback)
    adapter_from_runtime = getattr(runtime, "adapter", None)
    adapter_from_hub     = getattr(app.state.hub, "zep_adapter", None)
    app.state.adapter    = adapter_from_runtime or adapter_from_hub

    cfg = getattr(app.state, "persist_cfg", {}) or {}
    hub_cls     = type(app.state.hub).__name__ if app.state.hub else None
    adapter_obj = app.state.adapter

    thread_mode = getattr(adapter_obj, "thread_mode", None) or cfg.get("thread_mode")
    targets     = getattr(adapter_obj, "targets", None)     or cfg.get("targets")

    logger.info("🧠 Hub/Adapter: {} | thread_mode={} | targets={}", hub_cls, thread_mode, targets)

    logger.info("✅ Runtime bereit (user_id={}, thread_id={!r})", runtime.user_id, runtime.thread_id)

    # Zusatzdiagnose: Quelle des Adapters + Snapshot
    try:
        src = (
            "runtime.adapter" if app.state.adapter is adapter_from_runtime
            else "hub.zep_adapter" if app.state.adapter is adapter_from_hub
            else "unknown"
        )
        logger.info("🧪 Adapter-Quelle: {}", src)

        snapshot = None
        if adapter_obj is not None:
            space_snapshot_fn = getattr(adapter_obj, "space_snapshot", None)
            if callable(space_snapshot_fn):
                try:
                    snapshot = space_snapshot_fn()
                except Exception:
                    snapshot = None

        logger.debug("🧪 Adapter-Diag: thread_mode={} | targets={} | snapshot={}",
                    thread_mode, targets, snapshot)
    except Exception as e:
        logger.warning("Diag Hub/Adapter fehlgeschlagen: {}", e)

    watcher = None
    try:
        watcher = start_watcher(path="backend/")
        logger.info("🟢 Watcher gestartet für Pfad 'backend/'")
        yield
    finally:
        # Watcher stoppen
        try:
            if watcher is not None:
                if hasattr(watcher, "stop"): watcher.stop()
                if hasattr(watcher, "join"): watcher.join(timeout=5)
                logger.info("🔴 Watcher gestoppt")
        except Exception as e:
            logger.warning("Watcher-Cleanup schlug fehl: {}", e)

        # ZEP-Client schließen (sync/async tolerant)
        try:
            zep = getattr(app.state, "zep_client", None)
            if zep is not None:
                if hasattr(zep, "aclose") and callable(getattr(zep, "aclose")):
                    await zep.aclose()  # type: ignore[func-returns-value]
                elif hasattr(zep, "close") and callable(getattr(zep, "close")):
                    zep.close()
                logger.info("🔒 ZEP-Client-Verbindung geschlossen")
        except Exception as e:
            logger.warning("ZEP-Client-Cleanup schlug fehl: {}", e)



# ──────────────────────────────────────────────────────────────────────────────
# FastAPI-App
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    title="Gateway API",
    description="Modulare KI-Agentenplattform mit Autogen und UE5-Integration",
    version="0.1",
)

# CORS – sicher per ENV konfigurierbar; Wildcard erzwingt credentials=False
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routen (Bewusst uneinheitlich belassen – wird später vereinheitlicht)
ORCH_ENABLED = os.getenv("ORCH_ENABLED", "false").lower() == "true"
app.include_router(agents_router)
app.include_router(conference_router)
app.include_router(settings_router)
app.include_router(websocket_router)
app.include_router(system_router)

# 1) ZUERST der Kompatibilitäts-Alias für /api/chat
from typing import Any, Dict
from backend.routes.orch_api import orch_chat, ChatIn
from fastapi import Request
from fastapi.responses import JSONResponse

@app.post("/api/chat")
async def _chat_alias(request: Request) -> JSONResponse:
    # Debug: sehen, dass wirklich der Alias greift
    logger.debug("🔀 /api/chat via compat alias")
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    # Abwärtskompatibel: text/message → prompt
    if "prompt" not in payload:
        for k in ("text", "message"):
            if isinstance(payload.get(k), str):
                payload["prompt"] = payload.pop(k)
                break

    if "prompt" not in payload or not isinstance(payload["prompt"], str):
        return JSONResponse(
            {"detail": [{
                "type": "missing",
                "loc": ["body", "prompt"],
                "msg": "Field required",
                "input": payload
            }]},
            status_code=422
        )

    chat_in = ChatIn(**payload)
    res = await orch_chat(chat_in, request)
    return res if isinstance(res, JSONResponse) else JSONResponse(content=res)

# 2) DANACH erst die Router mounten (damit der Alias gewinnt)
#app.include_router(chat_router,   prefix="/api")
app.include_router(memory_router, prefix="/api")

# Optional: ORCH-Endpoints
if ORCH_ENABLED:
    from backend.routes.orch_api import router as orch_router
    app.include_router(orch_router, prefix="/api/orch")

app.add_api_route("/api/chat", _chat_alias, methods=["POST"])

# Health-Endpoint (für Docker/Logs): behebt 404 auf /api/health
@app.get("/api/health")
async def api_health():
    zep_ok = bool(getattr(app.state, "zep_client", None))
    return {
        "ok": True,
        "orch_enabled": ORCH_ENABLED,
        "user_id": getattr(app.state, "user_id", None),
        "thread_id": getattr(app.state, "thread_id", None),
        "zep_client": zep_ok,
    }

if ORCH_ENABLED:
    # Router nur einbinden, wenn explizit aktiviert
    from backend.routes.orch_api import router as orch_router
    app.include_router(orch_router, prefix="/api/orch")


if __name__ == "__main__":
    import uvicorn

    logger.info("🏁 Starte Uvicorn-Server auf 0.0.0.0:8080 …")
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)