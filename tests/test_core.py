import unittest
from core import CARGO_DB, SORT_MODES, calculate_load, cargo_slots, sort_cargo


class CargoSortTests(unittest.TestCase):
    def test_all_sort_options_return_all_items_without_mutating_input(self):
        original = list(CARGO_DB)
        for lang in ('ru', 'en'):
            for mode in SORT_MODES:
                with self.subTest(language=lang, sort_mode=mode):
                    ordered = sort_cargo(original, mode, lang)
                    self.assertEqual(len(ordered), len(original))
                    self.assertEqual({e['id'] for e in ordered}, {e['id'] for e in original})
                    self.assertEqual(original, CARGO_DB)

    def test_slot_order_both_directions_and_unknown_last(self):
        for mode, reverse in [('slots_asc', False), ('slots_desc', True)]:
            for lang in ('ru', 'en'):
                items = sort_cargo(CARGO_DB, mode, lang)
                slots = [x['slots'] for x in items if x['slots'] is not None]
                self.assertEqual(slots, sorted(slots, reverse=reverse))
                self.assertEqual([x['slots'] is None for x in items],
                                 sorted([x['slots'] is None for x in items]))

    def test_alphabetical_order_both_languages(self):
        cases = [
            ('ru', ['Ящик', 'Ёлка', 'Енот', 'Берёза'], ['Берёза','Енот','Ёлка','Ящик']),
            ('en', ['Zebra','alpha','Berry','Echo'], ['alpha','Berry','Echo','Zebra']),
        ]
        for lang, names, expected in cases:
            entries = [{'id':str(i),lang:n,'slots':1} for i,n in enumerate(names)]
            self.assertEqual([e[lang] for e in sort_cargo(entries,'name_asc',lang)], expected)
            self.assertEqual([e[lang] for e in sort_cargo(entries,'name_desc',lang)], expected[::-1])

    def test_sort_by_slots_equal_size_alphabetical(self):
        entries = [{'id':str(i), 'ru':name, 'slots':size} for i,(name,size) in
                   enumerate([('Ящик',2),('Блоки',2),('Груз',1)])]
        self.assertEqual([e['ru'] for e in sort_cargo(entries,'slots_desc','ru')],
                         ['Блоки','Ящик','Груз'])

    def test_search_results_can_be_sorted(self):
        entries = [e for e in CARGO_DB if 'бетон' in e['ru'].casefold()]
        self.assertTrue(entries)
        self.assertEqual({e['id'] for e in sort_cargo(entries,'name_desc','ru')},
                         {e['id'] for e in entries})

    def test_load_planner_unchanged(self):
        self.assertEqual(calculate_load([('metal_beams',2),('wooden_planks',1)]), 5)
        self.assertEqual(cargo_slots('metal_beams'), 2)
        with self.assertRaises(ValueError): calculate_load([('metal_beams',0)])


if __name__ == '__main__': unittest.main()
