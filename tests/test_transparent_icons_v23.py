"""Regression coverage for the user-approved cargo transparency update."""
import unittest
from PIL import Image
from core import CARGO, ROOT
from icon_manager import cargo_icon_path

class TransparentBundledCargoIconsTests(unittest.TestCase):
    def test_bundled_set_covers_catalog(self):
        paths=list((ROOT/'assets'/'cargo').glob('*.png'))
        self.assertEqual(len(paths),73)
        self.assertEqual({p.stem for p in paths},set(CARGO))

    def test_bundled_icons_have_transparent_backgrounds(self):
        for path in (ROOT/'assets'/'cargo').glob('*.png'):
            with self.subTest(path=path.name),Image.open(path) as icon:
                self.assertEqual(icon.mode,'RGBA')
                self.assertEqual(icon.size,(128,96))
                self.assertEqual(icon.getpixel((0,0))[3],0)
                self.assertEqual(icon.getchannel('A').getextrema(),(0,255))

    def test_all_readers_use_shared_bundled_defaults(self):
        for cid in CARGO:
            with self.subTest(cargo=cid):
                path=cargo_icon_path(cid,user_folder=ROOT/'not-present-test-custom-icons')
                self.assertEqual(path,ROOT/'assets'/'cargo'/f'{cid}.png')

if __name__ == '__main__': unittest.main()
