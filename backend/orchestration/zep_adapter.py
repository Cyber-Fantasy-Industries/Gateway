from __future__ import annotations
from typing import Any, Dict

"""
ZepMemoryAdapter
----------------
Synchrones Memory-Interface für CaptainHub/WorkcellIO, das eine bestehende
**async** ZEP-Thread/Graph-Fassade ("zep_facade") wrappt. Ziel: Hub bleibt
thread- und CLI-freundlich (sync), während intern asynchron gegen ZEP
gearbeitet werden kann.

Minimal-Implementierung:
- Bietet das **Memory-Protokoll** (create_space, write_message, write_event,
  set_status, gc) synchron an.
- Default-Persistenz ist **in-memory**; spätere Routen zu ZEP-Graph/Thread
  können hier ergänzt werden (TODOs markiert).

Hinweis: Dieser Adapter ist bewusst leichtgewichtig, damit Pylance die
strukturelle Typkompatibilität zu "Memory" erkennt und CaptainHub ohne
Type-Errors instanziiert werden kann.
"""

from typing import Any, Dict, Optional, Literal
from dataclasses import dataclass, field
import uuid
import time


PersistTarget = Literal["inmem", "thread", "graph"]
ThreadMode = Literal["isolated", "shared"]


@dataclass
class _Space:
    space_id: str
    kind: str
    name: Optional[str] = None
    parent_id: Optional[str] = None
    status: str = "open"
    # Rohspeicher für Nachrichten und Events (minimal, für v2 ausreichend)
    messages: list = field(default_factory=list)
    events: list = field(default_factory=list)

from typing import Mapping
class ZepMemoryAdapter:
    def __init__(
        self,
        *,
        zep_facade: Any,
        thread_mode: ThreadMode = "isolated",
        targets: Optional[Mapping[str, PersistTarget]
                          ] = None
        ) -> None:

        self._zep = zep_facade
        self._thread_mode: ThreadMode = thread_mode
        self._targets: Dict[str, PersistTarget] = {
            "workcell": "inmem",
            "orch": "graph",
            "agent_st": "inmem",
        }
        if targets:
            self._targets.update(dict(targets))

        # In-Memory Ablage (für inmem/graph Defaults in dieser Minimalversion)
        self._spaces: Dict[str, _Space] = {}

    # ---------------------------------------------------------------------
    # Synchrones Memory-Protokoll (structural typing für CaptainHub)
    # ---------------------------------------------------------------------
    def create_space(self, kind: str, name: Optional[str] = None, parent_id: Optional[str] = None) -> str:
        """Erzeugt einen Space und gibt dessen ID zurück (synchron)."""
        sid = str(uuid.uuid4())
        self._spaces[sid] = _Space(space_id=sid, kind=kind, name=name, parent_id=parent_id)
        # TODO: Bei target == "graph" könnte hier ein ZEP-Graph-Space angelegt werden.
        return sid

    def write_message(self, space_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Schreibt eine Nachricht in den Space (synchron)."""
        sp = self._spaces.get(space_id)
        if not sp:
            raise KeyError(f"unknown space_id {space_id}")
        sp.messages.append({
            "ts": time.time(),
            "role": role,
            "content": content,
            "meta": metadata or {},
        })
        # TODO: Bei target == "thread"/"graph" hier in ZEP spiegeln (async → fire/forget).

    # 2) write_event keyword-only + richtiger Param-Name
    def write_event(self, *, space_id: str, type: str, payload: Dict[str, Any]) -> None:
        sp = self._spaces.get(space_id)
        if not sp:
            raise KeyError(f"unknown space_id {space_id}")
        sp.events.append({"ts": time.time(), "type": type, "payload": payload})
        # TODO: optional nach ZEP spiegeln

    def set_status(self, space_id: str, status: str) -> None:
        sp = self._spaces.get(space_id)
        if not sp:
            raise KeyError(f"unknown space_id {space_id}")
        sp.status = status

    def gc(self, space_id: str) -> None:
        """Aufräumen (synchron). In der Minimalversion wird der Space gelöscht."""
        # TODO: Bei persistenten Targets ggf. Soft-GC/TTL
        self._spaces.pop(space_id, None)

    # ---------------------------------------------------------------------
    # Optionale Hilfen/Diag
    # ---------------------------------------------------------------------
    @property
    def thread_mode(self) -> ThreadMode:
        return self._thread_mode

    @property
    def targets(self) -> Dict[str, PersistTarget]:
        return dict(self._targets)

    def space_snapshot(self, space_id: str) -> Dict[str, Any]:
        sp = self._spaces.get(space_id)
        if not sp:
            raise KeyError(f"unknown space_id {space_id}")
        return {
            "space_id": sp.space_id,
            "kind": sp.kind,
            "name": sp.name,
            "parent_id": sp.parent_id,
            "status": sp.status,
            "messages": list(sp.messages),
            "events": list(sp.events),
        }
