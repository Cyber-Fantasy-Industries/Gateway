
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

# Keep protocol tiny and compatible with your existing Memory
class Memory(Protocol):
    def create_space(self, *, kind: str, name: Optional[str] = None, parent_id: Optional[str] = None) -> str: ...
    def write_message(self, *, space_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None: ...
    def write_event(self, *, space_id: str, type: str, payload: Dict[str, Any]) -> None: ...
    def set_status(self, *, space_id: str, status: str) -> None: ...
    def gc(self, *, space_id: str) -> None: ...

@dataclass
class WorkcellOpenResult:
    workcell_sid: str
    st_ids: Dict[str, str]

class WorkcellIO:
    """
    DRY-Wrapper für häufige I/O-Schritte:
    - Workcell & ST-Räume anlegen
    - Status & Events setzen
    - Schritt-Outputs gleichzeitig in Workcell + ST spiegeln
    """
    def __init__(self, memory: Memory) -> None:
        self.m = memory

    # --- Lifecycle -------------------------------------------------------------
    def open(self, *, ticket_id: str, workcell_space_id: Optional[str] = None) -> WorkcellOpenResult:
        wc = workcell_space_id or self.m.create_space(kind="workcell", name=f"wc:{ticket_id}")
        st_pl = self.m.create_space(kind="st", name="planner", parent_id=wc)
        st_cd = self.m.create_space(kind="st", name="coder", parent_id=wc)
        st_cr = self.m.create_space(kind="st", name="critic", parent_id=wc)
        self.m.set_status(space_id=wc, status="running")
        return WorkcellOpenResult(workcell_sid=wc, st_ids={"planner": st_pl, "coder": st_cd, "critic": st_cr})

    def start(self, *, workcell_sid: str, payload: Dict[str, Any]) -> None:
        self._event(workcell_sid, "start", payload)

    def close(self, *, workcell_sid: str, review: str = "OK", impl_ok: bool = True, do_gc: bool = True) -> None:
        self.m.set_status(space_id=workcell_sid, status="done")
        self._event(workcell_sid, "done", {"impl_ok": impl_ok, "review": review})
        if do_gc:
            self.m.gc(space_id=workcell_sid)

    # --- Steps -----------------------------------------------------------------
    def step_out(self, *, workcell_sid: str, st_ids: Dict[str, str], role: str, content: str, prompt: Optional[str] = None) -> None:
        meta = {"prompt": prompt} if prompt else None
        self.m.write_message(space_id=workcell_sid, role=role, content=content, metadata=meta)
        # Mirror raw content into role's ST
        sid = st_ids.get(role)
        if sid:
            self.m.write_message(space_id=sid, role=role, content=content)

    def _event(self, workcell_sid: str, type: str, payload: Dict[str, Any]) -> None:
        try:
            self.m.write_event(space_id=workcell_sid, type=type, payload=payload)
        except Exception:
            # Event darf nicht tödlich sein
            pass
