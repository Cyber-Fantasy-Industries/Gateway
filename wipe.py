# wipe.py
import subprocess

def run(cmd, check=False):
    print(f"💻 {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")

def get_container_ids(all_containers=False):
    flag = "-a" if all_containers else ""
    result = subprocess.run(
        f"docker ps {flag} --format \"{{{{.ID}}}}\"",
        shell=True,
        capture_output=True,
        text=True
    )
    ids = result.stdout.strip().splitlines()
    return ids

print("🛑 Stoppe alle laufenden Container...")
running_ids = get_container_ids()
if running_ids:
    run(f"docker stop {' '.join(running_ids)}")
else:
    print("ℹ️ Keine laufenden Container.")

print("🧹 Entferne alle gestoppten Container...")
all_ids = get_container_ids(all_containers=True)
if all_ids:
    run(f"docker rm {' '.join(all_ids)}")
else:
    print("ℹ️ Keine Container zum Entfernen.")

print("🗑 Suche alle Images mit REPOSITORY 'workforce_manager'...")
result = subprocess.run(
    "docker images --format \"{{.Repository}} {{.ID}}\"",
    shell=True,
    capture_output=True,
    text=True
)

found = False
for line in result.stdout.strip().splitlines():
    parts = line.split()
    if len(parts) == 2:
        repo, img_id = parts
        if repo == "workforce_manager":
            found = True
            print(f"🗑 Lösche Image {img_id}")
            run(f"docker rmi -f {img_id}", check=False)

if not found:
    print("ℹ️ Keine Images von 'workforce_manager' gefunden.")

print("🧽 Entferne ungenutzte Images und Build-Caches...")
run("docker system prune -f", check=False)

print("✅ Wipe abgeschlossen.")

# 👇 Hier bleibt das Fenster offen
input("\n👉 Drücke [Enter], um das Fenster zu schließen...")
