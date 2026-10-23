@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 goto use_py
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.10 or newer was not found.
echo Install Python and enable Add Python to PATH, then try again.
if /i not "%~1"=="--check" pause
exit /b 1

:use_py
set "YTDL_PYTHON=py -3"
goto run

:use_python
set "YTDL_PYTHON=python"

:run
if /i "%~1"=="--check" goto check
rem Keep execution in one parsed block: Git may replace this batch file.
(
    title Studio - Update
    echo.
    echo Studio - Update
    echo Close Studio and finish any downloads before continuing.
    echo This uses your existing GitHub access to the private repository.
    echo.
    pause
    %YTDL_PYTHON% -u "%~dp0update_project.py"
    if errorlevel 1 (
        echo.
        echo Update failed. See the error above, then retry.
        pause
        exit /b 1
    ) else (
        echo.
        pause
        exit /b 0
    )
)

:check
%YTDL_PYTHON% -u "%~dp0update_project.py" --check
exit /b %errorlevel%
