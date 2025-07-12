@echo off
cd /d %~dp0
echo 🔁 Starte Gateway API auf Port 8080...
uvicorn backend.main:app --reload --port 8080
pause
