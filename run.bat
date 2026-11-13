@echo off
REM Sea Safe: one command to set up and run on Windows.
REM First run creates a virtual environment and installs packages; later runs just start.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is needed. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv || (pause & exit /b 1)
)
.venv\Scripts\python -m pip install -q -r requirements.txt || (echo Package install failed. & pause & exit /b 1)

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example. Put your GEMINI_API_KEY and GROQ_API_KEY in it for the chat to work.
)

set PORT=8000
for /f "tokens=2 delims==" %%p in ('findstr /b "PORT=" .env') do set PORT=%%p

echo.
echo Sea Safe is starting on http://localhost:%PORT%   (press Ctrl+C to stop)
REM open the browser a few seconds later, once the server is up
start "" /b cmd /c "timeout /t 4 >nul & start http://localhost:%PORT%"
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
