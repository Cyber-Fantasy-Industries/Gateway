import os, json
from datetime import datetime
import uuid

CONFERENCE_DIR = os.path.join("ui", "history", "conferences")

def save(history_list, metadata=None):
    """
    Speichert einen vollständigen Konferenzverlauf inkl. optionaler Metadaten.
    Gibt den Pfad der gespeicherten Datei zurück.
    """
    if not history_list:
        return None

    os.makedirs(CONFERENCE_DIR, exist_ok=True)

    session_id = uuid.uuid4().hex[:8]  # kurze eindeutige ID
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{ts}_{session_id}.json"
    path = os.path.join(CONFERENCE_DIR, filename)

    data = {
        "session_id": session_id,
        "timestamp": ts,
        "messages": history_list,
    }

    if metadata:
        data["metadata"] = metadata

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path
