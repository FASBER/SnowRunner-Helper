"""Route plans are application-owned; test no game save modifications."""
import tempfile
import unittest
from pathlib import Path
from profile_sync import ProfileStore

class RoutesV18Tests(unittest.TestCase):
    def test_save_update_delete_and_profile_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_game = root / 'CompleteSave.cfg'
            save_game.write_text('{"game_only":true}', encoding='utf-8')
            original = save_game.read_bytes()
            store = ProfileStore(root / 'data')
            a = store.save_route('local', 'Доставка', ['level_us_01_01', 'Промзона'],
                                 [('metal_beams', 4)], notes='Без времени')
            self.assertEqual(store.list_routes('local')[0]['stops'], ['level_us_01_01', 'Промзона'])
            self.assertEqual(store.list_routes('a'*20), [])
            with self.assertRaisesRegex(ValueError, 'already exists'):
                store.save_route('local', 'доставка', [], [])
            b = store.save_route('local', 'Доставка 2', ['Склад'], [], route_id=a['id'])
            self.assertEqual(b['id'], a['id'])
            self.assertEqual(store.list_routes('local')[0]['stops'], ['Склад'])
            store.delete_route('local', a['id'])
            self.assertEqual(store.list_routes('local'), [])
            self.assertEqual(save_game.read_bytes(), original)

    def test_bad_stops_and_missing_ids_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            store = ProfileStore(Path(td))
            original = store.save_route('local', 'Valid', ['level_us_01_01'], [])
            for stops in [['\nunsafe'], [''] , ['A'*121], ['ok']*41, 'raw']:
                with self.subTest(stops=stops), self.assertRaises(ValueError):
                    store.save_route('local', 'Bad', stops, [])
            with self.assertRaises(ValueError):
                store.save_route('local', 'Valid', ['A'], [], route_id='bad')
            self.assertEqual(len(store.list_routes('local')), 1)
            self.assertEqual(store.list_routes('local')[0]['id'], original['id'])

if __name__ == '__main__':
    unittest.main()
