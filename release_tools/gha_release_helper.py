"""Safe release steps for FASBER/SnowRunner-Helper GitHub Actions.

`prepare`: on Windows build runner, validates vX.Y.Z tag and embeds *public*
Ed25519 key into a temporary workspace copy of update_config.py.

`sign`: on separate privileged runner, accepts the *private* PEM through a GitHub
Actions secret environment variable (never via a command-line argument or file).
Refuses to sign corrupt/non-PE files or mismatched public/private keys.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from github_releases import github_setup_url
from update_security import canonical_payload, verify_manifest

OWNER = 'FASBER'
REPO = 'SnowRunner-Helper'
ROOT = Path(__file__).resolve().parent.parent
APP_CONFIG = ROOT / 'update_config.py'
KEY_VARIABLE = 'OTA_ED25519_PUBLIC_BASE64'
KEY_SECRET = 'OTA_ED25519_PRIVATE_PEM'


def project_version(root=ROOT):
    data = json.loads((Path(root) / 'version.json').read_text(encoding='utf-8'))
    return data['version']


def verify_release_context(tag, root=ROOT, repository=None):
    version = project_version(root)
    if tag != f'v{version}':
        raise ValueError('Git tag must match the version.json version exactly')
    repository = repository if repository is not None else os.getenv('GITHUB_REPOSITORY', f'{OWNER}/{REPO}')
    if repository != f'{OWNER}/{REPO}':
        raise ValueError('Release is limited to the official repository')
    iss = (Path(root) / 'setup_snowrunner.iss').read_text(encoding='utf-8')
    if f'#define MyAppVersion "{version}"' not in iss or f'OutputBaseFilename=SnowRunnerHelper_Setup_v{version}' not in iss:
        raise ValueError('Installer metadata must agree with the tag')
    return version


def validate_public_key(value):
    try:
        decoded = base64.b64decode(value, validate=True)
    except (TypeError, binascii.Error) as exc:
        raise ValueError('Invalid OTA public key base64') from exc
    if len(decoded) != 32:
        raise ValueError('Ed25519 public key must decode to 32 bytes')
    return base64.b64encode(decoded).decode('ascii')


def prepare(tag, *, root=ROOT, public=None, repository=None):
    version = verify_release_context(tag, root, repository)
    public = validate_public_key(public if public is not None else os.getenv(KEY_VARIABLE,''))
    path = Path(root) / 'update_config.py'
    original = path.read_text(encoding='utf-8')
    replacement = f'PUBLIC_KEY_ED25519_BASE64 = {public!r}'
    replaced, count = re.subn(r'^PUBLIC_KEY_ED25519_BASE64\s*=\s*.*$', replacement,
                              original, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError('Cannot find public key setting in update_config.py')
    path.write_text(replaced, encoding='utf-8')
    return version


def is_windows_pe(exe):
    """Basic file signature sanity check; not Authenticode verification."""
    exe = Path(exe)
    if not exe.is_file() or exe.suffix.lower() != '.exe':
        return False
    with exe.open('rb') as f:
        header = f.read(64)
        if len(header) < 64 or header[:2] != b'MZ':
            return False
        pe_offset = int.from_bytes(header[60:64], 'little')
        if pe_offset < 64 or pe_offset > 16*1024*1024:
            return False
        f.seek(pe_offset)
        return f.read(4) == b'PE\x00\x00'


def sign_release(tag, *, root=ROOT, private_pem=None, public=None, repository=None, output='update.json', notes='Исправления и улучшения.'):
    version = verify_release_context(tag, root, repository)
    public = validate_public_key(public if public is not None else os.getenv(KEY_VARIABLE,''))
    private_pem = private_pem if private_pem is not None else os.getenv(KEY_SECRET,'')
    if not isinstance(private_pem, str) or not private_pem:
        raise ValueError('Missing signing secret. Refusing to publish unsigned release.')
    key = serialization.load_pem_private_key(private_pem.encode('utf-8'), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Signing key is not Ed25519')
    actual = base64.b64encode(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode('ascii')
    if actual != public:
        raise ValueError('Signing key does not match embedded public key')
    exe = Path(root) / 'installer_build' / f'SnowRunnerHelper_Setup_v{version}.exe'
    if not is_windows_pe(exe):
        raise ValueError('Installer is missing or not a Windows PE executable')
    if not (0 < exe.stat().st_size <= 1_073_741_824):
        raise ValueError('Invalid installer size')
    url = github_setup_url(OWNER, REPO, version, exe.name)
    digest = hashlib.sha256()
    with exe.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    sha = digest.hexdigest()
    payload = dict(version=version,channel='stable',url=url,sha256=sha,
                   size=exe.stat().st_size,notes=notes)
    envelope = {'payload':payload,'signature':base64.b64encode(
        key.sign(canonical_payload(payload))).decode('ascii')}
    content = (json.dumps(envelope,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    result = verify_manifest(content, public, channel='stable')
    if result.sha256 != sha:
        raise ValueError('Post-sign verification failed')
    out = Path(root) / output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(content)
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','sign'])
    parser.add_argument('--tag',required=True)
    parser.add_argument('--output',default='update.json')
    args=parser.parse_args()
    if args.action=='prepare':
        print(f'Validated release version {prepare(args.tag)}; public OTA key embedded')
    else:
        out=sign_release(args.tag,output=args.output)
        print(f'Signed and verified manifest at {out}')

if __name__=='__main__':
    main()
