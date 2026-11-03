@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv || goto :err
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :err
pyinstaller --noconfirm --clean --noconsole --onefile --name "RSG LocalHost" --icon icon.ico ^
  --add-data "app/assets;app/assets" --add-data "app/styles;app/styles" main.py || goto :err
echo.
echo Done: dist\RSG LocalHost.exe
pause
exit /b 0
:err
echo Build failed.
pause
exit /b 1
