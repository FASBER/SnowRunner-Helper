"""Offline integration tests for tampering, redirects, caching and launch policy."""
import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from update_security import (canonical_payload, verify_manifest, validate_https_url,
                             version_tuple, UpdateSecurityError, Release)
from update_checker import check_for_update, UpdateNetworkError
from update_downloader import download_installer, UpdateDownloadError, file_matches
from update_launcher import launch_installer, UpdateLaunchError

URL='https://updates.example.test/SnowRunnerHelper_Setup_v0.27.1.exe'
MANIFEST_URL='https://updates.example.test/manifest.json'

class Response(io.BytesIO):
    def __init__(self, data, url=MANIFEST_URL):
        super().__init__(data);self.url=url
    def geturl(self):return self.url

class OTATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key=Ed25519PrivateKey.generate()
        cls.pub=base64.b64encode(cls.key.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode('ascii')
        cls.content=b'fictional installer contents - for tests only'

    def payload(self, **overrides):
        d={'version':'0.27.1','channel':'stable','url':URL,
           'sha256':hashlib.sha256(self.content).hexdigest(),
           'size':len(self.content),'notes':'Example update'}
        d.update(overrides)
        return d

    def signed(self, payload):
        return json.dumps({'payload':payload,
                           'signature':base64.b64encode(self.key.sign(canonical_payload(payload))).decode('ascii')}).encode()

    def release(self):return verify_manifest(self.signed(self.payload()),self.pub)

    def test_signed_manifest_accepts_known_key(self):
        self.assertEqual(self.release().version,'0.27.1')

    def test_modified_payload_is_rejected(self):
        blob=json.loads(self.signed(self.payload()))
        blob['payload']['version']='99.0.0'
        with self.assertRaises(UpdateSecurityError):verify_manifest(json.dumps(blob).encode(),self.pub)

    def test_wrong_public_key_is_rejected(self):
        wrong=base64.b64encode(Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        with self.assertRaises(UpdateSecurityError):verify_manifest(self.signed(self.payload()),wrong)

    def test_unconfigured_key_fails_closed(self):
        with self.assertRaises(UpdateSecurityError):verify_manifest(self.signed(self.payload()),'')

    def test_unsigned_missing_and_overlarge_manifest_rejected(self):
        for data in (b'{}', b'not json',b' '*70000):
            with self.subTest(data=data[:10]), self.assertRaises(UpdateSecurityError):verify_manifest(data,self.pub)

    def test_only_https_urls(self):
        for url in ('http://example.test/x.exe','file:///tmp/a.exe','https://a.test/x.exe#frag',
                    'https://someone@a.test/x.exe','https://a.test/x.exe\n','https://a.test\\x'):
            with self.subTest(url=url),self.assertRaises(UpdateSecurityError):validate_https_url(url)

    def test_signed_bad_metadata_rejected(self):
        candidates=[{'version':'0.27.1-beta'},{'size':-1},{'size':True},{'sha256':'fff'},
                    {'channel':'nightly'},{'url':'http://local/setup.exe'},{'notes':123}]
        for update in candidates:
            with self.subTest(update=update),self.assertRaises(UpdateSecurityError):
                verify_manifest(self.signed(self.payload(**update)),self.pub)

    def test_semantic_version_comparison(self):
        self.assertGreater(version_tuple('0.27.10'),version_tuple('0.27.9'))
        with self.assertRaises(UpdateSecurityError):version_tuple('1.0')

    def test_checker_only_returns_newer_updates(self):
        blob=self.signed(self.payload())
        opener=lambda req,timeout:Response(blob)
        self.assertIsNone(check_for_update(MANIFEST_URL,self.pub,'0.27.1',opener=opener))
        self.assertIsNone(check_for_update(MANIFEST_URL,self.pub,'0.31.0',opener=opener))
        self.assertEqual(check_for_update(MANIFEST_URL,self.pub,'0.27.0',opener=opener).version,'0.27.1')

    def test_checker_rejects_downgrade_redirect(self):
        with self.assertRaises(UpdateSecurityError):
            check_for_update(MANIFEST_URL,self.pub,'0.27.0',
                    opener=lambda req,timeout:Response(self.signed(self.payload()),url='http://evil/a'))

    def test_download_hash_and_cache(self):
        release=self.release()
        calls=[]
        with tempfile.TemporaryDirectory() as directory:
            def opener(req,timeout):calls.append(req);return Response(self.content,url=URL)
            path=download_installer(release,directory,opener=opener)
            self.assertTrue(file_matches(path,release))
            self.assertEqual(path.read_bytes(),self.content)
            # Cache must avoid extra download.
            self.assertEqual(download_installer(release,directory,opener=opener),path)
            self.assertEqual(len(calls),1)

    def test_download_rejects_corrupt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateDownloadError):
                download_installer(self.release(),directory,
                          opener=lambda req,timeout:Response(b'corrupted file',url=URL))
            self.assertEqual(list(Path(directory).glob('*.exe')),[])

    def test_download_rejects_redirect_to_http(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateSecurityError):
                download_installer(self.release(),directory,
                          opener=lambda req,timeout:Response(self.content,url='http://evil/f.exe'))

    def test_launcher_blocks_other_paths_and_nonwindows(self):
        with tempfile.TemporaryDirectory() as directory:
            rel=self.release()
            path=download_installer(rel,directory,
                 opener=lambda req,timeout:Response(self.content,url=URL))
            with self.assertRaises(UpdateLaunchError):launch_installer(path,rel,user_folder=directory,platform='posix')
            with self.assertRaises(UpdateSecurityError):
                launch_installer('/tmp/fake.exe',rel,user_folder=directory,platform='nt')
            calls=[]
            result=launch_installer(path,rel,user_folder=directory,platform='nt',
                      popen=lambda *args,**kw:calls.append((args,kw)) or 'LAUNCHED')
            self.assertEqual(result,'LAUNCHED')
            self.assertEqual(calls[0][0][0],[str(path)])

    def test_cancel_download_keeps_no_executable(self):
        from update_downloader import UpdateDownloadCancelled
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateDownloadCancelled):
                download_installer(self.release(),directory,
                    opener=lambda req,timeout:Response(self.content,url=URL),cancelled=lambda:True)
            self.assertFalse(list(Path(directory).iterdir()))

    def test_download_overlong_file_cannot_be_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdateDownloadError):
                download_installer(self.release(),directory,
                    opener=lambda req,timeout:Response(self.content+b'bad',url=URL))
            self.assertFalse(list(Path(directory).iterdir()))

    def test_pinned_key_and_https_must_be_set_for_production(self):
        import update_config
        self.assertEqual(update_config.CURRENT_VERSION,'0.31.0')
        self.assertEqual(update_config.RELEASE_MANIFEST_URL,'https://github.com/FASBER/SnowRunner-Helper/releases/latest/download/update.json')
        import os
        self.assertEqual(update_config.PUBLIC_KEY_ED25519_BASE64,os.getenv('OTA_ED25519_PUBLIC_BASE64',''))

    def test_game_data_remains_outside_installer(self):
        code=(Path(__file__).resolve().parent.parent/'core.py').read_text(encoding='utf8')
        self.assertIn('Path.home() / APP_NAME',code)

if __name__=='__main__':unittest.main()

# Keep cancellation semantics explicit even when an HTTP stream is interrupted.
