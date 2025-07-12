import subprocess
import time

IMAGE_NAME = "gateway"
CONTAINER_NAME = "gateway-container"

def run(cmd):
    print(f"💻 {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    print(result.stderr)

print("🔨 Baue Image...")
run(f"docker build -t {IMAGE_NAME} .")

print("🚀 Starte Container...")
run(f"docker run -d --name {CONTAINER_NAME} -p 8080:8080 {IMAGE_NAME}")

print("✅ Container läuft. Öffne http://localhost:8080")

input("⏹ Drücke [Enter] zum Beenden...")

print("🧹 Beende und entferne Container & Image...")
run(f"docker stop {CONTAINER_NAME}")
run(f"docker rm {CONTAINER_NAME}")
run(f"docker rmi {IMAGE_NAME}")

print("✅ Cleanup abgeschlossen.")
