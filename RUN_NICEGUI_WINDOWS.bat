@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Python environment belum ada. Ikuti README_MODERN_EXCEL.md untuk instalasi.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m nicegui_app.main
pause
