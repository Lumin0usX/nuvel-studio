-- Compiled locally by the installer. The app remains beside the source folder.
on run
    set appPath to POSIX path of (path to me)
    set projectPath to do shell script "/usr/bin/dirname " & quoted form of appPath
    set pythonPath to projectPath & "/.venv-macos/bin/python"
    set launcherPath to projectPath & "/desktop_launcher.py"
    try
        do shell script "/usr/bin/test -x " & quoted form of pythonPath & " && /usr/bin/test -f " & quoted form of launcherPath
        do shell script "exec " & quoted form of pythonPath & " " & quoted form of launcherPath & " --applet"
    on error
        set logPath to (POSIX path of (path to library folder from user domain)) & "Logs/YTDLStudio/"
        display alert "YTDL Studio could not start or closed unexpectedly." message "Keep this launcher in the project folder. Run install_macos.command if needed. Startup logs: " & logPath as critical
    end try
end run
