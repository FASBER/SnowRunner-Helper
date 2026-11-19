@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===== SnowRunner Helper: reproducible Windows EXE build =====
REM Use python.exe from PATH (actions/setup-python), NEVER unqualified py.exe.
REM On GitHub runners py.exe may select Python 3.15 even if setup-python chose 3.11.
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: python.exe not found. Install Python 3.11 x64.
  exit /b 1
)
python -c "import sys; print('Build interpreter:', sys.executable, sys.version); sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
  echo ERROR: Building this Windows release requires Python 3.11 x64 on PATH.
  exit /b 1
)
REM Always recreate the disposable venv: an old one could contain Python 3.15 wheels.
if exist ".build-venv" (
  rmdir /s /q ".build-venv"
  if errorlevel 1 (echo ERROR: Cannot remove stale build environment & exit /b 1)
)
python -m venv ".build-venv"
if errorlevel 1 (echo ERROR: Cannot create build virtualenv & exit /b 1)
set "BUILD_PY=.build-venv\Scripts\python.exe"
"%BUILD_PY%" -m pip install -r requirements.txt "pyinstaller>=6.0"
if errorlevel 1 (echo ERROR: Cannot install build dependencies & exit /b 1)
REM Check both actual Python runtime and _rust.pyd PE dependency table.
"%BUILD_PY%" release_tools\verify_freeze_runtime.py
if errorlevel 1 (echo ERROR: Unsafe Python/cryptography binary dependencies & exit /b 1)
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
