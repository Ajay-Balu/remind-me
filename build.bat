@echo off
REM Builds a single RemindMe.exe in the dist folder (no Python needed to run it).
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY ( echo Python was not found. & pause & exit /b 1 )

%PY% -m pip install -q -r requirements.txt pyinstaller || ( pause & exit /b 1 )
%PY% -c "from remindme.tray import save_ico; save_ico('icon.ico')" || ( pause & exit /b 1 )
%PY% -m PyInstaller --noconfirm --onefile --windowed --name RemindMe --icon icon.ico ^
  --hidden-import pystray._win32 --hidden-import PIL.ImageTk --add-data "assets;assets" run.pyw
echo.
echo Done: dist\RemindMe.exe
pause
