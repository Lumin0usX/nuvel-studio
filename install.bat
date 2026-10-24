@echo off
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 goto use_py
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/windows/
echo Enable Add Python to PATH, then try again.
if /i not "%~1"=="--check" pause
exit /b 1

:use_py
set "NUVEL_PYTHON=py -3"
goto run

:use_python
set "NUVEL_PYTHON=python"

:run
title Studio - Install
if /i "%~1"=="--check" goto check
%NUVEL_PYTHON% -m pip install --upgrade -r "%~dp0requirements.txt"
set "NUVEL_EXIT=%errorlevel%"
if not "%NUVEL_EXIT%"=="0" goto failed
%NUVEL_PYTHON% "%~dp0create_windows_launcher.py"
set "NUVEL_EXIT=%errorlevel%"
if not "%NUVEL_EXIT%"=="0" goto failed
echo.
echo Installation complete. Open the new Studio shortcut (no Terminal).
pause
exit /b 0

:failed
echo.
echo Installation failed. See the error above.
pause
exit /b %NUVEL_EXIT%

:check
%NUVEL_PYTHON% -m pip --version
exit /b %errorlevel%
