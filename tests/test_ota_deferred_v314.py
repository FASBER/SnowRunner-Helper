"""Regression coverage for background hand-off before installing on Windows."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from update_launcher import (launch_installer, _deferred_script, _ps_literal,
                             UpdateLaunchError)
from update_security import Release, UpdateSecurityError


class DeferredOTATests(unittest.TestCase):
    def release(self, data):
        return Release(version='0.31.15', channel='stable',
                       url='https://github.com/FASBER/SnowRunner-Helper/releases/download/v0.31.15/SnowRunnerHelper_Setup_v0.31.15.exe',
                       sha256=hashlib.sha256(data).hexdigest(), size=len(data),
                       notes='Deferred OTA installer')

    def test_wait_for_old_exe_and_reverify_hash_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            data=b'legitimate test installer content'
            setup=Path(directory)/'SnowRunnerHelper_Setup_v0.31.15.exe'
            setup.write_bytes(data)
            calls=[]
            release=self.release(data)
            launched=launch_installer(setup, release, user_folder=directory, platform='nt',
                parent_pid=9123, powershell_exe='C:/Windows/WindowsPowerShell/powershell.exe',
                popen=lambda *args, **kwargs: calls.append((args,kwargs)) or 'started')
            self.assertEqual(launched, 'started')
            cmd=calls[0][0][0]
            self.assertEqual(cmd[0].replace('\\', '/'), 'C:/Windows/WindowsPowerShell/powershell.exe')
            self.assertIn('-EncodedCommand',cmd)
            ps=base64.b64decode(cmd[-1]).decode('utf-16le')
            self.assertIn('$parentProcessId = 9123',ps)
            self.assertIn('$bootloaderProcessId = 0',ps)
            self.assertLess(ps.index('Get-Process -Id $processIdToWait'),ps.index('Start-Process -FilePath'))
            self.assertLess(ps.index('Get-FileHash -LiteralPath'),ps.index('Start-Process -FilePath'))
            self.assertIn(release.sha256,ps)
            self.assertIn('ota_launch_error.txt',ps)
            self.assertNotIn('shell',calls[0][1])

    def test_pyinstaller_bootloader_parent_is_also_waited_for(self):
        script=_deferred_script('C:/a.exe',123,10,'a'*64,'C:/error.txt',bootloader_pid=456)
        self.assertIn('$parentProcessId = 123',script)
        self.assertIn('$bootloaderProcessId = 456',script)
        self.assertIn('$waitingPids += $bootloaderProcessId',script)
        self.assertIn('foreach ($processIdToWait in $waitingPids)',script)

    def test_tampered_installer_never_starts(self):
        with tempfile.TemporaryDirectory() as directory:
            data=b'legitimate test installer content'
            setup=Path(directory)/'SnowRunnerHelper_Setup_v0.31.15.exe'
            setup.write_bytes(data+b'tampering')
            calls=[]
            with self.assertRaises(UpdateSecurityError):
                launch_installer(setup,self.release(data),user_folder=directory,
                    platform='nt',parent_pid=42,powershell_exe='powershell.exe',
                    popen=lambda *args,**kw:calls.append(1))
            self.assertEqual(calls,[])

    def test_path_injection_is_quoted_not_executed(self):
        path=r"C:\User's folder\x; Start-Process evil.exe\file.exe"
        escaped=_ps_literal(path)
        self.assertTrue(escaped.startswith("'C:"))
        self.assertIn("User''s folder",escaped)
        script=_deferred_script(path,123,12,'a'*64,'logfile')
        self.assertIn("User''s folder",script)

    def test_reject_non_windows_and_invalid_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            data=b'x'
            setup=Path(directory)/'SnowRunnerHelper_Setup_v0.31.15.exe'
            setup.write_bytes(data)
            rel=self.release(data)
            with self.assertRaises(UpdateLaunchError):
                launch_installer(setup,rel,user_folder=directory,platform='posix')
            with self.assertRaises(UpdateLaunchError):
                launch_installer(setup,rel,user_folder=directory,platform='nt',
                    parent_pid=-1,popen=lambda *a,**k:None)


if __name__=='__main__': unittest.main()
