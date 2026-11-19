"""Tests use synthetic data, NEVER bundled copyrighted game archives."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stg_inspector import inspect_path
from official_import import import_recipes
from core import CARGO


class GameArchiveInspectionTests(unittest.TestCase):
    def test_binary_stg_is_reported_but_not_claimed_as_recipe(self):
        with tempfile.TemporaryDirectory() as home:
            path = Path(home) / 'level_us_04_02.pak'
            with zipfile.ZipFile(path, 'w') as pak:
                pak.writestr('[scene]:data.stg', b'BIN\0\1garbage\0craftSettings\0' + b'\xff' * 2048)
                pak.writestr('pak.load_list', b'\x00\x01')
                pak.writestr('level_us_04_02_brands.desc_block', b'12345')
            report = inspect_path(path)
            self.assertEqual(report['files'], 1)
            self.assertEqual(report['stg'], 1)
            self.assertEqual(report['json'], 0)
            self.assertIn('craftSettings', report['report'])
            self.assertIn('не декодирует', report['report'])
            self.assertEqual(report['results'][0]['stg_probe']['markers']['craftSettings (ASCII)'], 1)
            imported, stats = import_recipes(path, CARGO)
            self.assertEqual(imported, [])
            self.assertEqual(stats['json_candidates'], 0)

    def test_scan_folder_without_decoding_all_stg(self):
        with tempfile.TemporaryDirectory() as home:
            folder = Path(home)
            for i in range(3):
                with zipfile.ZipFile(folder / f'level_ru_{i:02d}.pak', 'w') as pak:
                    pak.writestr('[scene]:data.stg', b'hello')
            report = inspect_path(folder, lang='en')
            self.assertEqual(report['files'], 3)
            self.assertEqual(report['stg'], 3)
            self.assertTrue(all(item['stg_probe'] is None for item in report['results']))
            self.assertIn('does NOT decode STG recipes', report['report'])

    def test_standalone_stg_sample_is_bounded(self):
        with tempfile.TemporaryDirectory() as home:
            file = Path(home) / 'data.stg'
            file.write_bytes(b'\x10\x00\x00STG TEST\x00\x00')
            report = inspect_path(file)
            self.assertEqual(report['stg'], 1)
            self.assertEqual(report['results'][0]['stg_probe']['scanned_bytes'], file.stat().st_size)

    def test_json_craft_recipes_still_import_correctly(self):
        with tempfile.TemporaryDirectory() as home:
            file = Path(home) / 'level_test.pak'
            with zipfile.ZipFile(file, 'w') as archive:
                archive.writestr('zone_settings.json', ('{"zone": {"craftSettings": ['
                    '{"name":"metal_beams","craftCount":1,'
                    '"cargoComponents":[{"name":"metal_rolls","count":2}]}'
                    ']}}'))
            result = inspect_path(file)
            self.assertEqual(result['json'], 1)
            recipes, report = import_recipes(file, CARGO)
            self.assertEqual(len(recipes), 1)
            self.assertEqual(recipes[0]['inputs'], {'metal_rolls': 2})
            self.assertEqual(report['craft_entries'], 1)


if __name__ == '__main__':
    unittest.main()
