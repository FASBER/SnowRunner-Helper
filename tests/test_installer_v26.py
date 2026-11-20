"""Non-Windows checks for the native Windows installation scenario."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
ISS = (ROOT/'setup_snowrunner.iss').read_text(encoding='utf-8-sig')

def value(key):
    for line in ISS.splitlines():
        if line.lower().startswith(key.lower()+'='):
            return line.partition('=')[2].strip()
    return None

class InstallerChecks(unittest.TestCase):
    def test_selectable_install_directory(self):
        self.assertEqual(value('DisableDirPage'), 'no')
        self.assertEqual(value('UsePreviousAppDir'), 'yes')
        self.assertIn('{localappdata}', value('DefaultDirName').lower())
        self.assertEqual(value('PrivilegesRequired'), 'lowest')
    def test_user_data_not_purged(self):
        active = '\n'.join(x.strip() for x in ISS.splitlines() if x.strip() and not x.lstrip().startswith(';'))
        self.assertNotIn('[UninstallDelete]', active)
        self.assertIn('[InstallDelete]', active)
        self.assertIn('Name: "{app}\\SnowRunnerCraftAssistant.exe"',active)
        self.assertNotIn('Type: dirifempty; Name: "{userappdata}',active)
        self.assertNotIn('Type: filesandordirs; Name: "{userprofile}',active)
        data = (ROOT/'core.py').read_text(encoding='utf-8')
        self.assertIn('Path.home() / APP_NAME', data)
    def test_reliable_upgrade_identity(self):
        self.assertEqual(value('AppId'), 'SnowRunnerCraftAssistant.CommunityEdition')
        self.assertIn('dist\\{#MyAppExeName}', ISS)
        self.assertIn('ignoreversion', ISS)
    def test_branding_included(self):
        for path in ('installer_assets/wizard_side.bmp','installer_assets/wizard_small.bmp', 'app_icon.ico'):
            self.assertTrue((ROOT/path).is_file())
    def test_two_stage_windows_builder(self):
        builder=(ROOT/'build_installer_windows.bat').read_text(encoding='utf-8')
        self.assertIn('call build_windows.bat', builder)
        self.assertIn('setup_snowrunner.iss',builder)
        self.assertIn('installer_build\\SnowRunnerHelper_Setup_v0.31.8.exe', builder)

if __name__=='__main__': unittest.main()
