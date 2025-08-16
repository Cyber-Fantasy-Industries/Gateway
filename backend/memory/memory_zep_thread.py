# 2) backend/memory/memory_zep_thread.py

"""
ZepThreadMemory (async-only)
----------------------------
- Ensures/lazily creates a thread
- Adds user/assistant/system messages (with recreate+retry on 404)
- Builds a compact context block (user_context + recent)
"""
from __future__ import annotations

from typing import Any, Optional, List, Dict, Set
from zep_cloud.core.api_error import ApiError

try:
    from loguru import logger
except Exception:  # pragma: no cover
    class _Dummy:
        def debug(self, *a, **k): pass
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
    logger = _Dummy()


class ZepThreadMemory:
    def __init__(
        self,
        client,
        user_id: str,
        thread_id: Optional[str] = None,
        *,
        default_context_mode: str = "basic",
    ) -> None:
        self._client = client
        self._user_id = user_id
        self._thread_id = thread_id
        self._default_context_mode = default_context_mode

    # -------------------------
    # Properties / accessors
    # -------------------------
    @property
    def thread_id(self) -> Optional[str]:
        return self._thread_id

    def set_thread(self, thread_id: str) -> None:
        self._thread_id = thread_id

    def _is_local(self) -> bool:
        tid = getattr(self, "_thread_id", None)
        return isinstance(tid, str) and tid.startswith("local_")

    @property
    def is_local(self) -> bool:
        return self._is_local()

    # -------------------------
    # Core helpers
    # -------------------------
    async def ensure_thread(self, force_check: bool = False) -> str:
        """
        Ensure a remote Zep thread exists and cache its id.
        Fast-path: if we already hold an id and no force_check, do nothing.
        """
        # FAST-PATH: vorhandene ID → kein Remote-Call, kein Log
        if self._thread_id and not force_check:
            return self._thread_id

        # Local-Threads nicht remote verifizieren
        if self._thread_id and self._thread_id.startswith("local_"):
            return self._thread_id

        # Hier erst remote prüfen/erstellen
        # (verwende deinen bisherigen Remote-Call; Beispiel unten ist Platzhalter)
        resp = await self._client.thread.get_or_create(user_id=self._user_id, thread_id=self._thread_id)
        tid = getattr(resp, "thread_id", None) or getattr(resp, "id", None)
        if not tid:
            # Fallback: weise eine lokale ID zu (defensiv)
            tid = f"local_{self._user_id}"
        self._thread_id = str(tid)
        # optional: nur HIER einmal loggen
        # logger.debug("ensure_thread: verified/created thread %s", self._thread_id)
        return self._thread_id


    async def add_user_message(self, content: str, *, name: Optional[str] = None) -> None:
        await self._add_message("user", content, name=name)

    async def add_assistant_message(self, content: str, *, name: Optional[str] = None) -> None:
        await self._add_message("assistant", content, name=name)

    async def add_system_message(self, content: str, *, name: Optional[str] = None) -> None:
        await self._add_message("system", content, name=name)

    async def _add_message(self, role: str, content: str, *, name: Optional[str] = None) -> None:
        # Local-Threads: nichts senden
        if self._is_local():
            return

        # Inhalt prüfen/trimmen
        if not isinstance(content, str):
            content = str(content)
        content = content.strip()
        if not content:
            return

        # Payload als Dict (SDK-agnostisch)
        msg = {"role": str(role), "content": content}
        if name:
            msg["name"] = name

        # Kein Preflight: direkt senden, bei 404 genau 1x reparieren
        for attempt in (1, 2):
            thread_id = await self.ensure_thread(force_check=(attempt == 2))
            try:
                # {}-Style wie im Rest deines Logs
                logger.debug("add_message: using thread_id={} (cached={})", thread_id, self._thread_id)
                await self._client.thread.add_messages(thread_id=thread_id, messages=[msg])
                return
            except ApiError as e:
                status = getattr(e, "status_code", None)
                body = (getattr(e, "body", "") or "").lower()
                if attempt == 1 and (status == 404 or "not found" in body):
                    logger.warning("add_message: 404 on {}, resetting cached id and retrying", thread_id)
                    self._thread_id = None  # erzwingt Neuermittlung im 2. Versuch
                    continue
                raise

    async def list_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self._thread_id or self._is_local():
            return []
        try:
            resp = await self._client.thread.get(thread_id=self._thread_id)
            raw = getattr(resp, "messages", None) or []
            out: List[Dict[str, Any]] = []
            for m in raw[-limit:]:
                if isinstance(m, dict):
                    role = m.get("role") or ""
                    content = m.get("content") or ""
                    ts = m.get("created_at") or m.get("ts")
                else:
                    role = getattr(m, "role", "") or getattr(m, "type", "")
                    content = getattr(m, "content", "") or getattr(m, "text", "")
                    ts = getattr(m, "created_at", None)
                if not content:
                    continue
                out.append({"role": str(role), "content": str(content), "ts": ts})
            return out
        except Exception:
            return []

    async def search_text(
        self,
        query: str,
        *,
        limit: int = 5,
        roles: Optional[List[str]] = None,
        exclude_notes: bool = False,
        dedupe: bool = True,
        max_scan: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Einfache Thread-Volltextsucht:
        - Holt die letzten `max_scan` Nachrichten des Threads
        - Filtert NEUESTE → ÄLTERE nach `query`
        - Optional: Rollenfilter, „Merke:“ ausblenden, Dedupe
        Rückgabe: [{\"role\",\"content\",\"ts\"}, ...]
        """
        if not self._thread_id or self._is_local():
           return []
        qcf = (query or "").strip().casefold()
        try:
            resp = await self._client.thread.get(thread_id=self._thread_id)
            raw = getattr(resp, "messages", None) or []
        except Exception:
            raw = []

        msgs = raw[-max_scan:] if max_scan else raw
        want_roles: Optional[Set[str]] = {r.lower() for r in roles} if roles else None
        results: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for m in reversed(msgs):  # neueste → ältere
            if isinstance(m, dict):
                role = str(m.get("role") or "")
                text = str(m.get("content") or "")
                ts = m.get("created_at") or m.get("ts")
            else:
                role = str(getattr(m, "role", "") or getattr(m, "type", ""))
                text = str(getattr(m, "content", "") or getattr(m, "text", ""))
                ts = getattr(m, "created_at", None)
            if not text:
                continue
            if want_roles and role.lower() not in want_roles:
                continue
            if exclude_notes and text.strip().lower().startswith("merke:"):
                continue
            if qcf and qcf not in text.casefold():
                continue
            key = text.strip().casefold()
            if dedupe and key in seen:
                continue
            seen.add(key)
            results.append({"role": role or "user", "content": text, "ts": ts})
            if len(results) >= limit:
                break
        return results

    async def get_user_context(self, mode: Optional[str] = None) -> str:
        if not self._thread_id or self._is_local():
            return ""
        try:
            ctx = await self._client.thread.get_user_context(
                thread_id=self._thread_id, mode=mode or self._default_context_mode
            )
            return str(getattr(ctx, "context", "") or "")
        except Exception:
            return ""

    async def build_context_block(self, *, include_recent: bool = True, recent_limit: int = 10) -> str:
        parts: List[str] = []
        ctx = await self.get_user_context()
        if ctx:
            parts.append(f"Memory context: {ctx}")
        if include_recent:
            recent = await self.list_recent_messages(limit=recent_limit)
            if recent:
                lines: List[str] = []
                for m in recent:
                    role = (m.get("role") or "").strip() if isinstance(m, dict) else ""
                    content = (m.get("content") or "").strip() if isinstance(m, dict) else ""
                    if not content:
                        continue
                    content = str(content).strip()
                    if len(content) > 2000:
                        content = content[:2000] + " …"
                    lines.append(f"{role}: {content}")
                if lines:
                    parts.append("Recent conversation:\n" + "\n".join(lines))
        return "\n\n".join(parts)
