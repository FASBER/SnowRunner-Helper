import unittest
from pathlib import Path
from core import CARGO, BUILTIN_RECIPES, validate_recipe
from cache_craft import game_recipes_from_cache

class VerifiedCacheTests(unittest.TestCase):
    def test_builtins_derived_and_valid(self):
        self.assertEqual(len(BUILTIN_RECIPES),100)
        for r in BUILTIN_RECIPES:
            self.assertTrue(validate_recipe(r))
            self.assertNotIn('PROG_SANDBOX',r['game_zone'])
            self.assertTrue(r['map'].startswith('level_'))
    def test_energy_recipe_present(self):
        self.assertTrue(any(r['energy'] and not r['inputs'] for r in BUILTIN_RECIPES))
    def test_no_invented_ingredients(self):
        self.assertTrue(any(r['inputs'].get('metal_rolls')==2 and r['outputs'].get('metal_beams')==1 for r in BUILTIN_RECIPES))

if __name__=='__main__':unittest.main()
