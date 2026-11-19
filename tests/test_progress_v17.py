"""Synthetic save fixtures only: no genuine user saves used or changed."""
import json
import tempfile
import unittest
from pathlib import Path

from game_bridge import profile_key
from profile_sync import ProfileStore, extract_snapshot, snapshot_save


class ProgressV17Tests(unittest.TestCase):
    @staticmethod
    def sample():
        return {'CompleteSave': {'SslType': 'SaveObject', 'SslValue': {
            'persistentProfileData': {'money': 400, 'experience': 300,
                                      'trucksInWarehouse': [{'type': 'western_star_49x'}]},
            'objectiveStates': {'TASK_NEW': {'isFinished': False}},
            'finishedObjs': ['TASK_A', 'TASK_B', 'TASK_A'],
            'visitedLevels': ['level_us_01_02', 'level_us_01_01'],
            'levelGarageStatuses': {'level_us_01_01': 2, 'level_us_01_02': 0,
                                     'level_us_01_03': 1},
            'levelStates': {'level_us_01_02': {
                'warehouse_us_01_02_1': {'cargoAvailable': {
                    'mediumPlanks': 2, 'metalBeams': 10, 'metalRolls': -1, 'other': True}}}},
        }}}

    def test_known_progress_and_completions(self):
        p = extract_snapshot(self.sample())
        self.assertEqual(p['objectives']['completed'], 2)
        self.assertEqual(p['objectives']['finished_ids'], ['TASK_A', 'TASK_B'])
        self.assertEqual(p['objectives']['known_entries'], 1)
        self.assertEqual(p['visited_levels']['count'], 2)
        self.assertEqual(p['garages']['open_count'], 1)
        self.assertEqual(p['garages']['statuses']['level_us_01_03'], 1)
        self.assertEqual(p['retained_trucks']['count'], 1)

    def test_candidate_warehouses_are_explicitly_unverified(self):
        depots = extract_snapshot(self.sample())['cargo_depots']
        self.assertTrue(depots['available'])
        self.assertFalse(depots['verified'])
        self.assertEqual(depots['count'], 1)
        item = depots['candidates'][0]
        self.assertEqual(item['warehouse_id'], 'warehouse_us_01_02_1')
        self.assertEqual(item['cargo'], {'mediumPlanks': 2, 'metalBeams': 10, 'metalRolls': -1})
        self.assertNotIn('other', item['cargo'])

    def test_candidate_with_id_on_facility(self):
        value = {'SslValue': {'persistentProfileData': {},
                             'levelStates': [{'id': 'warehouse_ru_01_1',
                                              'cargoAvailable': {'metalBeams': 3}}]}}
        result = extract_snapshot(value)
        self.assertEqual(result['cargo_depots']['candidates'][0]['cargo'], {'metalBeams': 3})

    def test_unrelated_cargo_is_never_mislabeled_as_depot(self):
        value = {'SslValue': {'persistentProfileData': {},
                             'truck': {'cargoAvailable': {'metalBeams': 999}},
                             'warehouse_us_01_01': {'cargoAvailable': {'fake': 'infinite'}}}}
        self.assertFalse(extract_snapshot(value)['cargo_depots']['available'])

    def test_missing_fields_unknown_not_zero(self):
        value = {'SslValue': {'persistentProfileData': {}}}
        result = extract_snapshot(value)
        self.assertIsNone(result['objectives']['completed'])
        self.assertIsNone(result['visited_levels']['count'])
        self.assertIsNone(result['garages']['open_count'])
        self.assertFalse(result['cargo_depots']['available'])

    def test_bool_malformed_and_dict_fields_not_misread(self):
        value = {'SslValue': {'persistentProfileData': {},
                             'finishedObjs': {'TASK_A': True},
                             'visitedLevels': 'level_us_01_01',
                             'levelGarageStatuses': {'foo': True, 'bar': '2', 'baz': 2},
                             'warehouse_demo': {'cargoAvailable': {'a': False, 'b': 4.0, 'c': -2}}}}
        result = extract_snapshot(value)
        self.assertIsNone(result['objectives']['completed'])
        self.assertIsNone(result['visited_levels']['count'])
        self.assertEqual(result['garages']['open_count'], 1)
        self.assertFalse(result['cargo_depots']['available'])

    def test_save_update_preserves_existing_manual_draft(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'CompleteSave.cfg'
            source.write_text(json.dumps(self.sample()), encoding='utf-8')
            original = source.read_bytes()
            key = profile_key(source)
            store = ProfileStore(Path(d) / 'app')
            store.save_draft(key, [('metal_beams', 5)], note='My own manual plan')
            report, signature = snapshot_save(source)
            store.save_game_snapshot(key, source, report, signature)
            self.assertEqual(store.manifest(key), [('metal_beams', 5)])
            self.assertEqual(store.read(key)['draft']['note'], 'My own manual plan')
            self.assertEqual(store.read(key)['game_snapshot']['garages']['open_count'], 1)
            self.assertEqual(source.read_bytes(), original)

    def test_many_untrusted_nodes_capped(self):
        rows = [{'id': f'warehouse_{i}', 'cargoAvailable': {'beams': i}} for i in range(350)]
        value = {'SslValue': {'persistentProfileData': {}, 'areas': rows}}
        result = extract_snapshot(value)
        self.assertLessEqual(result['cargo_depots']['count'], 250)
        self.assertTrue(result['cargo_depots']['truncated'])


if __name__ == '__main__':
    unittest.main()
