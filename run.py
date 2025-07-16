import os
import subprocess
import traceback
import subprocess
import time

COMPOSE_FILE = "docker-compose.yml"
CONTAINER_NAME = "gateway-container"

def rebuild_image():
    print("\n♻️ Rebuild started...")
    wipe_all()
    build_image()
    quick_start()

def build_image():
    print("\n🔨 Start Image-Build...")
    subprocess.run(["docker-compose", "build", "--no-cache"], check=True)

def quick_start():
    print("\nStarting System...")
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    os.system('start cmd /k "docker-compose logs -f"')
    os.system('start cmd /k "docker-compose run gateway bash"')
    time.sleep(2)  # Warte 2 Sekunden
    print("System Started.")


def stop_container():
    print("\nStoping System...")
    subprocess.run(["docker-compose", "stop"], check=True)
    subprocess.run(["docker-compose", "down"], check=True)
    kill_all_gateway_containers()
    print("System Stopped.")

def kill_all_gateway_containers():
    print("\n🧹 Removing all Gateway-Containers...")
    # Hole alle Container, deren Name mit 'gateway' beginnt
    import subprocess
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=gateway", "--format", "{{.ID}}\t{{.Names}}"],
        stdout=subprocess.PIPE, text=True
    )
    lines = result.stdout.strip().split('\n')
    if lines and lines[0]:
        ids = [line.split('\t')[0] for line in lines]
        for cid in ids:
            subprocess.run(["docker", "rm", "-f", cid])
            print(f"🗑 Removed Container {cid}")
    else:
        print("ℹ️ No Container found.")

def wipe_all():
    print("\nDeleting Gateway...")
    subprocess.run(["docker-compose", "down", "--rmi", "all", "-v", "--remove-orphans"], check=True)
    #kill_all_gateway_containers()
    subprocess.run(["docker", "network", "rm", "gateway_default"])
    subprocess.run(["docker", "system", "prune", "-af"], check=True)

    try:
        result = subprocess.run(
            ["docker", "images", "-a", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}"],
            stdout=subprocess.PIPE, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if line.startswith("gateway"):
                parts = line.split("\t")
                if len(parts) == 2:
                    img_id = parts[1]
                    subprocess.run(["docker", "rmi", "-f", img_id])
                    print(f"🗑️  Gateway-Image entfernt: {img_id}")
    except Exception as e:
        print("Fehler beim expliziten Entfernen der Images:", e)
    print("✅ System-Wipe completed.")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

###########
def menu():
    print("\n################################")
    print("### [Gateway Docker-Dev CLI] ###")
    print("################################")
    print_docker_overview()
    print("#")
    print("#  r: Wipe System and Rebuild Image")
    print("#")
    print("#  a: Quick Start")
    print("#")
    print("#  s: Stop")
    print("#")
    print("#  w: wipe")
    print("#")
    print("#  x: Exit (Container läuft weiter)")
    print("#")
    print("#","-" * 30)


def print_docker_overview():
    print(" 🖥️  [Docker System Status]")
    print("################################")
    # image_exists = get_image_status()
    # container_status = get_container_status()
    # print(f"  🗂️  Image 'gateway':   {'✅' if image_exists else '❌'}")
    # if container_status == "running":
    #     print(f"  🟢 Container 'gateway-container':   läuft")
    # elif container_status == "stopped":
    #     print(f"  🟡 Container 'gateway-container':   gestoppt")
    # else:
    #     print(f"  🔴 Container 'gateway-container':   nicht vorhanden")
    # print("─" * 45)
    print(" 📦 Docker Images:")
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{:<18} {:<14} {:<8}".format("{{.Repository}}:{{.Tag}}", "{{.ID}}", "{{.Size}}")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            print("  {:<18} {:<14} {:<8}".format("REPOSITORY:TAG", "ID", "GRÖSSE"))
            for line in lines:
                print("  " + line)
        else:
            print("  ❌ Keine Images gefunden.")
    except Exception as e:
        print("  Fehler beim Auflisten der Images:", e)
    print("################################")
    print(" 🚢 Docker Container:")
    try:
        result = subprocess.run(
            [
                "docker", "ps", "-a",
                "--format",
                "{:<12} {:<32} {:<18} {:<16} {:<20} {:<30} {:<12}".format(
                    "{{.ID}}", "{{.Names}}", "{{.Status}}", "{{.Image}}",
                    "{{.Command}}", "{{.CreatedAt}}", "{{.Ports}}"
                )
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            print("  {:<12} {:<32} {:<18} {:<16} {:<20} {:<30} {:<12}".format(
                "ID", "NAME", "STATUS", "IMAGE", "COMMAND", "CREATED AT", "PORTS"
            ))
            for line in lines:
                print("  " + line)
        else:
            print("  ❌ Keine Container gefunden.")
    except Exception as e:
        print("  Fehler beim Auflisten der Container:", e)
    print("################################")
    print(" 🌐 Docker Netzwerke:")
    try:
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{:<20} {:<20} {:<16}".format("{{.Name}}", "{{.Driver}}", "{{.Scope}}")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            print("  {:<20} {:<20} {:<16}".format("NAME", "DRIVER", "SCOPE"))
            for line in lines:
                # Nur Netzwerke anzeigen, die 'gateway' enthalten
                if "gateway" in line:
                    print("  " + line)
        else:
            print("  ❌ Keine Netzwerke gefunden.")
    except Exception as e:
        print("  Fehler beim Auflisten der Netzwerke:", e)
    print("################################")
    print(" 📈 docker stats (Live-Überblick):")
    subprocess.run(["docker", "stats", "--no-stream"])
    print("################################")


#########################################
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

def main():
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    if not get_image_status():
        print("\n  No Image found.")
        build_image()
        quick_start()

    while True:
        menu()
        try:
            choice = input("> ").strip().lower()
            if choice == "r":
                rebuild_image()
            elif choice == "a":
                quick_start()
            elif choice == "w":
                wipe_all()
            elif choice == "s":
                stop_container()
            elif choice in ("x"):
                print("Beende CLI... (Container bleibt, unless du zuvor 's' ausgeführt hast)")
                break
            else:
                print("❓ Unbekannte Eingabe.")
        except Exception as ex:
            print("\n❌ Ausnahme im Menü:")
            traceback.print_exc()

if __name__ == "__main__":
    main()