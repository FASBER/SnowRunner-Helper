"""Run ONLY on the release maintainer's machine, OUTSIDE the published project.

Usage: python release_tools/generate_key.py C:\\private\\snowrunner_ed25519.pem
Never ship or commit the generated private PEM file.
"""
import base64
import sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate(destination):
    dest = Path(destination).expanduser().resolve()
    if dest.exists():
        raise SystemExit('Refusing to overwrite an existing private key')
    dest.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption())
    with dest.open('xb') as f:
        f.write(private_bytes)
    try: dest.chmod(0o600)
    except OSError: pass
    pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    print('ED25519 PUBLIC KEY (put in update_config.py):')
    print(base64.b64encode(pub).decode('ascii'))
    print('PRIVATE key was written outside the project; keep it offline and secret.')

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: generate_key.py <private_key_outside_project.pem>')
    generate(sys.argv[1])
