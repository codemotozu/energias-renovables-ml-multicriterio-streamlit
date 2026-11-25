@echo off
rem Abre el tablero en el navegador. La primera vez instala lo necesario.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Instalando el entorno. Solo ocurre la primera vez...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -r dashboardequirements.txt
)
start "" cmd /c "timeout /t 7 >nul & start http://localhost:8501"
.venv\Scripts\python.exe -m streamlit run dashboardpp.py --server.port 8501
pause
