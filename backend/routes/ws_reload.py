# ws_reload.py
import os
import time

import logging
from flask import Flask
from flask_sock import Sock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ✅ Eigenen Logger für Watchdog initialisieren
watchdog_log_path = os.path.join("history", "logs", "watchdog.log")
os.makedirs(os.path.dirname(watchdog_log_path), exist_ok=True)

watchdog_handler = logging.FileHandler(watchdog_log_path, encoding="utf-8")
watchdog_formatter = logging.Formatter('%(asctime)s [WATCHDOG] %(message)s')
watchdog_handler.setFormatter(watchdog_formatter)

logger = logging.getLogger("watchdog_logger")
logger.setLevel(logging.INFO)
logger.addHandler(watchdog_handler)
logger.propagate = False

# 🔧 Flask + WebSocket
sock = Sock()
clients = []
@sock.route('/ws/reload')
def reload_socket(ws):
    clients.append(ws)
    logger.info("🔌 Client verbunden")
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
    except:
        pass
    finally:
        clients.remove(ws)
        logger.info("❌ Client getrennt")

def broadcast_reload():
    for ws in clients:
        try:
            ws.send("reload")
        except:
            pass

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        path = str(event.src_path)
        if path.endswith(("server.log", "watchdog.log")):
            return
        logger.info(f"📦 Änderung erkannt: {path}")
        broadcast_reload()


def start_watcher(path="web_dashboard/static"):
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ws_chat.py
from flask_sock import Sock

sock = Sock()
chat_clients = []

@sock.route('/ws/conference')
def conference_socket(ws):
    chat_clients.append(ws)
    try:
        while True:
            data = ws.receive()  # Client kann optional was senden (z.B. "ping")
            if data is None:
                break
    finally:
        chat_clients.remove(ws)

def broadcast_chat_message(msg):
    for ws in chat_clients:
        try:
            ws.send(msg)
        except:
            pass
