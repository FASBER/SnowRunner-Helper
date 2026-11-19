"""Asset completeness and motion tests for v0.4."""
import unittest
from pathlib import Path
from core import ROOT, CARGO_DB, BUILTIN_RECIPES
from app import Application

class AssetTests(unittest.TestCase):
    def test_full_current_database_has_icons(self):
        cargo_dir=ROOT/'assets'/'cargo'
        recipe_dir=ROOT/'assets'/'recipes'
        for item in CARGO_DB:
            with self.subTest(cargo=item['id']):
                self.assertTrue((cargo_dir/f"{item['id']}.png").exists())
        for recipe in BUILTIN_RECIPES:
            with self.subTest(recipe=recipe['id']):
                self.assertTrue((recipe_dir/f"{recipe['id']}.png").exists())
        self.assertEqual(len(list(cargo_dir.glob('*.png'))), len(CARGO_DB))
        self.assertEqual(len(list(recipe_dir.glob('*.png'))), len(BUILTIN_RECIPES))

    def test_eased_color_lerp(self):
        self.assertEqual(Application.mix('#000000','#FFFFFF',0),'#000000')
        self.assertEqual(Application.mix('#000000','#FFFFFF',1),'#FFFFFF')
        self.assertEqual(Application.mix('#000000','#FFFFFF',.5),'#808080')
        self.assertEqual(Application.mix('#000000','#FFFFFF',-20),'#000000')

if __name__=='__main__':unittest.main()
