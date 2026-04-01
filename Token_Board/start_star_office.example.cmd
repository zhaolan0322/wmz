@echo off
setlocal

set "ROOT=%~dp0"
set "STAR_ROOT=%ROOT%vendor\Star-Office-UI"
set "STAR_PYTHON=%STAR_ROOT%\.venv\Scripts\python.exe"

if not exist "%STAR_ROOT%\state.json" (
  copy "%STAR_ROOT%\state.sample.json" "%STAR_ROOT%\state.json" >nul
)

rem Set this to your own bot workspace path before first run.
set "OPENCLAW_WORKSPACE=D:\path\to\your\workspace\mishu"
set "STAR_BACKEND_PORT=19000"

rem Use your own strong local values instead of committing real secrets.
set "FLASK_SECRET_KEY=replace_with_your_own_long_random_secret"
set "ASSET_DRAWER_PASS=replace_with_your_own_strong_drawer_password"
set "STAR_OFFICE_STATE_FILE=%STAR_ROOT%\state.json"

start "Star Office Backend" /MIN "%STAR_PYTHON%" "%STAR_ROOT%\backend\app.py"
start "Star Office Sync" /MIN py -3.12 "%ROOT%sync_mishu_star_office.py"

echo Star Office UI started at http://127.0.0.1:19000
echo Update OPENCLAW_WORKSPACE, FLASK_SECRET_KEY, and ASSET_DRAWER_PASS before production use.

endlocal
