# main.py
from loguru import logger
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.agents import router as agents_router
from backend.routes.conference import router as conference_router
from backend.routes.settings import router as settings_router
from backend.routes.websocket import router as websocket_router
from backend.routes.docker import router as docker_router
from backend.routes.system import router as system_router
from backend.routes.websocket import start_watcher
from backend.agent_core.core import initialize_lobby
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_lobby()
    start_watcher(path="backend/")
    yield
    # (Optional: Cleanup z.B. shutdown code)

app = FastAPI(
    lifespan=lifespan,
    title="Gateway API",
    description="Modulare KI-Agentenplattform mit Autogen und UE5-Integration",
    version="0.1"
)

  
# 📂 Log-Verzeichnis sicherstellen
LOG_PATH = "logs"
os.makedirs(LOG_PATH, exist_ok=True)
logger.add(os.path.join(LOG_PATH, "server.log"), rotation="500 KB", backtrace=True, diagnose=True)
logger.info("🚀 Gateway API gestartet.")

# 🟢 CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📌 API-Routen registrieren
app.include_router(agents_router)
app.include_router(conference_router)
app.include_router(settings_router)
app.include_router(websocket_router)
app.include_router(system_router)
app.include_router(docker_router)


# 🔧 Uvicorn-Einstiegspunkt
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)


