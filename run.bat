@echo off
cd /d "%~dp0banking-desktop"
call .\venv\Scripts\activate.bat
python app\main.py
