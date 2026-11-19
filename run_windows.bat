@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Python 3.10+ required. Install from https://www.python.org/downloads/windows/
 pause
 exit /b 1
)
py -c "from PIL import ImageTk; from fontTools.ttLib import TTFont; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey" >nul 2>nul
if errorlevel 1 (
 echo Installing Pillow and fonttools for images and custom fonts...
 py -m pip install -r requirements.txt
 if errorlevel 1 (echo Dependency installation failed & pause & exit /b 1)
)
py app.py
if errorlevel 1 (echo Application exited with an error & pause)
