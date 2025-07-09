import subprocess

IMAGE_NAME = "workforce_manager"

def build_image():
    print(f"🔨 Erstelle neues Docker-Image '{IMAGE_NAME}'...")
    subprocess.run(["docker", "build", "-t", IMAGE_NAME, "."], check=True)

if __name__ == "__main__":
    build_image()