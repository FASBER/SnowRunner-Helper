"""Secure, deferred Windows OTA installation for SnowRunner Helper.

The previous updater started Inno Setup *before* Tk/PyInstaller exited, so
Windows could not replace SnowRunnerHelper.exe while it remained open.

A separate, short-lived Windows PowerShell process now waits for this exact
parent PID to terminate, re-checks the installer size and SHA-256 after that
wait, and only then starts the approved Inno Setup file. No shell=True and no
network-controlled arbitrary command or installer arguments.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
import re
import subprocess
import sys

from update_downloader import file_matches
from update_security import Release, UpdateSecurityError, version_tuple


class UpdateLaunchError(RuntimeError):
    pass


def _ps_literal(value):
    """Always escape the PowerShell single-quoted string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _deferred_script(installer, parent_pid, size, digest, logfile, bootloader_pid=0):
    """Create a *self-contained* script for the separate Windows process."""
    return f"""
$ErrorActionPreference = 'Stop'
$parentProcessId = {int(parent_pid)}
$bootloaderProcessId = {int(bootloader_pid)}
$installerPath = {_ps_literal(installer)}
$logPath = {_ps_literal(logfile)}
$expectedBytes = [int64]{int(size)}
$expectedSha256 = {_ps_literal(digest)}
try {{
    $deadline = (Get-Date).AddMinutes(2)
    # PyInstaller one-file may leave a separate bootloader parent alive
    # for a short period after the Python child exits.
    $waitingPids = @($parentProcessId)
    if ($bootloaderProcessId -gt 0 -and $bootloaderProcessId -ne $parentProcessId) {{
        $waitingPids += $bootloaderProcessId
    }}
    foreach ($processIdToWait in $waitingPids) {{
        while ((Get-Process -Id $processIdToWait -ErrorAction SilentlyContinue) -and ((Get-Date) -lt $deadline)) {{
            Start-Sleep -Milliseconds 250
        }}
        if (Get-Process -Id $processIdToWait -ErrorAction SilentlyContinue) {{
            throw 'SnowRunner Helper did not finish closing; installer was not started.'
        }}
    }}
    $installerInfo = Get-Item -LiteralPath $installerPath -ErrorAction Stop
    if ($installerInfo.Length -ne $expectedBytes) {{
        throw 'Downloaded installer size changed after application exit.'
    }}
    $actualSha256 = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {{
        throw 'Downloaded installer SHA-256 changed after application exit.'
    }}
    # Explicitly mark OTA runs for new installers; legacy v0.31.5 is detected
    # by the setup source directory in the Inno Setup code.
    Start-Process -FilePath $installerPath -WorkingDirectory $installerInfo.DirectoryName -ArgumentList '/OTA=1' -ErrorAction Stop
    exit 0
}} catch {{
    try {{
        ('OTA startup failed: ' + $_.Exception.Message) | Set-Content -LiteralPath $logPath -Encoding UTF8
    }} catch {{ }}
    exit 1
}}
"""


def _verified_paths(path, release, user_folder):
    if not isinstance(release, Release):
        raise UpdateSecurityError('Installer must come from a verified signed release')
    version_tuple(release.version)
    if not re.fullmatch(r'[a-f0-9]{64}', release.sha256):
        raise UpdateSecurityError('Invalid signed installer SHA-256')
    if isinstance(release.size, bool) or not isinstance(release.size, int) or release.size < 1:
        raise UpdateSecurityError('Invalid signed installer size')
    root = Path(user_folder).resolve()
    target = Path(path).resolve()
    if target.parent != root or target.name != f'SnowRunnerHelper_Setup_v{release.version}.exe':
        raise UpdateSecurityError('Unexpected installer location')
    if not file_matches(target, release):
        raise UpdateSecurityError('Installer changed after download')
    return target, root


def launch_installer(path, release: Release, *, user_folder,
                     popen=None, platform=None, parent_pid=None, powershell_exe=None):
    """Start a background hand-off, then let the caller EXIT immediately.

    This returns after starting the hand-off, not after the installer starts.
    The caller must close its GUI and terminate so the old EXE is unlocked.
    """
    system = os.name if platform is None else platform
    if system != 'nt':
        raise UpdateLaunchError('Installation requires Windows')
    target, root = _verified_paths(path, release, user_folder)
    if parent_pid is None:
        parent_pid = os.getpid()
    if isinstance(parent_pid, bool) or not isinstance(parent_pid, int) or parent_pid <= 0:
        raise UpdateLaunchError('Invalid parent process ID')
    if powershell_exe is None:
        windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
        ps = windows / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    else:
        ps = Path(powershell_exe)
    if popen is None and not ps.is_file():
        raise UpdateLaunchError('Windows PowerShell not found; launch the installer manually')

    # The signed manifest supplied the expected digest and size. Verify again
    # in the helper AFTER the old application has exited, to resist tampering.
    # The one-file PyInstaller launcher can outlive its Python subprocess.
    # Waiting for BOTH processes avoids a second executable-file lock race.
    bootloader_pid = os.getppid() if getattr(sys, 'frozen', False) else 0
    script = _deferred_script(target, parent_pid, release.size, release.sha256,
                              root / 'ota_launch_error.txt', bootloader_pid)
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    command = [str(ps), '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden',
               '-EncodedCommand', encoded]
    run = popen or subprocess.Popen
    options = {'cwd': str(root), 'close_fds': True}
    if os.name == 'nt':
        options['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        return run(command, **options)
    except OSError as exc:
        raise UpdateLaunchError('Unable to start the deferred Windows installer') from exc
