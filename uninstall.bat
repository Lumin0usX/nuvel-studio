@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
if /i "%~1"=="--check" goto check
if exist "%~dp0.venv-windows-build\Scripts\pythonw.exe" (
    start "" /b "%~dp0.venv-windows-build\Scripts\pythonw.exe" "%~dp0app_uninstall.py"
    exit /b 0
)
py -3 "%~dp0app_uninstall.py" %*
if not errorlevel 1 exit /b 0
echo Uninstall could not start or finish. Close Studio and retry.
pause
exit /b 1

:check
if exist "%~dp0.venv-windows-build\Scripts\python.exe" (
    "%~dp0.venv-windows-build\Scripts\python.exe" "%~dp0app_uninstall.py" --check
    exit /b
)
py -3 "%~dp0app_uninstall.py" --check
exit /b
