"""No actual installed game needed to test read-only discovery."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from game_bridge import (discover_game_archives, discover_save_slots,
                         inspect_archive, inspect_save, profile_key,
                         read_save_json, steam_libraries)


class GameBridgeTests(unittest.TestCase):
    def test_game_archive_discovery_and_scan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'SnowRunner'
            archive = root / 'preload/paks/client/initial.pak'
            archive.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('[media]/classes/trucks/truck.xml', '<Truck/>')
                z.writestr('initial.cache_block', 'hello')
            result = discover_game_archives([root], steam_roots=[])
            self.assertEqual(result, [archive.resolve()])
            self.assertEqual(inspect_archive(archive)['cache_blocks'], 1)
            self.assertEqual(inspect_archive(archive)['xml'], 1)

    def test_saved_slots_and_json_reading(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / 'CompleteSave.cfg').write_text(json.dumps({'SslValue': {'gameStat': {'a': 3}}}), encoding='utf-8')
            (folder / 'CompleteSave2.cfg').write_text(json.dumps({'CompleteSave': {'distance': 5}}), encoding='utf-8')
            (folder / 'CompleteSaveExtra.cfg').write_text('{}')
            found = discover_save_slots(extra_roots=[folder], steam_roots=[])
            self.assertEqual([x['slot'] for x in found], [1, 3])
            self.assertEqual(len({x['profile_key'] for x in found}), 2)
            self.assertEqual(inspect_save(folder / 'CompleteSave.cfg')['top_level_keys'], ['gameStat'])
            self.assertEqual(read_save_json(folder / 'CompleteSave2.cfg')['CompleteSave']['distance'], 5)

    def test_invalid_save_is_read_only_and_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'CompleteSave.dat'
            path.write_bytes(b'\x00invalid')
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                read_save_json(path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(profile_key(path), profile_key(path))

    def test_nonstandard_nan_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'CompleteSave.cfg'
            path.write_text('{"persistentProfileData":{"money":NaN}}',encoding='utf-8')
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                read_save_json(path)
            self.assertEqual(path.read_bytes(), before)

    def test_steam_libraryfolders(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vdf = root / 'steamapps/libraryfolders.vdf'
            vdf.parent.mkdir()
            vdf.write_text('"libraryfolders" { "1" { "path" "/mnt/steamgames" } }')
            self.assertEqual(steam_libraries(root)[1], Path('/mnt/steamgames'))


if __name__ == '__main__':
    unittest.main()
