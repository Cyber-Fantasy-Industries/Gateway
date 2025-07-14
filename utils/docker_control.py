# import os
# import subprocess
# import threading
# import time
# import webbrowser
# import socket

# from utils.logger import log_to_gui

# IMAGE_NAME = "gateway"
# CONTAINER_NAME = "gateway-container"
# PORT = "5000"
# creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# def container_running():
#     out, err = run_cmd(f"docker ps -q -f name=^{CONTAINER_NAME}$")
#     return bool(out.strip())

# def run_cmd(cmd):
#     try:
#         result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
#         return (result.stdout or '').strip(), (result.stderr or '').strip()
#     except Exception as e:
#         return "", str(e)

# def run_cmd_live(cmd, callback):
#     process = subprocess.Popen(
#         cmd,
#         shell=True,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#         encoding='utf-8',
#         errors='replace',
#         bufsize=1,
#         creationflags=creationflags
#     )
#     if process.stdout:
#         for line in process.stdout:
#             callback(line.strip())

# def build_image(build_label, status_label, controls):
#     def job():
#         log_to_gui("🔨 Baue Docker-Image...")
#         update_status(build_label, status_label, controls, building=True)
#         run_cmd_live("docker build -t gateway .", log_to_gui)
#         update_status(build_label, status_label, controls)
#     return job

# def rebuild_image(build_label, status_label, controls):
#     def job():
#         log_to_gui("♻️ Entferne altes Image & Container...")
#         update_status(build_label, status_label, controls, building=True)
#         run_cmd_live(f"docker rm -f {CONTAINER_NAME}", log_to_gui)
#         run_cmd_live(f"docker rmi -f {IMAGE_NAME}", log_to_gui)
#         log_to_gui("🔨 Baue Docker-Image...")
#         run_cmd_live("docker build -t gateway .", log_to_gui)
#         update_status(build_label, status_label, controls)
#     return job

# def start_container(build_label, status_label, controls, log_error):
#     def job():
#         # Status abfragen
#         out, err = run_cmd("docker ps -a --filter name=gateway-container --format '{{.Status}}'")
#         status = out.strip()

#         if not status:
#             log_to_gui("🚀 Container wird neu erstellt...")
#         elif "Exited" in status:
#             log_to_gui("▶️ Container wird neu gestartet...")
#         elif "Up" in status:
#             log_to_gui("ℹ️ Container läuft bereits.")
#         else:
#             log_to_gui("ℹ️ Unbekannter Container-Status: " + status)

#         # Detached starten
#         run_cmd_live("docker-compose up -d", log_to_gui)

#         time.sleep(2)

#         if container_running():
#             if is_port_open("localhost", PORT):
#                 log_to_gui("✅ Flask-Server läuft und ist erreichbar.")
#             else:
#                 log_to_gui("⚠️ Flask-Server scheint nicht zu laufen (Port 5000 nicht aktiv).")
#         else:
#             log_to_gui("⚠️ Container läuft nicht. Zeige letzte Logs...")
#             #show_logs(log_error)

#         update_status(build_label, status_label, controls)

#         # KEIN run() hier!
#     return job



# def restart_container(build_label, status_label, controls, log_error):
#     def job():
#         log_to_gui("🔁 Starte Container neu via docker-compose...")
#         update_status(build_label, status_label, controls, restarting=True)

#         # Check, ob der Container überhaupt existiert
#         out, err = run_cmd("docker ps -a --filter name=gateway-container --format '{{.Status}}'")
#         status = out.strip()

#         if not status:
#             log_to_gui("ℹ️ Kein bestehender Container gefunden. Erstelle neuen Container...")
#             run_cmd_live("docker-compose up", log_to_gui)
#         else:
#             log_to_gui("🧹 Container wird neugestartet...")
#             run_cmd_live("docker-compose restart", log_to_gui)

#         time.sleep(2)

#         if container_running():
#             log_to_gui("✅ Container läuft nach Neustart.")
#         else:
#             log_to_gui("⚠️ Container läuft nicht nach Neustart.")

#         update_status(build_label, status_label, controls)
#     return job


# def shutdown_container(build_label, status_label, controls, log_error):
#     def job():
#         log_to_gui("⏹ Stoppe Container via docker-compose...")
#         update_status(build_label, status_label, controls, shutting_down=True)
#         run_cmd_live("docker-compose down", log_to_gui)
#         time.sleep(1)
#         update_status(build_label, status_label, controls)
#     return job

# def delete_container(build_label, status_label, controls, log_error):
#     def job():
#         log_to_gui("🗑 Entferne Container und Image...")
#         update_status(build_label, status_label, controls, shutting_down=True)

#         # Stoppen, falls läuft
#         run_cmd_live(f"docker stop {CONTAINER_NAME}", log_to_gui)

#         # Löschen
#         run_cmd_live(f"docker rm {CONTAINER_NAME}", log_to_gui)

#         # Image löschen
#         run_cmd_live(f"docker rmi {IMAGE_NAME}", log_to_gui)

#         update_status(build_label, status_label, controls)
#         log_to_gui("✅ Container und Image wurden entfernt.")
#     return job

# def stream_container_logs(log_error):
#     def job():
#         try:
#             process = subprocess.Popen(
#                 ["docker", "logs", "-f", CONTAINER_NAME],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.STDOUT,
#                 text=True,
#                 encoding='utf-8',
#                 errors='replace',
#                 bufsize=1,
#                 creationflags=creationflags
#             )
#             if process.stdout:
#                 for line in process.stdout:
#                     if line:
#                         log_error(f"[Docker] {line.strip()}")
#         except Exception as e:
#             log_error(f"❌ Fehler beim Logstream: {str(e)}")
#     return job

# def is_port_open(host, port):
#     try:
#         with socket.create_connection((host, port), timeout=2):
#             return True
#     except OSError:
#         return False

# def open_ui():
#     webbrowser.open(f"http://localhost:{PORT}")

# def image_exists():
#     result = subprocess.run("docker images -q gateway", shell=True, capture_output=True, text=True)
#     return bool(result.stdout.strip())

# def container_exists():
#     result = subprocess.run(f"docker ps -a -q -f name=^{CONTAINER_NAME}$", shell=True, capture_output=True, text=True)
#     return bool(result.stdout.strip())

# def update_status(build_label, status_label, controls, building=False, restarting=False, shutting_down=False):
#     img_exists = image_exists()
#     ctr_exists = container_exists()
#     ctr_running = container_running()
#     from utils import docker_control as docker
#     print(docker.container_running())
#     print(docker.container_exists())

#     # 🔧 Build-Statusanzeige
#     if building:
#         build_label.config(text="🛠 Build wird erstellt...", fg="blue")
#     elif img_exists:
#         build_label.config(text="🟢 Build vorhanden", fg="green")
#     else:
#         build_label.config(text="🔴 Kein Build vorhanden", fg="red")

#     # 🟡 Container-Statusanzeige
#     if restarting:
#         status_label.config(text="🟡 Container wird neugestartet...", fg="orange")
#     elif shutting_down:
#         status_label.config(text="🟡 Container wird gestoppt...", fg="orange")
#     elif ctr_running:
#         status_label.config(text="🟢 Container läuft", fg="green")
#     elif ctr_exists:
#         status_label.config(text="🟡 Container gestoppt", fg="orange")
#     else:
#         status_label.config(text="🔴 Kein Container vorhanden", fg="red")

#     if controls.get("build"):
#         set_button_state(controls["build"], enabled=not img_exists, color="green")

#     if controls.get("others"):
#         for btn in controls["others"]:
#             text = btn.cget("text")

#             if not img_exists:
#                 set_button_state(btn, enabled=False)
#             else:
#                 if text == "▶️ Start Container":
#                     set_button_state(btn, enabled=img_exists and not ctr_running, color="green")
#                 elif text == "🔁 Restart Container":
#                     set_button_state(btn, enabled=ctr_running, color="orange")
#                 elif text == "⏹ Shutdown Container":
#                     set_button_state(btn, enabled=ctr_running, color="red")
#                 elif text == "🌐 Open UI":
#                     set_button_state(btn, enabled=ctr_running, color="green")
#                 elif text == "♻️ Rebuild Image":
#                     set_button_state(btn, enabled=img_exists, color="blue")
#                 else:
#                     set_button_state(btn, enabled=True)



# def set_button_state(button, enabled, color=None):
#     button.config(state=tk.NORMAL if enabled else tk.DISABLED)
#     if enabled and color:
#         button.config(bg=color, fg="white", activebackground=color)
#     else:
#         button.config(bg="SystemButtonFace", fg="black")