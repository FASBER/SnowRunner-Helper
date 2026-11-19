import unittest
from core import REGIONS,BUILTIN_RECIPES,display_region,display_recipe_location,display_recipe_notes,filter_recipes

class MapNamesTests(unittest.TestCase):
    def test_all_builtin_maps_have_real_localized_names(self):
        self.assertEqual(len(BUILTIN_RECIPES),100)
        for recipe in BUILTIN_RECIPES:
            for language in ('ru','en'):
                display=display_recipe_location(recipe,language)
                self.assertIn(' → ',display)
                self.assertNotIn('level_',display)
                self.assertNotIn(recipe['region'],display)
                self.assertNotIn(recipe.get('game_zone',''),display)
                self.assertNotIn('Карта ',display)
                self.assertNotIn('Unknown map',display)
                self.assertNotIn('level_',display_recipe_notes(recipe,language))
    def test_known_and_unknown(self):
        self.assertEqual(display_region('level_ru_04_01','ru'),'Амур → Река Урска')
        self.assertEqual(display_region('level_ru_04_01','en'),'Amur → Urska River')
        self.assertEqual(display_region('level_us_99_99','ru'),'Карта не определена')
        self.assertEqual(display_region('level_us_99_99','en'),'Unknown map')
    def test_search_by_friendly_name(self):
        rus=filter_recipes(BUILTIN_RECIPES, query='река урска',lang='ru')
        eng=filter_recipes(BUILTIN_RECIPES, query='urska',lang='en')
        self.assertEqual(len(rus),4)
        self.assertEqual(len(eng),4)
        self.assertTrue(all(x['region']=='level_ru_04_01' for x in rus))
    def test_duplicate_map_field_is_ignored(self):
        r={'region':'level_us_03_01','map':'level_us_03_01'}
        self.assertEqual(display_recipe_location(r,'ru'),'Висконсин → Блэк Бэджер Лейк')
    def test_imported_notes_hide_zone(self):
        r={'verified':'local_game_data','notes':{'ru':'Зона: US_04_01_TEST'},'game_zone':'US_04_01_TEST'}
        self.assertNotIn('US_04',display_recipe_notes(r,'ru'))
