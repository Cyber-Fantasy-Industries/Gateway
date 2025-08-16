# backend/chat.py
import asyncio, os, io, sys
from typing import List, Dict, Any
import httpx
from loguru import logger

def _wrap_utf8(stream):
    try:
        enc = getattr(stream, "encoding", None)
        if isinstance(stream, io.TextIOBase) and (enc or "").lower() == "utf-8":
            return stream
        buf = getattr(stream, "buffer", None)
        if buf is not None:
            return io.TextIOWrapper(buf, encoding="utf-8", errors="replace")
    except Exception:
        pass
    return stream

sys.stdout = _wrap_utf8(sys.stdout)
sys.stderr = _wrap_utf8(sys.stderr)

ENV_URL = os.getenv("GATEWAY_API_URL")
CANDIDATES: List[str] = [
    "http://gateway:8080/api/chat",
    "http://gateway-container:8080/api/chat",
    "http://127.0.0.1:8080/api/chat",
]

async def resolve_api(client: httpx.AsyncClient) -> str:
    if ENV_URL:
        logger.debug("CLI: using ENV GATEWAY_API_URL={}", ENV_URL)
        return ENV_URL.rstrip("/")
    for url in CANDIDATES:
        try:
            logger.debug("CLI: probing {} …", url)
            r = await client.post(url, json={})
            if r.status_code in (200, 400, 422):
                logger.info("CLI: connected to {}", url)
                return url.rstrip("/")
            logger.debug("CLI: probe {} -> HTTP {}", url, r.status_code)
        except Exception as e:
            logger.debug("CLI: probe error for {}: {}", url, e)
    raise RuntimeError("Kein API-Endpunkt erreichbar. Setze GATEWAY_API_URL (z. B. http://gateway:8080/api/chat).")

BANNER = """\
=== GroupChat CLI (Server-Modus) ===
Prompt eingeben. 'exit' zum Beenden.
Tippe 'health' (oder 'hc') für einen ZEP-Healthcheck.
"""

VERBOSE = False

def _coerce_dict(x: Any) -> Dict[str, Any]:
    """Immer ein Dict liefern, egal ob JSON dict/list/primitive/String."""
    if isinstance(x, dict):
        return x
    if isinstance(x, list):
        return {"items": x}
    return {"detail": str(x)}

def _safe_json(resp: httpx.Response) -> Dict[str, Any]:
    """HTTPX-Response sicher in Dict verwandeln (fällt auf Text zurück)."""
    try:
        return _coerce_dict(resp.json())
    except Exception:
        return {"raw": resp.text}
    
def _print_steps(steps: list[dict]) -> None:
    if not isinstance(steps, list):
        print("[steps] <invalid>")
        return
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict):
            print(f"[step {i}] {s!r}")
            continue
        t = s.get("type", "?")
        # generische Felder, falls kein spezielles Format
        note = s.get("note") or s.get("message") or s.get("text") or s.get("content") or ""
        if note:
            print(f"[step {i}] {t}: {note}")
        else:
            # Notfall: rohes Dict anzeigen, damit nichts „verschwindet“
            print(f"[step {i}] {t}: {s}")


async def run_cli() -> None:
    global VERBOSE
    print(BANNER)

    async with httpx.AsyncClient(timeout=60) as client:
        # 1) API ermitteln
        try:
            api_url = await resolve_api(client)
            print(f"(verbunden mit {api_url})")
        except Exception as e:
            print(f"[Error] {e}")
            return

        # 2) Helpers, die api_url/client nutzen
        def _api_base_from_chat(chat_url: str) -> str:
            url = chat_url.rstrip("/")
            return url[:-5] if url.endswith("/chat") else url

        async def _do_healthcheck() -> None:
            api_base = _api_base_from_chat(api_url)
            url_candidates = [f"{api_base}/health/zep", f"{api_base}/api/health/zep"]
            hit = None
            for url in url_candidates:
                try:
                    r = await client.get(url)
                    hit = (url, r)
                    break
                except Exception:
                    continue
            if not hit:
                print("[Health] Error – no health endpoint reachable")
                return
            url, r = hit
            data = _safe_json(r)
            if r.status_code == 200:
                thread = data.get("thread") or data.get("thread_id")
                user = data.get("user") or data.get("user_id")
                extra = f" – Thread: {thread}" if thread else (f" – User: {user}" if user else "")
                print(f"[Health] OK{extra}")
            elif r.status_code == 503:
                detail = data.get("detail") or "Service unavailable"
                print(f"[Health] 503 – {detail}")
            else:
                print(f"[Health] HTTP {r.status_code} – {data}")

        async def _do_diag() -> None:
            api_base = _api_base_from_chat(api_url)
            for url in (f"{api_base}/chat/_diag", f"{api_base}/api/chat/_diag"):
                try:
                    r = await client.get(url)
                    if r.status_code == 200:
                        print("[Diag]", _safe_json(r))
                        return
                except Exception:
                    pass
            print("[Diag] Unreachable")

        async def _do_deep() -> None:
            api_base = _api_base_from_chat(api_url)
            url_candidates = [f"{api_base}/health/zep/deep", f"{api_base}/api/health/zep/deep"]
            for url in url_candidates:
                try:
                    r = await client.get(url)
                    data = _safe_json(r)
                    if r.status_code == 200:
                        print("[Deep] ok")
                        env = _coerce_dict(data.get("env"))
                        probes = data.get("probes") or []
                        print("  base_url:", env.get("base_url_repr"))
                        for p in probes:
                            p = _coerce_dict(p)
                            status = p.get("status") or p.get("error")
                            print(f"  {p.get('method')} {p.get('url')} -> {status}")
                        return
                    else:
                        print(f"[Deep] HTTP {r.status_code} – {data}")
                        return
                except Exception:
                    continue
            print("[Deep] Unreachable")

        async def _do_ping() -> None:
            api_base = _api_base_from_chat(api_url)
            for url in (f"{api_base}/ping", f"{api_base}/api/ping"):
                try:
                    r = await client.get(url)
                    data = _safe_json(r)
                    if r.status_code == 200 and data.get("ok"):
                        print(f"[Ping] ok – trace_id: {data.get('trace_id')} thread: {data.get('thread_id')}")
                        return
                    else:
                        print(f"[Ping] HTTP {r.status_code} – {data}")
                        return
                except Exception:
                    continue
            print("[Ping] Unreachable")

        # 3) Autorun + Prompt-Loop (bleibt IM with-Block, damit client offen bleibt)
        await _do_diag()
        await _do_healthcheck()
        await _do_deep()

        while True:
            try:
                user_text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not user_text:
                continue
            cmd = user_text.lower()

            if cmd in {"exit", "quit"}:
                print("Bye!")
                break
            if cmd in {"health", "/health", ":health", "hc"}:
                await _do_healthcheck(); continue
            if cmd in {"diag", ":diag"}:
                await _do_diag(); continue
            if cmd in {"ping"}:
                await _do_ping(); continue
            if cmd in {"v", ":v", "verbose"}:
                VERBOSE = not VERBOSE
                print(f"[Verbose] {'on' if VERBOSE else 'off'}"); continue

            try:
                dry_req = False
                if user_text.lower().startswith("dry "):
                    dry_req = True
                    user_text = user_text[4:].lstrip()

                r = await client.post(api_url + ("?dry=true" if dry_req else ""), json={"prompt": user_text})
                if VERBOSE:
                    print("[HTTP]", r.status_code, dict(r.headers))
                r.raise_for_status()

                data: Dict[str, Any] = _safe_json(r)
                trace = data.get("trace_id")
                if trace:
                    print(f"[trace_id] {trace}")

                steps = data.get("steps") or []
                reply_text = str(data.get("reply", "") or "").strip()

                # erst Steps (falls vorhanden) …
                if steps:
                    _print_steps(steps)

                # … dann IMMER die Antwort zeigen, wenn vorhanden
                if reply_text:
                    print("\n[Assistant]")
                    print(reply_text.encode("utf-8", "replace").decode("utf-8", "replace"))
                    print()
                elif not steps:
                    # gar nichts da? kurze Diagnose ausgeben
                    print("\n[Assistant]")
                    print("(keine Antwort erhalten – roher Payload unten)")
                    print(repr(data))
                    print()


            except httpx.HTTPStatusError as he:
                j = _safe_json(he.response)
                print(f"[HTTP {he.response.status_code}]")
                detail = j.get("detail")
                if not isinstance(detail, dict):
                    detail = j
                if isinstance(detail, dict):
                    if "trace_id" in detail:
                        print("  trace_id:", detail["trace_id"])
                    if "status" in detail:
                        print("  zep_status:", detail["status"])
                    if "body" in detail:
                        print("  zep_body:", repr(detail["body"]))
                else:
                    print(detail)
                if VERBOSE:
                    print("  headers:", dict(he.response.headers))
            except Exception as e:
                print(f"[Error] {e}")


if __name__ == "__main__":
    asyncio.run(run_cli())
