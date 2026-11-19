"""Stream the verified installer into a private user directory with a SHA-256 check."""
import hashlib
import os
import shutil
import urllib.request
from pathlib import Path
from update_security import Release, UpdateSecurityError, validate_https_url, version_tuple

class UpdateDownloadError(RuntimeError):
    pass

class UpdateDownloadCancelled(UpdateDownloadError):
    pass

def file_matches(path, release):
    path = Path(path)
    try:
        if path.stat().st_size != release.size:
            return False
        digest = hashlib.sha256()
        with path.open('rb') as file:
            for data in iter(lambda: file.read(262144), b''):
                digest.update(data)
        return digest.hexdigest() == release.sha256
    except OSError:
        return False

def download_installer(release: Release, folder, *, progress=None, cancelled=None, opener=None, timeout=30):
    if not isinstance(release, Release):
        raise UpdateSecurityError('Release must be authenticated before download')
    validate_https_url(release.url)
    version_tuple(release.version)
    root = Path(folder).resolve()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f'SnowRunnerHelper_Setup_v{release.version}.exe'
    part = root / f'.SnowRunnerHelper_{release.version}_{os.getpid()}.part'
    if file_matches(dest, release):
        if progress: progress(release.size, release.size)
        return dest
    part.unlink(missing_ok=True)  # discard residue of a previous interrupted download
    if shutil.disk_usage(root).free < release.size + 10*1024*1024:
        raise UpdateDownloadError('Not enough free disk space')
    fetch = opener or urllib.request.urlopen
    downloaded = 0
    digest = hashlib.sha256()
    try:
        req = urllib.request.Request(release.url, headers={'User-Agent': 'SnowRunnerHelper-Updater/1'})
        with fetch(req, timeout=timeout) as response, part.open('xb') as output:
            validate_https_url(response.geturl())
            while True:
                if cancelled and cancelled():
                    raise UpdateDownloadCancelled('Download canceled by user')
                data = response.read(131072)
                if not data: break
                downloaded += len(data)
                if downloaded > release.size:
                    raise UpdateDownloadError('Downloaded file exceeds signed size')
                output.write(data)
                digest.update(data)
                if progress: progress(downloaded, release.size)
            output.flush()
            os.fsync(output.fileno())
        if downloaded != release.size or digest.hexdigest() != release.sha256:
            raise UpdateDownloadError('Installer checksum or size does not match signed manifest')
        os.replace(part, dest)
        return dest
    except (OSError, TimeoutError) as exc:
        raise UpdateDownloadError('Could not download update') from exc
    finally:
        part.unlink(missing_ok=True)
