#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway Docker-Dev CLI (slim)
- Full Rebuild (+wipe)
- Start / Stop
- Enter running container shell (docker exec)
- Debug (DNS + Health)
- Compact Docker status overview

Notes:
- Works with both `docker-compose` and `docker compose`.
- Service/Container names assumed: `gateway` / `gateway-container`.
"""

import os
import platform
import subprocess
import time
from shutil import which
import traceback
import re
from pathlib import Path


COMPOSE_FILE = "docker-compose.yml"
SERVICE_NAME = "gateway"
CONTAINER_NAME = "gateway-container"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

ENV_FILE = Path(".env")  # Compose liest diese Datei automatisch, wenn vorhanden
SERVICE_NAME = "gateway"  # du nutzt das bereits – falls anders, hier anpassen

def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data

def _write_env_file_var(path: Path, key: str, value: str) -> None:
    """Setzt/aktualisiert KEY=VALUE in .env (idempotent)."""
    lines = []
    found = False
    if path.exists():
        for line in path.read_text().splitlines():
            if re.match(rf"^\s*{re.escape(key)}\s*=", line):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")

def set_openai_key_interactive():
    print("Bitte neuen OPENAI_API_KEY eingeben (wird in .env persistiert):")
    try:
        new_key = input("OPENAI_API_KEY = ").strip()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        return
    if not new_key or not new_key.startswith("sk-"):
        print("Ungültig oder leer – keine Änderung.")
        return

    # 1) In Prozess-Env setzen (damit docker compose den Wert sieht)
    os.environ["OPENAI_API_KEY"] = new_key

    # 2) .env persistent aktualisieren (damit Folge-Starts den Key haben)
    _write_env_file_var(ENV_FILE, "OPENAI_API_KEY", new_key)
    print(f"Gesetzt. (.env aktualisiert, Länge={len(new_key)})")

def restart_gateway(force_recreate: bool = True):
    compose = _compose_bin()
    args = [*compose.split(), "up", "-d"]
    if force_recreate:
        args.append("--force-recreate")
    args.append(SERVICE_NAME)
    print("Recreating gateway mit aktuellem Env …")
    _run(args, check=True)
    print("Done.")


def _is_windows() -> bool:
    return os.name == "nt" or platform.system().lower().startswith("win")


def _compose_bin() -> str:
    # Prefer docker-compose if available, else fallback to docker compose
    if which("docker-compose"):
        return "docker-compose"
    return "docker compose"


def _run(cmd, check: bool = False, capture: bool = False, echo: bool = True):
    display = " ".join(cmd) if isinstance(cmd, list) else cmd
    if echo:
        print(f"$ {display}")
    if capture:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    return subprocess.run(cmd, check=check)


def _to_text(s) -> str:
    if s is None:
        return ""
    if isinstance(s, (bytes, bytearray)):
        try:
            return s.decode()
        except Exception:
            return s.decode(errors="ignore")
    return str(s)

# -----------------------------------------------------------------------------
# Core actions
# -----------------------------------------------------------------------------

def open_logs_window():
    """Open a live logs window for the gateway service."""
    compose = _compose_bin()
    if _is_windows():
        os.system(f'start cmd /k "{compose} logs -f {SERVICE_NAME}"')
    else:
        subprocess.Popen(["bash", "-lc", f"{compose} logs -f {SERVICE_NAME}"])


def enter_container_shell():
    """Open an interactive shell in the running server container (no new run-container)."""
    cmd = f"docker exec -it {CONTAINER_NAME} bash"
    if _is_windows():
        os.system(f'start cmd /k "{cmd}"')
    else:
        subprocess.call(["bash", "-lc", cmd])


def quick_start():
    compose = _compose_bin()
    print("Starting System…")
    _run([*compose.split(), "up", "-d"], check=True)
    time.sleep(2)
    open_logs_window()
    enter_container_shell()
    print("System Started.")


def stop_container():
    compose = _compose_bin()
    print("Stopping System…")
    _run([*compose.split(), "stop", SERVICE_NAME], check=False)
    print("Stopped.")


def wipe_all():
    """Aggressive wipe: down (images, volumes, orphans) + prune + legacy network cleanup."""
    compose = _compose_bin()
    print("Deleting Gateway...")
    # Compose down incl. images, volumes, orphans (ok if already down)
    _run([*compose.split(), "down", "--rmi", "all", "-v", "--remove-orphans"], check=False)
    # Remove possible legacy/default networks (ignore errors if not present)
    _run(["docker", "network", "rm", "gateway_default"], check=False)
    _run(["docker", "network", "rm", "gateway-net"], check=False)
    # Reclaim space aggressively
    _run(["docker", "system", "prune", "-af"], check=True)
    print("Wipe complete.")


def rebuild_image():
    compose = _compose_bin()
    print("Rebuilding Image (no cache)…")
    _run([*compose.split(), "build", "--no-cache", SERVICE_NAME], check=True)
    print("Build complete.")


def full_rebuild():
    """Full rebuild: wipe (down, images, prune) then build & up fresh."""
    compose = _compose_bin()
    print("[Full Rebuild] Wipe …")
    wipe_all()
    print("[Full Rebuild] Build --no-cache …")
    _run([*compose.split(), "build", "--no-cache", SERVICE_NAME], check=True)
    print("[Full Rebuild] Up -d …")
    _run([*compose.split(), "up", "-d"], check=True)
    time.sleep(2)
    open_logs_window()
    enter_container_shell()
    print("[Full Rebuild] Done.")


def _has_any(cmd) -> bool:
    r = _run(cmd, check=False, capture=True, echo=False)
    out = _to_text(getattr(r, "stdout", "")).strip()
    return bool(out)


def print_docker_overview():
    compose = _compose_bin()
    print("══════════════════════════════════════════════")
    print(" 🖥️  [Docker System Status]")
    print("══════════════════════════════════════════════")

    # Images
    try:
        print("  📦 Docker Images:")
        if _has_any(["docker", "images", "-q"]):
            r = _run([
                "docker", "images", "--format",
                "table {{.Repository}}:{{.Tag}}	{{.ID}}	{{.Size}}"
            ], capture=True, echo=False)
            out = _to_text(getattr(r, "stdout", "")).strip() or "<none>"
            print("" + out)
        else:
            print("  <keine Images gefunden>")
    except Exception:
        print("  (Fehler beim Abrufen der Images)")

    # Container
    try:
        print("  🚢 Docker Container:")
        if _has_any(["docker", "ps", "-a", "-q"]):
            r = _run([
                "docker", "ps", "-a", "--format",
                "table {{.ID}}	{{.Names}}	{{.Status}}	{{.Image}}	{{.Command}}	{{.RunningFor}}	{{.Ports}}"
            ], capture=True, echo=False)
            out = _to_text(getattr(r, "stdout", "")).strip() or "<none>"
            print("" + out)
        else:
            print("  <keine Container gefunden>")
    except Exception:
        print("  (Fehler beim Abrufen der Container)")

    # Compose Services
    try:
        print("  🧩 Compose Services:")
        r = _run([*compose.split(), "ps"], capture=True, echo=False)
        out = _to_text(getattr(r, "stdout", "")).strip() or "<none>"
        print("" + out)
    except Exception:
        print("  (Fehler beim Abrufen der Compose-Services)")


# -----------------------------------------------------------------------------
# Menu (reduced + debug)
# -----------------------------------------------------------------------------

def menu():
    while True:
        print("################################")
        print("### [Gateway Docker-Dev CLI] ###")
        print("################################")
        print_docker_overview()
        print("################################")
        print(" f: wipe/Rebuild")
        print(" a: Start Server")
        print(" s: Stop Server")
        print(" k: Set OPENAI_API_KEY (+persist to .env)")
        print(" r: Restart gateway (force-recreate)")
        print(" x: Exit")
        print("################################")
        choice = input("> ").strip().lower()
        try:
            if choice == "f":
                full_rebuild()
            elif choice == "a":
                quick_start()
            elif choice == "s":
                stop_container()
            elif choice == "k":
                set_openai_key_interactive()
            elif choice == "r":
                restart_gateway(force_recreate=True)
            elif choice in ("x", "q", "exit"):
                print("Bye.")
                break
            else:
                print("Unbekannte Option.")
        except KeyboardInterrupt:
            print("(Abgebrochen)")
        except subprocess.CalledProcessError as e:
            print(f"Fehler (exit {e.returncode}): {' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd}")
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("Bye.")