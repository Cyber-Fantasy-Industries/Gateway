import os
import subprocess
import traceback

COMPOSE_FILE = "docker-compose.yml"
CONTAINER_NAME = "gateway-container"

def build_image():
    print("\n🔨 Baue Image (docker-compose build)...")
    try:
        subprocess.run(["docker-compose", "build", "--no-cache"], check=True)
    except Exception as ex:
        print("❌ Fehler beim Bauen des Images:")
        traceback.print_exc()

def full_dev_start():
    print("\n🚦 Starte API-Service, öffne Bash & führe main.py aus...")
    try: # 1. API-Service Container dauerhaft starten (im Hintergrund)
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        os.system('start cmd /k "docker-compose logs -f"')
    except Exception as ex:
        print("❌ Fehler beim Starten des Service-Containers:")
        import traceback
        traceback.print_exc()
    try: # Starte interaktives Bash im Container
        os.system('start cmd /k "docker-compose run gateway bash"')
        print("💡 Neues Terminalfenster (Bash im Container) geöffnet.")
    except Exception as ex:
        print("❌ Fehler beim Öffnen der Shell:")
        import traceback 
        traceback.print_exc()
        

def stop_container():
    print("\n⏹ Stoppe Container (docker-compose stop)...")
    try:
        subprocess.run(["docker-compose", "stop"], check=True)
    except Exception as ex:
        print("❌ Fehler beim Stoppen:")
        traceback.print_exc()

def down_container():
    print("\n⬇️ Compose Down (docker-compose down)...")
    try:
        subprocess.run(["docker-compose", "down"], check=True)
    except Exception as ex:
        print("❌ Fehler beim Down:")
        traceback.print_exc()

def wipe_all():
    print("\n🧹 Wipe: Lösche alles (Container, Images, Volumes, Orphans)...")
    try:
        subprocess.run(["docker-compose", "down", "--rmi", "all", "-v", "--remove-orphans"], check=True)
        full_system_wipe()
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

    except Exception as ex:
        print("❌ Fehler beim Wipe:")
        traceback.print_exc()
        

def full_system_wipe():
    print("\n🧨 Führe kompletten System-Wipe aus (docker system prune -af)...")
    try:
        subprocess.run(["docker", "system", "prune", "-af"], check=True)
        print("✅ Kompletter System-Wipe abgeschlossen.")
    except Exception as ex:
        print("❌ Fehler beim System-Wipe:")
        import traceback
        traceback.print_exc()


def menu():
    print("\n[Gateway Docker-Dev CLI]")
    print("b: (Re)Build Image")
    print("a: Start")
    print("s: Stop Container")
    print("d: Compose Down (Container entfernen)")
    print("w: Wipe (alles löschen!)")
    print("x/q: Exit (Container bleibt ggf. laufen)")
    print("-" * 36)

import subprocess

def get_image_status(image_name="gateway"):
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout.strip():
            return True
    except Exception:
        pass
    return False

def get_container_status(container_name="gateway-container"):
    try:
        # Zeigt Container mit Status 'Up'
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout.strip():
            return "running"
        # Jetzt noch prüfen, ob existiert, aber stopped
        result2 = subprocess.run(
            ["docker", "ps", "-aq", "-f", f"name={container_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result2.stdout.strip():
            return "stopped"
    except Exception:
        pass
    return "not found"

def print_status():
    image_exists = get_image_status()
    container_status = get_container_status()
    print("\n[Docker Status]")
    print(f"Image 'gateway': {'✅ vorhanden' if image_exists else '❌ nicht gefunden'}")
    if container_status == "running":
        print(f"Container 'gateway-container': 🟢 läuft")
    elif container_status == "stopped":
        print(f"Container 'gateway-container': 🟡 gestoppt")
    else:
        print(f"Container 'gateway-container': 🔴 nicht vorhanden")
    print("-" * 36)

def list_all_images():
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if not lines or (len(lines) == 1 and lines[0] == ""):
            print("❌ Keine Images gefunden.")
            return
        print("📦 Docker Images:")
        print("REPOSITORY:TAG\t\tID\t\tGRÖSSE")
        for line in lines:
            print(line)
    except Exception as e:
        print("Fehler beim Auflisten der Images:", e)

def list_all_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if not lines or (len(lines) == 1 and lines[0] == ""):
            print("❌ Keine Container gefunden.")
            return
        print("🚢 Docker Container:")
        print("NAME\t\tSTATUS\t\tIMAGE")
        for line in lines:
            print(line)
    except Exception as e:
        print("Fehler beim Auflisten der Container:", e)

def print_docker_overview():
    print("="*40)
    list_all_images()
    print()
    list_all_containers()
    print("="*40)


def main():
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    print("🌐 Gateway Dev CLI gestartet.\n")
    print_docker_overview()
    print_status()
    # Bild baust du erst, wenn nicht vorhanden! später wieder einfügen
    # if not get_image_status():
        # build_image()
        # full_dev_start()
    while True:
        menu()
        try:
            choice = input("> ").strip().lower()
            if choice == "b":
                build_image()
            elif choice == "a":
                full_dev_start()
            elif choice == "s":
                stop_container()
            elif choice == "d":
                down_container()
            elif choice == "w":
                wipe_all()
            elif choice in ("x", "q"):
                print("Beende CLI... (Container bleibt, unless du zuvor 'd' oder 'w' ausgeführt hast)")
                break
            else:
                print("❓ Unbekannte Eingabe.")
        except Exception as ex:
            print("\n❌ Ausnahme im Menü:")
            traceback.print_exc()

if __name__ == "__main__":
    main()