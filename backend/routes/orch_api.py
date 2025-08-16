# backend/routes/orch_api.py
from __future__ import annotations

import uuid
import inspect
from typing import Optional, List, Dict, Any, Callable, cast

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.captain_hub import Ticket, OrchestrationRun

router = APIRouter()

# In-Memory Run-Registry (leichtgewichtig, für Dev/CLI ausreichend)
_RUNS: Dict[str, Dict[str, Any]] = {}


# =========================
# Models
# =========================
class StartIn(BaseModel):
    goal: str
    deliverables: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    nested: Optional[bool] = False


class ChatIn(BaseModel):
    text: Optional[str] = None
    prompt: Optional[str] = None


# =========================
# Helpers
# =========================
def _has_any_spokes(hub) -> bool:
    """True, wenn der Router irgendeine Kandidatenliste liefert."""
    try:
        r = getattr(hub, "router", None)
        if r is None:
            return False
        roles = ("planner", "coder", "critic")
        for role in roles:
            try:
                cands = r.candidates(role, set())
            except Exception:
                cands = []
            if cands:
                return True
        return False
    except Exception:
        return False


# =========================
# Routes
# =========================
@router.post("/start")
async def orch_start(body: StartIn, request: Request, background_tasks: BackgroundTasks):
    """Startet eine Orchestrierung im Hintergrund und liefert eine run_id zurück."""
    hub = getattr(request.app.state, "hub", None)
    if hub is None:
        return {"run_id": None, "error": "hub not ready"}

    run_id = f"run_{uuid.uuid4().hex}"
    goal = body.goal.strip()
    deliverables = body.deliverables or []
    constraints = body.constraints or []

    run = OrchestrationRun(run_id=run_id)
    ticket = Ticket(ticket_id=str(uuid.uuid4()), goal=goal, deliverables=deliverables, constraints=constraints)

    def _do():
        try:
            res = hub.run_ticket(run=run, ticket=ticket)
            _RUNS[run_id] = {"run_id": run_id, "goal": goal, "success": True, "artifacts": res}
        except Exception as e:
            _RUNS[run_id] = {"run_id": run_id, "goal": goal, "success": False, "error": str(e)}

    background_tasks.add_task(_do)
    return {"run_id": run_id}


@router.get("/status")
async def orch_status(run_id: str):
    """Liefert den zuletzt bekannten Status/Result eines Runs."""
    return {"run_id": run_id, "result": _RUNS.get(run_id)}


@router.get("/_diag")
async def orch_diag(request: Request):
    """Minimale Diagnoseausgabe zu Hub/Memory/Adapter/Persist."""
    app = request.app
    hub = getattr(app.state, "hub", None)
    mem = getattr(app.state, "memory", None)
    adapter = getattr(app.state, "adapter", None)
    persist = getattr(app.state, "persist_cfg", {}) or {}

    # targets können entweder top-level liegen oder unter persist["targets"]
    targets = None
    if isinstance(persist, dict):
        if "targets" in persist and isinstance(persist["targets"], dict):
            targets = persist["targets"]
        else:
            # Legacy-Layout
            targets = {
                "workcell": persist.get("workcell"),
                "orch": persist.get("orchestrator") or persist.get("orch"),
                "agent_st": persist.get("agent_st"),
            }

    return {
        "has_hub": hub is not None,
        "user_id": getattr(app.state, "user_id", None),
        "persist": targets or {},
        "has_memory": mem is not None,
        "memory_type": type(mem).__name__ if mem else None,
        "adapter": {
            "thread_mode": getattr(adapter, "thread_mode", None),
            "targets": getattr(adapter, "targets", None),
        },
    }


@router.post("/chat")
async def orch_chat(body: ChatIn, request: Request):
    """
    One-shot Chat über den Orchestrator:
    - Wenn Spokes vorhanden: Hub-Pipeline (Planner/Coder/Critic)
    - Sonst: Hub-Bridge (hub.chat_reply_sync) oder direkte Chat-Fassade (reply/converse)
    - Fallback: einfacher Plan/Impl-Text
    """
    goal = (body.text or body.prompt or "").strip()
    if not goal:
        return {"reply": "", "steps": []}

    hub = getattr(request.app.state, "hub", None)
    lobby = getattr(request.app.state, "lobby", None)

    # 1) Wenn Spokes registriert sind → volle Hub-Pipeline
    if hub and _has_any_spokes(hub):
        run = OrchestrationRun(run_id=str(uuid.uuid4()))
        ticket = Ticket(ticket_id=str(uuid.uuid4()), goal=goal, deliverables=[], constraints=[])
        res = await run_in_threadpool(hub.run_ticket, run, ticket)
        steps: List[List[str]] = []
        if res.get("plan"):
            steps.append(["planner", res["plan"]])
        if res.get("impl"):
            steps.append(["coder", res["impl"]])
        if res.get("review"):
            steps.append(["critic", res["review"]])
        return {"reply": res.get("impl") or "", "steps": steps, "workcell_space_id": res.get("workcell_space_id")}

    # 2) Hub-Bridge (sync) – im bootstrap gesetzt, wenn möglich
    if hub:
        try:
            sync_fn = getattr(hub, "chat_reply_sync", None)
            if callable(sync_fn):
                call_sync = cast(Callable[[str], Optional[str]], sync_fn)
                reply = await run_in_threadpool(call_sync, goal)
                if reply:
                    return {"reply": reply, "steps": []}
        except Exception:
            pass

        # 3) Direkte Chat-Fassade (reply oder converse), async/sync
        chat_obj = getattr(hub, "chat", None)
        for attr in ("reply", "converse"):
            fn = getattr(chat_obj, attr, None)
            if not callable(fn):
                continue
            try:
                if inspect.iscoroutinefunction(fn):
                    out = await fn(goal)
                else:
                    out = await run_in_threadpool(fn, goal)
                if isinstance(out, dict):
                    rep = out.get("reply")
                    if isinstance(rep, str) and rep:
                        return {"reply": rep, "steps": out.get("steps", [])}
                elif isinstance(out, str) and out:
                    return {"reply": out, "steps": []}
            except Exception:
                continue

    # 4) Fallback: Lobby (falls vorhanden)
    if lobby and hasattr(lobby, "converse"):
        try:
            out = await lobby.converse(goal)
            if isinstance(out, dict):
                return {"reply": out.get("reply", ""), "steps": out.get("steps", [])}
            if isinstance(out, tuple):
                reply = out[0]
                steps = out[1] if len(out) > 1 else []
                return {"reply": reply, "steps": steps}
        except Exception:
            pass

    # 5) Letzter Fallback (keine Chat-Engine verfügbar)
    plan = f"(Fallback) Plan aus Ziel:\n{goal}"
    impl = f"(No coder) Nutze Plan:\n{plan}"
    return {"reply": impl, "steps": [["planner", plan], ["coder", impl]]}
