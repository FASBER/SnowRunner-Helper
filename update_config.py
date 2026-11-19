"""Release configuration. Deliberately inert until an official signing key is set.

The Ed25519 PRIVATE key must NEVER be placed in this repository or bundled EXE.
The corresponding PUBLIC key is safe to embed here at release time.
"""
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
try:
    CURRENT_VERSION = json.loads((_ROOT / 'version.json').read_text(encoding='utf-8'))['version']
except (OSError, ValueError, KeyError, TypeError):
    CURRENT_VERSION = '0.31.1'

# Verified public GitHub repository. No GitHub token is bundled.
# For production OTA you MUST set the matching Ed25519 public key below.
# Never put the private signing key in the repository or the EXE.
from github_releases import github_latest_manifest_url
GITHUB_OWNER = 'FASBER'
GITHUB_REPO = 'SnowRunner-Helper'
RELEASE_MANIFEST_URL = (github_latest_manifest_url(GITHUB_OWNER, GITHUB_REPO)
                        if GITHUB_OWNER and GITHUB_REPO else '')
PUBLIC_KEY_ED25519_BASE64 = ''
UPDATE_CHANNEL = 'stable'
MAX_INSTALLER_BYTES = 1_073_741_824  # 1 GiB; conservative cap for setup downloads
