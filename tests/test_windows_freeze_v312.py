"""Regression guard for v0.31.1 broken Windows _rust.pyd packaging."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parent.parent

class WindowsFrozenRuntimeChecks(unittest.TestCase):
    def test_build_uses_python_311_instead_of_py_launcher(self):
        s=(ROOT/'build_windows.bat').read_text(encoding='utf-8')
        self.assertIn('python -m venv',s)
        self.assertIn('sys.version_info[:2] == (3,11)',s)
        self.assertIn('release_tools\\verify_freeze_runtime.py',s)
        self.assertNotIn('set "PY_EXE=py"',s)

    def test_pe_check_blocks_free_threaded_python_dll(self):
        s=(ROOT/'release_tools/verify_freeze_runtime.py').read_text(encoding='utf-8')
        self.assertIn('python3t.dll',s)
        self.assertIn('pefile.PE',s)
        self.assertIn("cryptography.hazmat.bindings._rust",s)

    def test_release_requires_real_frozen_executable_smoke(self):
        workflow=(ROOT/'.github/workflows/release.yml').read_text(encoding='utf-8')
        self.assertIn('Start-Process',workflow)
        self.assertIn('--self-test',workflow)
        self.assertLess(workflow.index('Smoke-test frozen Windows EXE'),workflow.index('Build Windows installer'))
        app=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('def _self_test_frozen():',app)
        self.assertIn('Ed25519PrivateKey.generate()',app)
        self.assertIn("if sys.argv[1:] == ['--self-test']:",app)

    def test_release_version_unchanged_app_id(self):
        version=json.loads((ROOT/'version.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(version,'0.31.5')
        iss=(ROOT/'setup_snowrunner.iss').read_text(encoding='utf-8')
        self.assertIn('AppId=SnowRunnerCraftAssistant.CommunityEdition',iss)
        self.assertIn(f'SnowRunnerHelper_Setup_v{version}',iss)

if __name__=='__main__': unittest.main()
