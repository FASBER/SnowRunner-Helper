"""Regression checks for first launch after OTA upgrade to 0.31.13.

These tests verify source/script contracts. Inno Setup compilation and a real
Windows OTA installation must also be tested on GitHub and the user's PC.
"""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parent.parent

class OTAPostinstallChecks(unittest.TestCase):
    def setUp(self):
        self.iss = (ROOT / 'setup_snowrunner.iss').read_text(encoding='utf-8')
        self.launcher = (ROOT / 'update_launcher.py').read_text(encoding='utf-8')

    def test_new_version_metadata(self):
        self.assertEqual(json.loads((ROOT/'version.json').read_text(encoding='utf-8'))['version'], '0.31.13')
        self.assertIn('#define MyAppVersion "0.31.13"', self.iss)

    def test_autolaunch_is_not_unconditional(self):
        run_line = next(line for line in self.iss.splitlines() if line.startswith('Filename: "{app}\\{#MyAppExeName}"; Description:'))
        self.assertIn('postinstall', run_line)
        self.assertIn('Check: ShouldOfferLaunchOnFinish', run_line)
        self.assertIn('Result := not IsOtaInstall();',self.iss)

    def test_old_ota_client_detected_by_installer_location(self):
        self.assertIn("GetEnv('USERPROFILE')",self.iss)
        self.assertIn('SnowRunnerCraftAssistant\\updates', self.iss)
        self.assertIn("CompareText(ExpandConstant('{src}'), UpdateDir) = 0",self.iss)

    def test_explicit_ota_marker_for_next_clients(self):
        self.assertIn("CompareText(ParamStr(I), '/OTA=1') = 0", self.iss)
        self.assertIn("-ArgumentList '/OTA=1'",self.launcher)
        self.assertIn("Get-FileHash -LiteralPath",self.launcher)

    def test_manual_install_keeps_postinstall_choice(self):
        self.assertIn('function ShouldOfferLaunchOnFinish(): Boolean;', self.iss)
        self.assertIn('Result := not IsOtaInstall();',self.iss)
        self.assertNotIn('Flags: nowait postinstall skipifsilent unchecked',self.iss)

    def test_log_created_only_when_ota_is_done(self):
        self.assertIn('CurStep <> ssDone',self.iss)
        self.assertIn('ota_setup_status_v{#MyAppVersion}.txt',self.iss)
        self.assertIn('OTA Setup v{#MyAppVersion} completed;',self.iss)
        # Never hard-code a release number in the OTA status marker again.
        self.assertNotRegex(self.iss, r'ota_setup_status_v\d+\.\d+\.\d+\.txt')
        self.assertIn('SaveStringToFile',self.iss)
        self.assertIn('ota_launch_error.txt',self.launcher)

    def test_profiles_unmodified_and_previous_install_dir_reused(self):
        self.assertIn('UsePreviousAppDir=yes',self.iss)
        self.assertIn('AppId=SnowRunnerCraftAssistant.CommunityEdition',self.iss)
        self.assertFalse(any(line.strip() == '[UninstallDelete]' for line in self.iss.splitlines()))

    def test_unchanged_windows_exe_validation(self):
        self.assertIn('file_matches(target, release)',self.launcher)
        self.assertIn("Downloaded installer SHA-256 changed after application exit.",self.launcher)

if __name__ == '__main__': unittest.main()
