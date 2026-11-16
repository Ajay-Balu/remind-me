@echo off
cd /d "%~dp0"
call :findpy || goto :eof

echo Installing requirements with %PY% ...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 ( echo. & echo pip install failed - see the message above. & pause & exit /b 1 )

%PY% -c "import tkinter, pystray, PIL"
if errorlevel 1 ( echo. & echo A required module is missing - see the message above. & pause & exit /b 1 )

start "" %PYW% run.pyw
echo Remind Me started - look for the blue drop icon in the system tray.
timeout /t 3 >nul
goto :eof

:findpy
REM Prefer the "py" launcher (works even when python.exe is not on PATH).
set "PY=" & set "PYW="
where py >nul 2>nul && py -3 -c "import sys" >nul 2>nul && (set "PY=py -3" & set "PYW=pyw -3")
if defined PY exit /b 0
python -c "import sys" >nul 2>nul && (set "PY=python" & set "PYW=pythonw")
if defined PY exit /b 0
echo Python was not found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during setup.
pause
exit /b 1
