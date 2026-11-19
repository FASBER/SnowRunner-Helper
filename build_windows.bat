@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===== SnowRunner Helper: Windows EXE build =====
set "PY_EXE=py"
where py >nul 2>nul
if errorlevel 1 set "PY_EXE=python"
where "%PY_EXE%" >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.10+ not found. Install Python for Windows.
  exit /b 1
)
if not exist ".build-venv\Scripts\python.exe" (
  %PY_EXE% -m venv .build-venv
  if errorlevel 1 exit /b 1
)
set "BUILD_PY=.build-venv\Scripts\python.exe"
"%BUILD_PY%" -m pip install -r requirements.txt "pyinstaller>=6.0"
if errorlevel 1 (echo ERROR: Python dependencies unavailable & exit /b 1)
"%BUILD_PY%" -m unittest discover -s tests -p "test_*.py"
if errorlevel 1 (echo ERROR: automated tests failed & exit /b 1)
"%BUILD_PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
 --icon "app_icon.ico" --name "SnowRunnerHelper" ^
 --add-data "catalog.json;." --add-data "recipes_builtin.json;." ^
 --add-data "assets;assets" --add-data "version.json;." ^
 --hidden-import "PIL.ImageTk" --collect-all fontTools ^
 --hidden-import "fontTools.ttLib" --collect-submodules fontTools app.py
if errorlevel 1 (echo ERROR: Windows EXE build failed & exit /b 1)
if not exist "dist\SnowRunnerHelper.exe" (echo ERROR: output missing & exit /b 1)
echo SUCCESS: dist\SnowRunnerHelper.exe
exit /b 0
