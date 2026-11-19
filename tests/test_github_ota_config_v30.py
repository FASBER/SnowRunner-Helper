"""GitHub project linkage must never enable unsigned OTA releases."""
import unittest
import update_config
from update_ui import UpdaterUI
from github_releases import github_latest_manifest_url

class GitHubIntegrationTests(unittest.TestCase):
    def test_owner_repo_exact(self):
        self.assertEqual((update_config.GITHUB_OWNER, update_config.GITHUB_REPO),
                         ('FASBER', 'SnowRunner-Helper'))
        self.assertEqual(update_config.RELEASE_MANIFEST_URL,
                         github_latest_manifest_url('FASBER', 'SnowRunner-Helper'))

    def test_disabled_until_owner_installs_public_key(self):
        import os
        configured_key = os.getenv('OTA_ED25519_PUBLIC_BASE64', '')
        self.assertEqual(update_config.PUBLIC_KEY_ED25519_BASE64, configured_key)
        updater = object.__new__(UpdaterUI)
        self.assertEqual(updater.configured(), bool(configured_key))

    def test_version_consistent_with_package(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        version=json.loads((root/'version.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(update_config.CURRENT_VERSION,version)
        iss=(root/'setup_snowrunner.iss').read_text(encoding='utf-8')
        self.assertIn(f'MyAppVersion "{version}"',iss)
        self.assertIn(f'OutputBaseFilename=SnowRunnerHelper_Setup_v{version}',iss)

if __name__=='__main__':unittest.main()
