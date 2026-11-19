"""Isolated, synthetic fixtures; never requires or modifies real SnowRunner files."""
import tempfile
import unittest
from pathlib import Path
from profile_sync import ProfileStore
from warehouse_planning import preview_warehouse


class DraftManagementTests(unittest.TestCase):
    def test_named_drafts_search_copy_rename_restore_delete(self):
        with tempfile.TemporaryDirectory() as td:
            store = ProfileStore(Path(td))
            store.save_draft('local', [('metal_beams', 2)])
            source = store.create_named_draft('local', 'Главная доставка', [('metal_beams', 2)])
            self.assertEqual(store.list_named_drafts('local', 'достав')[0]['id'], source['id'])
            with self.assertRaisesRegex(ValueError, 'already exists'):
                store.create_named_draft('local', 'главная доставка', [])
            copied = store.duplicate_named_draft('local', source['id'], 'Резерв')
            store.rename_named_draft('local', copied['id'], 'Запасной план')
            store.save_draft('local', [('wooden_planks', 5)])
            self.assertEqual(store.restore_named_draft('local', source['id']), [('metal_beams', 2)])
            self.assertEqual(store.list_draft_history('local')[0]['load'], [['wooden_planks', 5]])
            self.assertEqual(len(store.list_named_drafts('local')), 2)
            store.delete_named_draft('local', source['id'])
            self.assertEqual(len(store.list_named_drafts('local')), 1)
            self.assertEqual(store.list_named_drafts('local')[0]['name'], 'Запасной план')
            with self.assertRaisesRegex(ValueError, 'not found'):
                store.restore_named_draft('local', source['id'])

    def test_recovery_is_bounded_and_restorable(self):
        with tempfile.TemporaryDirectory() as td:
            store = ProfileStore(Path(td))
            for count in range(1, 45):
                store.save_draft('local', [('metal_beams', count)])
            self.assertEqual(len(store.list_draft_history('local')), 30)
            self.assertEqual(store.list_draft_history('local')[0]['load'], [['metal_beams', 43]])
            self.assertEqual(store.restore_draft_history('local', 0), [('metal_beams', 43)])
            self.assertEqual(store.list_draft_history('local')[0]['load'], [['metal_beams', 44]])
            with self.assertRaises(ValueError):
                store.restore_draft_history('local', 9999)
            with self.assertRaises(ValueError):
                store.restore_draft_history('local', True)

    def test_profile_isolation_and_corruption_preservation(self):
        with tempfile.TemporaryDirectory() as td:
            store = ProfileStore(Path(td))
            store.create_named_draft('local', 'A', [('metal_beams', 1)])
            key = 'a'*20
            self.assertFalse(store.list_named_drafts(key))
            store.create_named_draft(key, 'B', [('wooden_planks', 5)])
            self.assertEqual(store.list_named_drafts('local')[0]['name'], 'A')
            self.assertEqual(store.list_named_drafts(key)[0]['name'], 'B')
            store.file(key).write_text('not json!', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'unreadable'):
                store.create_named_draft(key, 'C', [])
            self.assertEqual(store.file(key).read_text(), 'not json!')

    def test_mapping_is_profile_specific_and_validated(self):
        with tempfile.TemporaryDirectory() as td:
            store = ProfileStore(Path(td))
            store.map_game_cargo('local', 'metalBeams', 'metal_beams')
            self.assertEqual(store.cargo_mappings('local'), {'metalBeams': 'metal_beams'})
            self.assertEqual(store.cargo_mappings('a'*20), {})
            with self.assertRaises(ValueError):
                store.map_game_cargo('local', 'metalBeams', 'alien_cargo')
            # Malformed persisted values must not crash a mapping read.
            data = store.read('local')
            data['manual_cargo_mappings'] = {'bad': ['metal_beams'], 'metalBeams': 'metal_beams'}
            store._write('local', data)
            self.assertEqual(store.cargo_mappings('local'), {'metalBeams': 'metal_beams'})
            store.map_game_cargo('local', 'metalBeams', None)
            self.assertEqual(store.cargo_mappings('local'), {})


class WarehousePreviewTests(unittest.TestCase):
    @staticmethod
    def sample():
        return {'cargo_depots': {'candidates': [{'warehouse_id': 'warehouse_demo',
                 'cargo': {'metalBeams': 4, 'wood': -1, 'unknown': 123}}]}}

    def test_only_manual_mapping_affects_preview(self):
        rows = preview_warehouse(self.sample(), 'warehouse_demo', {}, [('metal_beams', 6)])
        self.assertIsNone(rows['rows'][0]['shortage'])
        self.assertFalse(rows['verified'])
        rows = preview_warehouse(self.sample(), 'warehouse_demo',
                  {'metalBeams': 'metal_beams', 'wood': 'wooden_planks'},
                  [('metal_beams', 6), ('wooden_planks', 12)])
        self.assertEqual(rows['rows'][0]['shortage'], 2)
        self.assertEqual(rows['rows'][1]['status'], 'tentative_unlimited')
        self.assertFalse(rows['auto_deduction'])

    def test_conflicting_raw_ids_not_double_counted(self):
        rows = preview_warehouse(self.sample(), 'warehouse_demo',
                  {'metalBeams': 'metal_beams', 'wood': 'metal_beams'}, [('metal_beams', 6)])
        self.assertEqual(rows['ambiguous_cargo_ids'], ['metal_beams'])
        self.assertIsNone(rows['rows'][0]['shortage'])

    def test_duplicate_facilities_are_rejected(self):
        sample = self.sample()
        sample['cargo_depots']['candidates'].append(sample['cargo_depots']['candidates'][0].copy())
        with self.assertRaises(ValueError):
            preview_warehouse(sample, 'warehouse_demo', {}, [])

if __name__ == '__main__':
    unittest.main()
