"""Workflow and signer regression tests without network or GitHub secrets."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from release_tools.gha_release_helper import (
    verify_release_context, validate_public_key, prepare, sign_release, is_windows_pe)
from update_security import verify_manifest

ROOT = Path(__file__).resolve().parent.parent

class GitHubActionsChecks(unittest.TestCase):
    def test_workflows_exist_and_require_tag_to_release(self):
        release = (ROOT/'.github/workflows/release.yml').read_text(encoding='utf-8')
        ci = (ROOT/'.github/workflows/checks.yml').read_text(encoding='utf-8')
        self.assertIn('push:', ci)
        self.assertIn('pull_request:', ci)
        self.assertNotIn('pull_request:', release)
        self.assertIn('tags:', release)
        self.assertIn('contents: write', release)
        self.assertIn('OTA_ED25519_PRIVATE_PEM', release)
        self.assertIn('gh release create', release)
        self.assertIn('choco install innosetup', release)
        self.assertIn('github.repository ==',release)

    def make_root(self, temp):
        root=Path(temp)
        (root/'version.json').write_text('{"version":"0.31.0"}',encoding='utf-8')
        (root/'setup_snowrunner.iss').write_text('#define MyAppVersion "0.31.0"\nOutputBaseFilename=SnowRunnerHelper_Setup_v0.31.0\n',encoding='utf-8')
        (root/'update_config.py').write_text("PUBLIC_KEY_ED25519_BASE64 = ''\n",encoding='utf-8')
        (root/'installer_build').mkdir()
        return root

    def test_tag_and_repository_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make_root(d)
            self.assertEqual(verify_release_context('v0.31.0',root,repository='FASBER/SnowRunner-Helper'),'0.31.0')
            for tag, repo in [('v0.31.1','FASBER/SnowRunner-Helper'),('v0.31.0','evil/SnowRunner-Helper')]:
                with self.subTest(tag=tag,repo=repo),self.assertRaises(ValueError):
                    verify_release_context(tag,root,repository=repo)

    def test_invalid_public_key_rejected(self):
        for key in ('', 'not-base64', base64.b64encode(b'bad').decode()):
            with self.subTest(key=key),self.assertRaises(ValueError):validate_public_key(key)

    def test_no_unsigned_or_wrong_key_release(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make_root(d)
            key=Ed25519PrivateKey.generate()
            private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()).decode()
            public=base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,
                                        serialization.PublicFormat.Raw)).decode()
            prepare('v0.31.0',root=root,public=public)
            self.assertIn(public,(root/'update_config.py').read_text())
            exe=root/'installer_build/SnowRunnerHelper_Setup_v0.31.0.exe'
            with self.assertRaises(ValueError): sign_release('v0.31.0',root=root,private_pem=private,public=public)
            exe.write_bytes(b'NOT_WINDOWS_PE')
            self.assertFalse(is_windows_pe(exe))
            with self.assertRaises(ValueError):sign_release('v0.31.0',root=root,private_pem=private,public=public)
            raw=bytearray(128);raw[0:2]=b'MZ';raw[60:64]=(64).to_bytes(4,'little');raw[64:68]=b'PE\0\0'
            exe.write_bytes(raw)
            self.assertTrue(is_windows_pe(exe))
            wrong=base64.b64encode(Ed25519PrivateKey.generate().public_key().public_bytes(
                serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
            with self.assertRaises(ValueError):sign_release('v0.31.0',root=root,private_pem=private,public=wrong)
            manifest=sign_release('v0.31.0',root=root,private_pem=private,public=public)
            release=verify_manifest(manifest.read_bytes(),public)
            self.assertEqual(release.url,'https://github.com/FASBER/SnowRunner-Helper/releases/download/v0.31.0/SnowRunnerHelper_Setup_v0.31.0.exe')
            self.assertEqual(release.version,'0.31.0')
            self.assertNotIn('PRIVATE KEY',manifest.read_text())

    def test_no_secret_in_existing_files(self):
        import os
        from update_config import PUBLIC_KEY_ED25519_BASE64
        self.assertEqual(PUBLIC_KEY_ED25519_BASE64, os.getenv('OTA_ED25519_PUBLIC_BASE64',''))

if __name__=='__main__':unittest.main()
