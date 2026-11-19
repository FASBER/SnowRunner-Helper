"""GitHub URLs and signed upload preparation: no live GitHub dependency."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from github_releases import github_latest_manifest_url, github_setup_url
from release_tools.prepare_github_release import prepare
from update_security import verify_manifest, UpdateSecurityError

class GitHubReleaseTests(unittest.TestCase):
    def test_latest_manifest_link(self):
        self.assertEqual(github_latest_manifest_url('sample-user', 'SnowRunner-Helper'),
            'https://github.com/sample-user/SnowRunner-Helper/releases/latest/download/update.json')

    def test_tag_pinned_download_link(self):
        self.assertEqual(github_setup_url('sample-user', 'SnowRunner-Helper', '0.28.1'),
            'https://github.com/sample-user/SnowRunner-Helper/releases/download/v0.28.1/SnowRunnerHelper_Setup_v0.28.1.exe')

    def test_invalid_repo_name_rejected(self):
        for item in ('', '../secret', 'org/repo', 'repo name', '?', '.', '..', 'x\n'):
            with self.subTest(item=item), self.assertRaises(ValueError):
                github_latest_manifest_url('user', item)

    def test_invalid_filename_and_version_rejected(self):
        for file in ('../app.exe', 'bad.exe?x', 'installer.zip', 'bad\\foo.exe', ''):
            with self.subTest(file=file), self.assertRaises(ValueError):
                github_setup_url('user', 'repo', '0.28.1', file)
        with self.assertRaises(UpdateSecurityError):
            github_setup_url('user','repo','0.28.1-rc1')

    def test_publisher_produces_verifiable_signature_without_leaking_private_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            key=Ed25519PrivateKey.generate()
            priv=root/'secret.pem'
            priv.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                         serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            pub=base64.b64encode(key.public_key().public_bytes(
                         serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
            exe=root/'SnowRunnerHelper_Setup_v0.28.1.exe'
            exe.write_bytes(b'fake binary only for test')
            manifest=root/'update.json'
            result=prepare('owner','repo','0.28.1',exe,priv,output=manifest)
            rel=verify_manifest(manifest.read_bytes(),pub)
            self.assertEqual(rel.version,'0.28.1')
            self.assertTrue(rel.url.endswith('v0.28.1/SnowRunnerHelper_Setup_v0.28.1.exe'))
            self.assertTrue(result['manifest_url'].endswith('/releases/latest/download/update.json'))
            self.assertNotIn('PRIVATE KEY',manifest.read_text(encoding='utf-8'))

    def test_configuration_defaults_off_without_repo_and_key(self):
        import update_config
        self.assertEqual(update_config.GITHUB_OWNER, 'FASBER')
        self.assertEqual(update_config.GITHUB_REPO, 'SnowRunner-Helper')
        self.assertEqual(update_config.RELEASE_MANIFEST_URL,'https://github.com/FASBER/SnowRunner-Helper/releases/latest/download/update.json')
        import os
        self.assertEqual(update_config.PUBLIC_KEY_ED25519_BASE64,os.getenv('OTA_ED25519_PUBLIC_BASE64',''))

if __name__=='__main__':unittest.main()
