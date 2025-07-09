import os, sys
#print("WORKING DIRECTORY:", os.getcwd())
#print("SYS.PATH:", sys.path)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# ui/app.pyw

from utils.logger import setup_file_logger, log_to_gui, log_to_error, poll_log_queue, set_error_output_box
from utils import docker_control as docker
from tkinter import scrolledtext
import tkinter as tk
import threading


def create_main_window():
    window = tk.Tk()
    window.title("Workforce Manager – Docker Dev Control")
    window.geometry("1400x700")
    return window

def create_labels(window):
    notice = tk.Label(window, text="⚠️ Container will NOT close if you close this window!", fg="#FF0000", font=("Courier New", 10))
    build_label = tk.Label(window, text="", fg="#00FF00", font=("Courier New", 10))
    status_label = tk.Label(window, text="", fg="#00FF00", font=("Courier New", 11, "bold"))
    return notice, build_label, status_label

def create_output_box(window):
    output_box = scrolledtext.ScrolledText(
        window,
        wrap=tk.WORD,
        height=15,
        bg="black",
        fg="#00FF00",
        insertbackground="#00FF00",
        font=("Courier New", 10)
    )
    output_box.tag_config("bold", font=("Courier", 10, "bold"))
    return output_box

def create_error_box(window):
    error_box = scrolledtext.ScrolledText(
        window,
        wrap=tk.WORD,
        height=10,
        bg="black",
        fg="#FF5555",
        insertbackground="#FF5555",
        font=("Courier New", 10)
    )
    error_box.insert(tk.END, "[Docker]:\n")
    return error_box

def run(job):
    threading.Thread(target=job, daemon=True).start()

def create_buttons(frame, update_status, controls, build_label, status_label, run, log_error):
    buttons = [
        ("🔨 Build Image", lambda: run(docker.build_image(build_label, status_label, controls))),
        ("♻️ Rebuild Image", lambda: run(docker.rebuild_image(build_label, status_label, controls))),
        (
            "▶️ Start Container",
            #lambda: run(docker.start_container(build_label, status_label, controls, log_error))
            lambda: [
                    run(docker.start_container(build_label, status_label, controls, log_error)),
                    run(docker.stream_container_logs(log_error))
                ]
        ),
        (
            "🔁 Restart Container",
            lambda: run(docker.restart_container(build_label, status_label, controls, log_error))
        ),
        (
            "⏹ Shutdown Container",
            lambda: run(docker.shutdown_container(build_label, status_label, controls, log_error))
        ),
        ("🗑 Delete Container",
            lambda: run(docker.delete_container(build_label, status_label, controls, log_error))),

        ("🌐 Open UI", docker.open_ui),
    ]

    for text, cmd in buttons:
        btn = tk.Button(
            frame,
            text=text,
            width=20,
            command=cmd,
            fg="#00FF00",
            bg="black",
            activeforeground="black",
            activebackground="#00FF00",
            font=("Courier New", 10)
        )
        btn.pack(side=tk.LEFT, padx=5)
        if "Build Image" in text:
            controls["build"] = btn
        else:
            controls["others"].append(btn)


def monitor_container_status(status_label, window):
    running = docker.container_running()
    if running:
        current_color = status_label.cget("fg")
        new_color = "green" if current_color != "green" else "#00FF00"
        status_label.config(fg=new_color)
    else:
        status_label.config(text="🔴 Kein Container vorhanden", fg="red")
    window.after(2000, lambda: monitor_container_status(status_label, window))


def launch_gui():
    global window, output_box, error_output_box, build_label, status_label, controls
    window = create_main_window()
    notice, build_label, status_label = create_labels(window)
    notice.pack(pady=5)
    build_label.pack()
    status_label.pack()

    controls = {"build": None, "others": []}
    button_frame = tk.Frame(window)
    button_frame.pack(pady=10)
    create_buttons(button_frame, docker.update_status, controls, build_label, status_label, run, log_to_error)


    # Frame für die beiden Boxen nebeneinander
    log_frame = tk.Frame(window)
    log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Output Box (links)
    output_box = create_output_box(log_frame)
    output_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Error Box (rechts)
    error_output_box = create_error_box(log_frame)
    error_output_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    set_error_output_box(error_output_box)
    setup_file_logger()
    docker.update_status(build_label, status_label, controls)
    poll_log_queue(output_box, window)
    monitor_container_status(status_label, window)
    def on_close():
        log_to_gui("⏹ Beende GUI...")
        try:
            if docker.container_running():
                log_to_gui("⏹ Stoppe laufenden Container...")
                
        except Exception as e:
            log_to_gui(f"⚠️ Fehler beim Stoppen: {e}")
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_close)

    #monitor_container_status()
    window.mainloop()

if __name__ == "__main__":
    launch_gui()
    

 
