"""Sign a real compiled Windows installer, yielding a manifest.json file.

Usage: python release_tools/sign_release.py private.pem Setup_v27.exe \
  https://releases.example.org/SnowRunnerHelper_Setup_v27.exe 0.27.0 manifest.json

The URL must actually serve exactly the EXE that was hashed and signed.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cryptography.hazmat.primitives import serialization
from update_security import canonical_payload, validate_https_url, version_tuple


def sign(installer, url, version, private_key_file, notes='Исправления и улучшения.',channel='stable'):
    version_tuple(version)
    validate_https_url(url)
    key=serialization.load_pem_private_key(Path(private_key_file).read_bytes(),password=None)
    path=Path(installer)
    if not path.is_file() or path.suffix.lower()!='.exe':
        raise ValueError('An actual compiled .exe installer is required')
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(262144),b''):digest.update(chunk)
    payload={'version':version,'channel':channel,'url':url,'sha256':digest.hexdigest(),
             'size':path.stat().st_size,'notes':notes}
    signature=base64.b64encode(key.sign(canonical_payload(payload))).decode('ascii')
    return {'payload':payload,'signature':signature}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('private_key_file')
    parser.add_argument('installer')
    parser.add_argument('url')
    parser.add_argument('version')
    parser.add_argument('manifest_out')
    parser.add_argument('--notes',default='Исправления и улучшения.')
    args=parser.parse_args()
    manifest=sign(args.installer,args.url,args.version,args.private_key_file,args.notes)
    Path(args.manifest_out).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Release manifest created:',args.manifest_out)
