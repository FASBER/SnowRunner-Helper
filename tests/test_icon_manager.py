"""Persistence and validation regression checks; no Tk needed."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from core import CARGO
from icon_manager import cargo_icon_path, has_custom_icon, install_cargo_icon, reset_cargo_icon

class CargoIconTests(unittest.TestCase):
    ID = 'metal_beams'

    def test_import_png_and_restore(self):
        with TemporaryDirectory() as td:
            path=Path(td); src=path/'test.png'; store=path/'my_icons'; bundled=path/'bundled'
            Image.new('RGBA',(900,450),(220,35,70,100)).save(src)
            bundled.mkdir()
            Image.new('RGBA',(24,24),(10,10,10,255)).save(bundled/f'{self.ID}.png')
            self.assertEqual(cargo_icon_path(self.ID,store,bundled),bundled/f'{self.ID}.png')
            result=install_cargo_icon(self.ID,src,store)
            self.assertEqual(result,store/f'{self.ID}.png')
            self.assertTrue(has_custom_icon(self.ID,store))
            self.assertEqual(cargo_icon_path(self.ID,store,bundled),result)
            with Image.open(result) as icon:
                self.assertEqual(icon.format,'PNG')
                self.assertLessEqual(max(icon.size),768)
                self.assertEqual(icon.mode,'RGBA')
                self.assertEqual(icon.getpixel((0,0))[3],100)
            self.assertTrue(reset_cargo_icon(self.ID,store))
            self.assertFalse(has_custom_icon(self.ID,store))
            self.assertEqual(cargo_icon_path(self.ID,store,bundled),bundled/f'{self.ID}.png')
            self.assertFalse(reset_cargo_icon(self.ID,store))

    def test_import_additional_formats(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            for ext in ('jpg','jpeg','webp'):
                source=root/f'new.{ext}'
                Image.new('RGB',(50,30),(123,45,67)).save(source)
                icon=install_cargo_icon(self.ID,source,root/'my_icons')
                with Image.open(icon) as picture:
                    self.assertEqual(picture.size,(50,30))
                    self.assertEqual(picture.format,'PNG')

    def test_unknown_or_invalid_rejected(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(ValueError):
                install_cargo_icon('does_not_exist',root/'any.png',root/'my_icons')
            bad=root/'bad.png';bad.write_bytes(b'not an image')
            with self.assertRaises(ValueError):
                install_cargo_icon(self.ID,bad,root/'my_icons')
            unsupported=root/'bad.svg';unsupported.write_text('<svg/>')
            with self.assertRaises(ValueError):
                install_cargo_icon(self.ID,unsupported,root/'my_icons')
            with self.assertRaises(ValueError):
                reset_cargo_icon('wrong',root/'my_icons')
            self.assertIn(self.ID,CARGO)

if __name__=='__main__': unittest.main()
