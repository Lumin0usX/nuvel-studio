@echo off
rem SPDX-License-Identifier: GPL-3.0-only
rem Copyright © 2026 Lumin0usX
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
title Studio
if /i "%~1"=="--check" goto check
%NUVEL_PYTHON% "%~dp0nuvel_studio.py"
set "NUVEL_EXIT=%errorlevel%"
if "%NUVEL_EXIT%"=="0" exit /b 0
echo.
echo Studio could not start. See the error above.
echo Run install.bat if a dependency is missing.
pause
exit /b %NUVEL_EXIT%

:check
%NUVEL_PYTHON% -c "import glass_app; print('Studio launcher: OK')"
exit /b %errorlevel%
