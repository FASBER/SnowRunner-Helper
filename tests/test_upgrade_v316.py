"""v0.31.16 regression checks — only Python stdlib unittest (CI-compatible)."""
import json
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from player_identity_v316 import _persona_from_vdf, _steam_id_from_save_path, display_profile
from hotkey_upgrade_v316 import pressed_modifiers
from vehicle_catalog_v316 import (index_archive, fleet_from_save,
                                  scan_and_cache_catalog, read_cached_catalog,
                                  evidence_image_path)
from changelog_ui_v316 import load_notes


class UpgradeV316Checks(unittest.TestCase):
    def test_identity_not_a_fake_steam_name(self):
        app = SimpleNamespace(active_profile_key='profile-hash', config={}, profiles=SimpleNamespace(
            read=lambda key: {'source_path': 'C:/NotSteam/CompleteSave2.cfg'}))
        self.assertEqual(display_profile(app), 'Steam · слот 3')
        app.config['profile_display_names'] = {'profile-hash': 'Зимний водитель'}
        self.assertEqual(display_profile(app), 'Зимний водитель')

    def test_steam_persona_exact_id(self):
        sid = '76561197960265729'
        p = Path('C:/Steam/userdata/1/1465360/remote/CompleteSave.cfg')
        self.assertEqual(_steam_id_from_save_path(p), sid)
        vdf = ('"users" { "' + sid + '" { "PersonaName" "Tester" } '
               '"76561197960265730" { "PersonaName" "Wrong" } }')
        self.assertEqual(_persona_from_vdf(vdf, sid), 'Tester')
        self.assertIsNone(_persona_from_vdf(vdf, '76561197960265731'))

    def test_combo_shift_control_and_win(self):
        ev = SimpleNamespace(state=0x0001 | 0x0004)
        self.assertEqual(pressed_modifiers(ev), ['Ctrl', 'Shift'])
        self.assertEqual(pressed_modifiers(SimpleNamespace(state=0),
                                           lambda vk: vk in (0xA2, 0xA0, 0x5B)),
                         ['Ctrl', 'Shift', 'Win'])

    def test_real_catalog_from_xml_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fake = folder / 'initial.pak'
            with zipfile.ZipFile(fake, 'w') as z:
                z.writestr('[media]/classes/trucks/truck_4x4.xml', 'x'*100)
                z.writestr('[media]/classes/trailers/trailer_2.xml', '')
                z.writestr('[media]/classes/trailers/semitrailer_heavy.xml', '')
                z.writestr('[media]/classes/truck_addons/flatbed.xml', '')
                z.writestr('[media]/textures/random.xml', '')
            catalog = index_archive(fake)
            self.assertEqual({(i['id'], i['category']) for i in catalog}, {
                ('truck_4x4', 'truck'), ('trailer_2', 'trailer'),
                ('semitrailer_heavy', 'semitrailer'), ('flatbed', 'addon')})
            self.assertEqual(scan_and_cache_catalog(fake, folder), catalog)
            self.assertEqual(read_cached_catalog(folder), catalog)
            self.assertIsNone(evidence_image_path('truck_4x4', 'truck', folder, folder))

    def test_fleet_uses_only_actual_save_records(self):
        payload = {
            'persistentProfileData': {'trucksInWarehouse': [
                {'type': 'kenworth_963'}, {'type': 'tayga_6455b'}]},
            'garagesData': {'US_01_01': {'slotsDatas': {
                'slot1': {'truckDesc': {'type': 'azov_73210'}},
                'slot2': {'truckDesc': None}}}},
            'modTruckOnLevels': [{'type': 'not_known_to_be_owned'}]
        }
        fleet = fleet_from_save({'CompleteSave2': {'SslValue': payload}})
        self.assertEqual(len(fleet), 3)
        self.assertTrue(any(x['id'] == 'azov_73210' and
                            x['where'].startswith('Гараж:') for x in fleet))
        self.assertNotIn('not_known_to_be_owned', [x['id'] for x in fleet])

    def test_changelog_collapsible_notes_and_version(self):
        notes = load_notes(ROOT)
        self.assertEqual(notes[0]['version'],
                         json.loads((ROOT / 'version.json').read_text(encoding='utf-8'))['version'])
        self.assertIn('Исправлено', notes[0]['sections'])

    def test_weight_sort_missing_last(self):
        import expedition_upgrade_v316 as up
        stub = types.ModuleType('core')
        stub._sort_name = lambda x, lang: x['id']
        stub.sort_cargo = lambda items, mode, lang: sorted(items, key=lambda x: x['id'])
        records = [{'id': 'x_unknown'}, {'id': 'bricks'}, {'id': 'metal_beams'}]
        with patch.dict(sys.modules, {'core': stub}):
            sorted_rows = up.sort_entries(records, 'weight_asc', 'ru')
            self.assertEqual(sorted_rows[-1]['id'], 'x_unknown')
            self.assertEqual({r['id'] for r in sorted_rows[:-1]}, {'bricks', 'metal_beams'})
            self.assertEqual(up.sort_entries(records, 'weight_desc', 'ru')[-1]['id'], 'x_unknown')

    def test_image_quality_checker_flags_missing_not_fake(self):
        from image_quality_audit_v316 import audit_folder
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'cargo'
            folder.mkdir()
            Image.new('RGBA', (32, 32), (0, 0, 0, 0)).save(folder / 'bricks.png')
            report = audit_folder(folder, ('bricks', 'metal_beams'))
            self.assertEqual(report['missing'], ['metal_beams'])
            self.assertEqual(report['transparent_capable'], 1)
            self.assertEqual(report['4k_by_pixel_count'], 0)

    def test_release_metadata_synchronized(self):
        release = json.loads((ROOT / 'version.json').read_text(encoding='utf-8'))
        version = release['version']
        self.assertEqual((ROOT / 'VERSION.txt').read_text().strip(), version)
        self.assertIn(version, (ROOT / 'setup_snowrunner.iss').read_text())
        self.assertIn(version, (ROOT / 'build_installer_windows.bat').read_text())

    def test_ui_settings_button_hit_areas_inside_workplace(self):
        import expedition_upgrade_v316 as up
        fakeappearance = types.ModuleType('appearance')
        fakeappearance.PRESETS = {'snow': {'ru': 'Снежный конвой', 'en': 'Snow convoy'}}
        coords = []

        class Fake:
            reference_ui = True
            lang = 'ru'
            appearance = {'preset': 'snow'}
            app = SimpleNamespace(config={'theme':'game','ui_scale':100,'text_size':100},
                updater=SimpleNamespace(open_settings=lambda: None),
                overlay=SimpleNamespace(shortcut='Ctrl+Shift+F9',toggle=lambda: None,
                    shortcut_dialog=lambda: None),
                appearance_editor=lambda: None, game_connection_dialog=lambda: None,
                recipe_editor=lambda: None, adjust=lambda *args: None)
            def round(self, *args): pass
            def line(self, *args): pass
            def txt(self, *args, **kwargs): pass
            def button(self, x1, y1, x2, y2, *args, **kwargs):
                coords.append((x1,y1,x2,y2))
            def about_dialog(self): pass
            def cycle_theme(self): pass
            def change(self, *args): pass

        with patch.dict(sys.modules, {'appearance': fakeappearance}):
            up._draw_settings(Fake())
        self.assertGreaterEqual(len(coords), 12)
        self.assertTrue(all(200 <= a < c <= 1290 and 179 <= b < d <= 713
                            for a,b,c,d in coords))


if __name__ == '__main__':
    unittest.main()
