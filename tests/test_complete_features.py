"""Regression checks for the final integration features."""
import unittest
from craft_overlay import parse_hotkey, MOD_ALT, MOD_CONTROL, MOD_SHIFT
from core import BUILTIN_RECIPES, CARGO_DB, display_recipe_location
from appearance import normalize

class IntegrationTests(unittest.TestCase):
    def test_hotkeys_reject_unmodified_or_invalid_key(self):
        self.assertEqual(parse_hotkey('Ctrl+Shift+F9')[0] & (MOD_CONTROL|MOD_SHIFT), MOD_CONTROL|MOD_SHIFT)
        self.assertEqual(parse_hotkey('Alt+G')[1],ord('G'))
        for text in ('F9','Ctrl','Ctrl+F14','Ctrl+A+B','bad'):
            with self.subTest(key=text),self.assertRaises(ValueError):parse_hotkey(text)

    def test_settings_keep_full_bleed_range_and_preview_separation(self):
        d=normalize({'ui_scale':80,'text_size':135,'accent':'#66BBDD'})
        self.assertEqual(d['ui_scale'],80)
        self.assertEqual(d['text_size'],135)
        self.assertEqual(d['accent'],'#66BBDD')
        self.assertTrue(d['animations'])

    def test_local_game_recipes_keep_real_map_names(self):
        self.assertGreaterEqual(len(BUILTIN_RECIPES),95)
        self.assertGreaterEqual(len(CARGO_DB),25)
        for r in BUILTIN_RECIPES:
            label=display_recipe_location(r,'ru')
            self.assertNotIn('level_',label)
            self.assertNotIn('RU_04_',label)

if __name__ == '__main__':unittest.main()
