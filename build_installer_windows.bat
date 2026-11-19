@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===== SnowRunner Helper v0.31.0 Setup =====
call build_windows.bat
if errorlevel 1 goto error
set "ISCC="
where ISCC.exe >nul 2>nul
if not errorlevel 1 set "ISCC=ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo ERROR: Inno Setup 6 missing. Install from https://jrsoftware.org/isinfo.php
  echo Application EXE is still available: dist\SnowRunnerHelper.exe
  goto error
)
echo Building native installer via %ISCC% ...
"%ISCC%" "setup_snowrunner.iss"
if errorlevel 1 goto error
if not exist "installer_build\SnowRunnerHelper_Setup_v0.31.0.exe" (
  echo ERROR: Installer file not found
  goto error
)
echo.
echo SUCCESS: installer_build\SnowRunnerHelper_Setup_v0.31.0.exe
echo To verify: Install into a custom path, reopen, uninstall and verify profiles are retained.
pause
exit /b 0
:error
echo Build incomplete; see errors above.
pause
exit /b 1
