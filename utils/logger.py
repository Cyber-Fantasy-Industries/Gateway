import os
import logging
from queue import Queue

gui_log_queue = Queue()
error_output_box = None

import logging

logger = logging.getLogger("gateway")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def setup_file_logger(log_path="logs/server.log"):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s [SERVER] %(message)s')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    log_to_gui("🚀 Logging gestartet.")

def log_to_gui(message):
    logging.info(message)
    gui_log_queue.put(message)

# def log_to_error(message):
#     logging.warning(message)
#     if error_output_box:
#         error_output_box.insert(tk.END, message + "\n")
#         error_output_box.see(tk.END)
#     else:
#         gui_log_queue.put("[ERROR] " + message)

def set_error_output_box(box):
    global error_output_box
    error_output_box = box

# def poll_log_queue(output_box, window):
#     try:
#         while not gui_log_queue.empty():
#             msg = gui_log_queue.get_nowait()
#             if msg:
#                 output_box.insert(tk.END, msg + "\n")
#                 output_box.see(tk.END)
#     except Exception as e:
#         output_box.insert(tk.END, f"[Fehler] {e}\n")
#         output_box.see(tk.END)
#     window.after(500, poll_log_queue, output_box, window)
