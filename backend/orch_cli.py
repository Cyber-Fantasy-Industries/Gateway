# backend/orch_cli.py
import os
import sys
import time
import json
import httpx
import argparse

BASE = os.getenv("ORCH_API_URL", "http://localhost:8080/api/orch")

def _root_base():
    if "/api/orch" in BASE:
        return BASE.split("/api/orch", 1)[0]
    return BASE.rsplit("/api", 1)[0] if "/api" in BASE else BASE

def _split_semis(s: str | None):
    if not s:
        return []
    return [x.strip() for x in s.split(";") if x.strip()]

# -------- Orchestrator REST --------
def start(goal, deliverables=None, constraints=None, nested=False):
    payload = {
        "goal": goal,
        "deliverables": deliverables or [],
        "constraints": constraints or [],
        "nested": nested,
    }
    r = httpx.post(f"{BASE}/start", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def status(run_id):
    r = httpx.get(f"{BASE}/status", params={"run_id": run_id}, timeout=30)
    r.raise_for_status()
    return r.json()

def diag():
    try:
        r = httpx.get(f"{BASE}/_diag", timeout=10)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[diag] error: {e}")

def health(deep=False):
    root = _root_base()
    url = f"{root}/api/health/zep/deep" if deep else f"{root}/api/health/zep"
    r = httpx.get(url, timeout=20 if deep else 10)
    r.raise_for_status()
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))

# -------- Chat via Orchestrator --------
def chat_once(text):
    r = httpx.post(f"{BASE}/chat", json={"text": text}, timeout=30)
    r.raise_for_status()
    return r.json()

def chat_loop():
    print("Orchestrator CLI (Chat-Modus). Tippe 'exit', 'diag', 'health', 'status <run_id>' oder Text. Für Orchestrierung: 'start <ziel>'.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not line:
            continue
        low = line.lower()

        if low in {"exit", "quit"}:
            print("Bye!"); break
        if low.startswith("health"):
            health(deep="--deep" in low); continue
        if low == "diag":
            diag(); continue
        if low.startswith("status "):
            rid = line.split(" ", 1)[1].strip()
            try:
                st = status(rid)
                print(json.dumps(st, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"[status] error: {e}")
            continue
        if low.startswith("start "):
            goal = line.split(" ", 1)[1].strip()
            s = start(goal, deliverables=[], constraints=[], nested=False)
            run_id = s.get("run_id"); print(f"[Orch] run_id={run_id}")
            print("[Orch] polling status... (Ctrl+C to stop)")
            try:
                while True:
                    time.sleep(2)
                    st = status(run_id)
                    print(json.dumps(st, ensure_ascii=False))
                    if st.get("result", {}).get("success") is True:
                        break
            except KeyboardInterrupt:
                print("Aborted by user.")
            except Exception as e:
                print(f"[Error] {e}")
            continue

        # Default: CHAT
        try:
            res = chat_once(line)
            reply = res.get("reply")
            if reply:
                print(reply)
            else:
                print(json.dumps(res, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[chat] error: {e}")

def interactive_start():
    # Chat ist der Default; Orchestrierung per 'start <ziel>'
    return chat_loop()

def main():
    parser = argparse.ArgumentParser(prog="orch_cli", description="Orchestrator CLI")
    sub = parser.add_subparsers(dest="cmd")

    # Start
    p_start = sub.add_parser("start", help="Orchestration starten")
    p_start.add_argument("goal", nargs="?", help="Zielbeschreibung (wenn fehlt, interaktiv)")
    p_start.add_argument("--nested", action="store_true")
    p_start.add_argument("--deliverables", help='Semikolon-getrennt, z.B. "a;b;c"')
    p_start.add_argument("--constraints", help='Semikolon-getrennt, z.B. "x;y"')

    # Status/Diag/Health
    p_status = sub.add_parser("status", help="Status eines Runs abfragen")
    p_status.add_argument("run_id")
    sub.add_parser("diag", help="Diagnose")
    p_health = sub.add_parser("health", help="ZEP-Health (optional --deep)")
    p_health.add_argument("--deep", action="store_true")

    # Chat
    p_chat = sub.add_parser("chat", help="Chatten über den Orchestrator (nutzt /api/orch/chat)")
    p_chat.add_argument("text", nargs="*", help="Nachricht (leer -> interaktiver Chat)")
    p_chat.add_argument("-l", "--loop", action="store_true", help="Chat-Loop starten")

    if len(sys.argv) == 1:
        return interactive_start()

    args = parser.parse_args()
    if args.cmd == "start":
        if not args.goal:
            return interactive_start()
        dels = _split_semis(args.deliverables or "")
        cons = _split_semis(args.constraints or "")
        print(f"[Orch] start: goal='{args.goal}' nested={args.nested}")
        s = start(args.goal, deliverables=dels, constraints=cons, nested=args.nested)
        run_id = s.get("run_id"); print(f"[Orch] run_id={run_id}")
        print("[Orch] polling status... (Ctrl+C to stop)")
        while True:
            time.sleep(2)
            try:
                st = status(run_id); print(json.dumps(st, ensure_ascii=False))
                if st.get("result", {}).get("success") is True:
                    break
            except KeyboardInterrupt:
                print("Aborted by user."); break
            except Exception as e:
                print(f"[Error] {e}"); break
    elif args.cmd == "status":
        st = status(args.run_id); print(json.dumps(st, ensure_ascii=False, indent=2))
    elif args.cmd == "diag":
        diag()
    elif args.cmd == "health":
        health(deep=getattr(args, "deep", False))
    elif args.cmd == "chat":
        if args.loop or not args.text:
            return chat_loop()
        res = chat_once(" ".join(args.text))
        print(res.get("reply") or json.dumps(res, ensure_ascii=False, indent=2))
    else:
        return interactive_start()

if __name__ == "__main__":
    main()