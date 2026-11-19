"""Generate safe GitHub Releases links for the signed SnowRunner OTA channel.

GitHub hosts binary assets; publisher-signed update.json is the only trusted
update authority. This module never needs a token for public repositories.
"""
import re
from urllib.parse import quote

from update_security import version_tuple

_COMPONENT = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$')
_ASSET = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$')


def _component(value: str) -> str:
    if not isinstance(value, str) or not _COMPONENT.fullmatch(value) or value in {'.', '..'}:
        raise ValueError('Invalid GitHub repository owner or name')
    return value


def github_latest_manifest_url(owner: str, repo: str, filename='update.json') -> str:
    """Stable releases only; prereleases do not become the latest release."""
    owner, repo = _component(owner), _component(repo)
    if not isinstance(filename, str) or not _ASSET.fullmatch(filename):
        raise ValueError('Invalid release asset filename')
    return f'https://github.com/{quote(owner)}/{quote(repo)}/releases/latest/download/{quote(filename)}'


def github_setup_url(owner: str, repo: str, version: str,
                     filename: str | None = None) -> str:
    owner, repo = _component(owner), _component(repo)
    version_tuple(version)
    filename = filename if filename is not None else f'SnowRunnerHelper_Setup_v{version}.exe'
    if not isinstance(filename, str) or not _ASSET.fullmatch(filename) or not filename.lower().endswith('.exe'):
        raise ValueError('Invalid setup EXE filename')
    return f'https://github.com/{quote(owner)}/{quote(repo)}/releases/download/v{version}/{quote(filename)}'
