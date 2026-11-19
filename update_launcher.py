"""Launch an authenticated installer after the app has saved its drafts.

No shell=True, no custom arguments from the network, no update actions on Linux.
"""
import os
import subprocess
from pathlib import Path
from update_downloader import file_matches
from update_security import Release, UpdateSecurityError

class UpdateLaunchError(RuntimeError):
    pass

def launch_installer(path, release: Release, *, user_folder, popen=None, platform=None):
    platform = platform or os.name
    if platform != 'nt':
        raise UpdateLaunchError('Installation requires Windows')
    target = Path(path).resolve()
    root = Path(user_folder).resolve()
    if target.parent != root or target.name != f'SnowRunnerHelper_Setup_v{release.version}.exe':
        raise UpdateSecurityError('Unexpected installer location')
    if not file_matches(target, release):
        raise UpdateSecurityError('Installer changed after download')
    # Native Inno Setup UI: user can verify/retain the installation directory.
    # With UsePreviousAppDir=yes Inno Setup defaults to the previous directory.
    run = popen or subprocess.Popen
    try:
        return run([str(target)], cwd=str(root), close_fds=True)
    except OSError as exc:
        raise UpdateLaunchError('Cannot launch the Windows installer') from exc
