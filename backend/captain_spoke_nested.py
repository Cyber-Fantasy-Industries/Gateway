
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Set, Tuple

"""
CaptainHubNested: überschreibt **nur** die Coder-Wahl und den Coder-Schritt.
Kein doppeltes run_ticket, keine duplizierten Events/Spaces/GC.
"""

from .captain_hub import CaptainHub, OrchestrationRun, Ticket, Spoke, Memory


# === Nested Captain-Spoke =====================================================
class HasRunNested(Protocol):
    def run_nested(
        self,
        *,
        memory: Memory,
        run_id: str,
        ticket_id: str,
        parent_workcell_space_id: str,
        tags: Set[str],
    ) -> Dict[str, Any]: ...


@dataclass
class CaptainSpoke:
    """Platzhalter/Adapter: Spoke mit `run_nested`-Funktion (Builder-Captain)."""
    role: str
    score: int
    impl: Any  # ungenutzt, nested ruft direkt run_nested
    runner: HasRunNested

    def acquire(self) -> None: ...
    def release(self) -> None: ...

    def run_nested(
        self,
        *,
        memory: Memory,
        run_id: str,
        ticket_id: str,
        parent_workcell_space_id: str,
        tags: Set[str],
    ) -> Dict[str, Any]:
        return self.runner.run_nested(
            memory=memory,
            run_id=run_id,
            ticket_id=ticket_id,
            parent_workcell_space_id=parent_workcell_space_id,
            tags=tags,
        )


# === Hub-Subklasse =============================================================
class CaptainHubNested(CaptainHub):
    """Nur Coder-Strategie austauschen; Pipeline bleibt in der Basis."""

    # 1) Coder-Wahl: Erlaube builder_captain Spokes, den Slot zu gewinnen
    def _choose_coder(self, tags: Set[str]) -> Optional[Spoke]:
        # Hole Kandidaten für beide Rollen
        bc_list = self.router.candidates("builder_captain", tags) or []
        cd_list = self.router.candidates("coder", tags) or []

        def best(xs):
            try:
                return sorted(xs, key=lambda s: getattr(s, "score", 0), reverse=True)[0]
            except Exception:
                return None

        bc = best(bc_list)
        cd = best(cd_list)

        if bc and cd:
            return bc if getattr(bc, "score", 0) >= getattr(cd, "score", 0) else cd
        return bc or cd or None

    # 2) Coder-Phase: Wenn CaptainSpoke (mit run_nested) gewählt wurde, nutze nested
    def coder_step(
        self,
        *,
        run: OrchestrationRun,
        ticket: Ticket,
        plan: str,
        coder: Optional[Spoke],
        critic: Optional[Spoke],
        workcell_space_id: str,
        st_ids: Dict[str, str],
    ) -> Tuple[str, str]:
        if coder and hasattr(coder, "run_nested"):
            # Tags einmalig berechnen (gleich wie in allocate_workcell)
            tags = self._compute_tags(ticket)
            nested_result = getattr(coder, "run_nested")(
                memory=self.memory,
                run_id=run.run_id,
                ticket_id=ticket.ticket_id,
                parent_workcell_space_id=workcell_space_id,
                tags=tags,
            )
            impl = str(nested_result.get("impl", ""))
            review = str(nested_result.get("review", "OK"))

            # Optional noch in ST-Spaces spiegeln (für Konsistenz)
            if impl:
                self.memory.write_message(space_id=st_ids["coder"], role="coder", content=impl)
            if review:
                self.memory.write_message(space_id=st_ids["critic"], role="critic", content=review)

            return impl, review

        # Fallback: Standard-Verhalten
        return super().coder_step(
            run=run,
            ticket=ticket,
            plan=plan,
            coder=coder,
            critic=critic,
            workcell_space_id=workcell_space_id,
            st_ids=st_ids,
        )
