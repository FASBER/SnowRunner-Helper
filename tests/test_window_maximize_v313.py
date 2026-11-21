"""Regression tests for the SnowRunner Helper custom maximize button."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class WindowMaximizeChecks(unittest.TestCase):
    def test_button_is_interactive_and_fullscreen_is_reversible(self):
        s=(ROOT/"game_ui.py").read_text(encoding="utf-8")
        self.assertIn("self.hit(1231,0,1268,45,self.toggle_maximize",s)
        self.assertIn("self.root.bind('<F11>'",s)
        self.assertIn("self.canvas.bind('<Double-Button-1>'",s)
        self.assertIn("self._usable_screen_area()",s)
        self.assertIn("self.restore_geometry = self.root.geometry()",s)
        self.assertIn("if self.maximized:return",s)

    def test_version(self):
        import json
        self.assertEqual(json.loads((ROOT/"version.json").read_text(encoding="utf-8"))["version"], (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip())

if __name__=="__main__":
    unittest.main()
