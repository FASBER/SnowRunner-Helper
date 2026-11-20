"""Regression tests: user-facing rename must not lose existing installs or game profiles."""
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

class RenameChecks(unittest.TestCase):
    def test_product_version_and_window_title(self):
        release=json.loads((ROOT/'version.json').read_text(encoding='utf-8'))
        self.assertEqual(release['name'],'SnowRunner Helper')
        self.assertEqual(release['version'],'0.31.7')
        self.assertIn("root.title('SnowRunner Helper'",(ROOT/'game_ui.py').read_text(encoding='utf-8'))

    def test_install_upgrade_preserves_identity_and_custom_path(self):
        iss=(ROOT/'setup_snowrunner.iss').read_text(encoding='utf-8')
        self.assertIn('AppId=SnowRunnerCraftAssistant.CommunityEdition',iss)
        self.assertIn('AppName={#MyAppName}',iss)
        self.assertIn('#define MyAppName "SnowRunner Helper"',iss)
        self.assertIn('UsePreviousAppDir=yes',iss)
        self.assertIn('DefaultDirName={localappdata}\\Programs\\SnowRunner Helper',iss)
        self.assertIn('Name: "{app}\\SnowRunnerCraftAssistant.exe"',iss)
        self.assertNotIn('[UninstallDelete]', '\n'.join(line for line in iss.splitlines() if not line.strip().startswith(';')))

    def test_player_data_remains_in_prior_folder(self):
        core=(ROOT/'core.py').read_text(encoding='utf-8')
        self.assertIn("APP_NAME = 'SnowRunnerCraftAssistant'",core)
        self.assertIn('Path.home() / APP_NAME',core)

    def test_new_distribution_and_update_names_are_consistent(self):
        builder=(ROOT/'build_windows.bat').read_text(encoding='utf-8')
        self.assertIn('--name "SnowRunnerHelper"',builder)
        iss=(ROOT/'setup_snowrunner.iss').read_text(encoding='utf-8')
        self.assertIn('SnowRunnerHelper_Setup_v0.31.7',iss)
        self.assertIn("f'SnowRunnerHelper_Setup_v{release.version}.exe'",(ROOT/'update_downloader.py').read_text(encoding='utf-8'))
        self.assertIn("f'SnowRunnerHelper_Setup_v{release.version}.exe'",(ROOT/'update_launcher.py').read_text(encoding='utf-8'))
        self.assertIn("f'SnowRunnerHelper_Setup_v{version}.exe'",(ROOT/'github_releases.py').read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
