@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 goto use_py
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.10 or newer was not found.
echo Install 64-bit Python and enable Add Python to PATH.
if /i not "%~1"=="--check" pause
exit /b 1

:use_py
set "YTDL_PYTHON=py -3"
goto run

:use_python
set "YTDL_PYTHON=python"

:run
if /i "%~1"=="--check" goto check
(
    title YTDL Studio - Build
    echo Building YTDL Studio for Windows. Close the app and finish downloads first.
    %YTDL_PYTHON% -u "%~dp0build_windows.py"
    if errorlevel 1 (
        echo.
        echo Build failed. See the error above. The previous app was kept.
        pause
        exit /b 1
    ) else (
        echo.
        echo Open the YTDL Studio shortcut to use the app without a terminal.
        pause
        exit /b 0
    )
)

:check
%YTDL_PYTHON% -u "%~dp0build_windows.py" --check
exit /b %errorlevel%
