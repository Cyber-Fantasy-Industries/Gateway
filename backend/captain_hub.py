
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple, Callable, cast, Sequence
from .prompts import render_planner, render_implement, render_review
from .workcell_io import WorkcellIO
import uuid 
import os
from loguru import logger


def _llm_chat(messages: Sequence[dict[str, Any]], model: str | None = None) -> str | None:
    """
    Versucht zuerst neues OpenAI-SDK (>=1.x), dann altes (<1.x).
    Unterstützt OPENAI_BASE_URL (z.B. Azure, LM Studio, Ollama Gateway).
    Setze LLM_DEBUG=1 für Fehlerlogs.s
    """
    mdl = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base = os.getenv("OPENAI_BASE_URL")  # optional (Azure/LM Studio/Ollama/OpenRouter)
    key  = os.getenv("OPENAI_API_KEY", "")

    def _dbg(exc: Exception, where: str):
        if os.getenv("LLM_DEBUG") == "1":
            logger.warning("LLM call failed in {}: {}", where, repr(exc))

    # Neues SDK (openai>=1.x)
    try:
        from openai import OpenAI  # type: ignore
        kwargs: dict[str, Any] = {}
        if base:
            kwargs["base_url"] = base
        if key:
            kwargs["api_key"] = key
        client = OpenAI(**kwargs)  # type: ignore[arg-type]
        resp = client.chat.completions.create(
            model=mdl,
            messages=cast(Any, messages),  # Pylance beruhigen
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        _dbg(e, "new-sdk")

    # Altes SDK (openai<1.x)
    try:
        import openai  # type: ignore
        if base:
            # Manche Gateways (LM Studio/Ollama Gateway) nutzen diese Felder
            openai.api_base = base  # type: ignore[attr-defined]
        if key and not getattr(openai, "api_key", None):
            openai.api_key = key  # type: ignore[attr-defined]
        resp = openai.ChatCompletion.create(  # type: ignore[attr-defined]
            model=mdl,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
        )
        choice = resp["choices"][0]
        content = choice.get("message", {}).get("content") or choice.get("text")
        return (content or "").strip()
    except Exception as e:
        _dbg(e, "old-sdk")

    return None



# --- Protocols kept inline for typing compatibility ---------------------------
class Memory(Protocol):
    def create_space(self, *, kind: str, name: Optional[str] = None, parent_id: Optional[str] = None) -> str: ...
    def write_message(self, *, space_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None: ...
    def write_event(self, *, space_id: str, type: str, payload: Dict[str, Any]) -> None: ...
    def set_status(self, *, space_id: str, status: str) -> None: ...
    def gc(self, *, space_id: str) -> None: ...

class Impl(Protocol):
    def run(self, prompt: str) -> str: ...

class Spoke(Protocol):
    role: str
    score: int
    impl: Impl
    def acquire(self) -> None: ...
    def release(self) -> None: ...

class Router(Protocol):
    def candidates(self, role: str, tags: Set[str]) -> List[Spoke]: ...

@dataclass
class HubPolicy:
    persist_workcell: str = "graph"

class TicketStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"

@dataclass
class Ticket:
    ticket_id: str
    goal: str
    deliverables: List[str]
    constraints: List[str]
    workcell_space_id: Optional[str] = None
    status: TicketStatus = TicketStatus.pending

@dataclass
class OrchestrationRun:
    run_id: str


class HubChatFacade:
    """
    Schlanke Chat-Fassade über CaptainHub.
    - Persistiert den User-Prompt im ZEP-Thread
    - Ruft direkt ein LLM mit ZEP-Kontext (KEINE Orchestrierung!)
    - Persistiert die Assistant-Antwort im ZEP-Thread
    - Liefert {reply, steps} ähnlich core2 zurück
    """
    def __init__(self, hub, zep_facade, user_id: str, thread_id: str):
        self.hub = hub
        self.zep = zep_facade
        self.user_id = user_id
        self.thread_id = thread_id

    async def _build_messages(self, prompt: str) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        ctx = None
        try:
            if hasattr(self.zep, "build_context_block"):
                ctx = await self.zep.build_context_block(include_recent=True, recent_limit=8)  # type: ignore
        except Exception:
            ctx = None

        if ctx:
            msgs.append({"role": "system", "content": f"Nutze folgenden kompakten Kontext:\n{ctx}"})
        msgs.append({"role": "user", "content": prompt})
        return msgs


    async def converse(self, prompt: str) -> dict:
        # 1) User-Message speichern (best effort)
        try:
            await self.zep.add_user_message(prompt)  # type: ignore
        except Exception:
            pass

        # 2) Direktes LLM mit ZEP-Kontext (kein hub.run_ticket!)
        reply: str | None = None
        try:
            messages = await self._build_messages(prompt)
            reply = _llm_chat(messages)
        except Exception:
            reply = None

        # Fallback – wenn kein LLM verfügbar ist
        if not reply:
            reply = f"Ich habe dich gehört: „{prompt}“ (LLM nicht verfügbar)."

        # 3) Assistant-Message spiegeln (best effort)
        try:
            await self.zep.add_assistant_message(reply)  # type: ignore
        except Exception:
            pass

        # 4) core2-ähnliches Format
        steps = [["assistant", reply]]
        return {"reply": reply, "steps": steps}


    
# --- Hub ----------------------------------------------------------------------
class CaptainHub:
    """CaptainHub mit DRY-Prompts & Schritt-I/O via WorkcellIO."""

    def __init__(self, *, router: Router, memory: Memory, policy: Optional[HubPolicy] = None) -> None:
        self.router = router
        self.memory = memory
        self.policy = policy or HubPolicy()
        self.io = WorkcellIO(memory)

    def build_chat_facade(self, *, zep_facade, user_id: str, thread_id: str) -> HubChatFacade:
        facade = HubChatFacade(self, zep_facade, user_id, thread_id)
        # wichtig: damit bootstrap die Bridge aktivieren kann
        setattr(self, "chat", facade)
        return facade
    
    chat_reply_sync: Optional[Callable[[str], Optional[str]]] = None
    def _try_chat_reply(self, text: str) -> Optional[str]:
        """
        Optionaler synchroner Hook:
        Wenn zur Laufzeit ein Attribut `chat_reply_sync` (callable) am Hub hängt,
        wird es genutzt. Andernfalls None.
        """
        try:
            fn = getattr(self, "chat_reply_sync", None)
            if callable(fn):
                # auf erwartete Signatur einschränken
                typed_fn = cast(Callable[[str], Optional[str]], fn)
                res = typed_fn(text)
                # Defensive: nur str|None zurückgeben
                if res is None or isinstance(res, str):
                    return res
                return str(res)
        except Exception:
            pass
        return None


    # -- Auswahl & Tags ---------------------------------------------------------
    def _match_spokes(self, role: str, tags: Set[str]) -> List[Tuple[int, Spoke]]:
        cands = self.router.candidates(role, tags) or []
        return sorted(((getattr(s, "score", 0), s) for s in cands), key=lambda t: t[0], reverse=True)

    def _compute_tags(self, ticket: Ticket) -> Set[str]:
        def toks(xs: List[str]) -> Set[str]:
            out: Set[str] = set()
            for x in xs:
                for w in x.replace(",", " ").split():
                    w = w.strip().lower()
                    if w:
                        out.add(w)
            return out
        return toks(ticket.deliverables) | toks(ticket.constraints)

    def _choose_planner(self, tags: Set[str]) -> Optional[Spoke]:
        r = self._match_spokes("planner", tags);  return r[0][1] if r else None

    def _choose_coder(self, tags: Set[str]) -> Optional[Spoke]:
        r = self._match_spokes("coder", tags);    return r[0][1] if r else None

    def _choose_critic(self, tags: Set[str]) -> Optional[Spoke]:
        r = self._match_spokes("critic", tags);   return r[0][1] if r else None

    # -- Workcell mgmt via WorkcellIO ------------------------------------------
    def allocate_workcell(self, ticket: Ticket) -> Dict[str, Spoke]:
        tags = self._compute_tags(ticket)
        chosen: Dict[str, Spoke] = {}
        if (pl := self._choose_planner(tags)): pl.acquire(); chosen["planner"] = pl
        if (cd := self._choose_coder(tags)):   cd.acquire(); chosen["coder"] = cd
        if (cr := self._choose_critic(tags)):  cr.acquire(); chosen["critic"] = cr
        return chosen

    def _release_workcell(self, chosen: Dict[str, Spoke]) -> None:
        for s in chosen.values():
            try: s.release()
            except Exception: pass

    # -- Pipeline ---------------------------------------------------------------
    def run_ticket(self, *, run: OrchestrationRun, ticket: Ticket) -> Dict[str, Any]:
        tags = self._compute_tags(ticket)
        chosen = self.allocate_workcell(ticket)
        try:
            opened = self.io.open(ticket_id=ticket.ticket_id, workcell_space_id=ticket.workcell_space_id)
            wc, st = opened.workcell_sid, opened.st_ids
            self.io.start(workcell_sid=wc, payload={"run_id": run.run_id, "ticket_id": ticket.ticket_id})

            # Fallback: wenn keine Spokes ausgewählt wurden (Registry leer)
            if not chosen:
                plan = f"(Fallback) Plan aus Ziel:\n{ticket.goal}"
                self.io.step_out(workcell_sid=wc, st_ids=st, role="planner", content=plan, prompt=None)

                # Anti-Rekursion: wenn wir bereits in der Chat-Fassade sind, NICHT die Bridge rufen
                if getattr(self, "_in_chat_facade", False):
                    impl = f"(No coder) Nutze Plan:\n{plan}"
                else:
                    impl = self._try_chat_reply(ticket.goal) or f"(No coder) Nutze Plan:\n{plan}"

                self.io.step_out(workcell_sid=wc, st_ids=st, role="coder", content=impl, prompt=None)
                review = "OK"
                self.io.close(workcell_sid=wc, review=review, impl_ok=True, do_gc=True)
                return {"plan": plan, "impl": impl, "review": review, "workcell_space_id": wc}


            # Planner
            planner = chosen.get("planner")
            plan_prompt = render_planner(ticket.goal, ticket.deliverables, ticket.constraints)
            if planner:
                plan = planner.impl.run(plan_prompt)
            else:
                plan = f"(No planner) Plan aus Ziel:\n{ticket.goal}"
            self.io.step_out(workcell_sid=wc, st_ids=st, role="planner", content=plan, prompt=plan_prompt)

            # Coder (Template)
            coder = chosen.get("coder")
            critic = chosen.get("critic")
            impl, review = self.coder_step(
                run=run, ticket=ticket, plan=plan, coder=coder, critic=critic,
                workcell_space_id=wc, st_ids=st
            )

            # Close
            self.io.close(workcell_sid=wc, review=review, impl_ok=bool(impl), do_gc=True)
            return {"plan": plan, "impl": impl, "review": review, "workcell_space_id": wc}
        finally:
            self._release_workcell(chosen)

    # -- Template Method --------------------------------------------------------
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
        # Implement
        if not coder:
            impl = f"(No coder) Nutze Plan:\n{plan}"
            impl_prompt = None
        else:
            impl_prompt = render_implement(plan, ticket.deliverables, ticket.constraints)
            impl = coder.impl.run(impl_prompt)
        self.io.step_out(workcell_sid=workcell_space_id, st_ids=st_ids, role="coder", content=impl, prompt=impl_prompt)

        # Review
        if critic:
            review_prompt = render_review(ticket.deliverables, ticket.constraints)
            review = critic.impl.run(review_prompt)
            self.io.step_out(workcell_sid=workcell_space_id, st_ids=st_ids, role="critic", content=review, prompt=review_prompt)
        else:
            review = "OK"

        return impl, review
