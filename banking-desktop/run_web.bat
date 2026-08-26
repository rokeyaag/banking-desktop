@echo off
cd /d "%~dp0"
call .\venv\Scripts\activate.bat
echo Starting NexaBank Web App on http://127.0.0.1:8000 ...
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
pause
