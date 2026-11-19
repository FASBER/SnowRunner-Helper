"""A game installation is not necessary; all source saves are synthetic fixtures."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from game_bridge import profile_key
from profile_sync import (ProfileStore, SaveMonitor, extract_snapshot,
                          snapshot_save, unwrap_save)


class ProfileSyncTests(unittest.TestCase):
    def sample(self):
        return {'CompleteSave': {'SslType': 'SaveObject', 'SslValue': {
            'gameTime': 123.5,
            'objectiveStates': {'mission_a': 1, 'mission_b': 2},
            'persistentProfileData': {
                'money': 1000, 'experience': 87,
                'unlockedItemNames': {'truck_a': False},
                'trucksInWarehouse': [{'type': 'truck_a'}, {'type': 'truck_a'}, {'type': 'truck_b'}],
            },
        }}}

    def test_validated_game_fields_without_false_depot_data(self):
        snap = extract_snapshot(self.sample())
        self.assertEqual(snap['statistics']['money'], 1000)
        self.assertEqual(snap['retained_trucks']['models'], {'truck_a': 2, 'truck_b': 1})
        self.assertEqual(snap['objectives']['known_entries'], 2)
        self.assertIsNone(snap['objectives']['completed'])
        self.assertFalse(snap['cargo_depots']['available'])
        self.assertEqual(unwrap_save(self.sample())['gameTime'], 123.5)

    def test_unrecognized_json_is_not_accepted_as_a_real_save(self):
        with tempfile.TemporaryDirectory() as td:
            bogus = Path(td) / 'CompleteSave.cfg'
            bogus.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'no recognized'):
                snapshot_save(bogus)

    def test_missing_data_not_zero(self):
        snap = extract_snapshot({'SslValue': {}})
        self.assertIsNone(snap['statistics']['money'])
        self.assertIsNone(snap['objectives']['known_entries'])
        self.assertFalse(snap['retained_trucks']['available'])
        snap = extract_snapshot({'SslValue': {'persistentProfileData': {'money': True, 'experience': -9}}})
        self.assertIsNone(snap['statistics']['money'])
        self.assertIsNone(snap['statistics']['experience'])

    def test_drafts_survive_game_updates_and_are_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / 'CompleteSave.cfg'
            second = root / 'CompleteSave1.cfg'
            first.write_text(json.dumps(self.sample()), encoding='utf-8')
            second.write_text('{}', encoding='utf-8')
            k1, k2 = profile_key(first), profile_key(second)
            db = ProfileStore(root / 'app_data')
            db.save_draft(k1, [('metal_beams', 2), ('wooden_planks', 1)])
            db.save_draft(k2, [('metal_beams', 8)])
            snap, sig = snapshot_save(first)
            original = first.read_bytes()
            db.save_game_snapshot(k1, first, snap, sig)
            self.assertEqual(db.manifest(k1), [('metal_beams', 2), ('wooden_planks', 1)])
            self.assertEqual(db.manifest(k2), [('metal_beams', 8)])
            self.assertIsNone(db.read(k2)['game_snapshot'])
            self.assertEqual(first.read_bytes(), original)
            self.assertEqual(db.read(k1)['last_signature'], list(sig))
            self.assertEqual(db.read(k1)['game_snapshot']['retained_trucks']['count'], 3)

    def test_invalid_keys_no_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            db = ProfileStore(Path(td))
            for key in ('../settings', '/tmp/unsafe', 'LOCAL', 'f'*19, '', 'local/../../x'):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    db.file(key)

    def test_unreadable_profile_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            db = ProfileStore(Path(td))
            path = db.file('local')
            path.write_text('!!! not json !!!', encoding='utf-8')
            with self.assertRaises(ValueError):db.save_draft('local', [])
            self.assertEqual(path.read_text(encoding='utf-8'), '!!! not json !!!')

    def test_invalid_draft_entries_removed_on_read(self):
        with tempfile.TemporaryDirectory() as td:
            db = ProfileStore(Path(td))
            db.save_draft('local', [('metal_beams', 2), ('wrong_cargo', 100),
                                     ('metal_beams', True), ('wooden_planks', -1)])
            self.assertEqual(db.manifest('local'), [('metal_beams', 2)])

    def test_selected_profile_cannot_sync_another_slot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / 'CompleteSave.cfg'
            b = root / 'CompleteSave1.cfg'
            a.write_text('{}', encoding='utf-8')
            b.write_text('{}', encoding='utf-8')
            db = ProfileStore(root / 'app')
            with self.assertRaises(ValueError):
                db.save_game_snapshot(profile_key(b), a, {}, (2, 3))
            self.assertFalse(db.file(profile_key(b)).exists())

    def test_monitor_requires_two_polls_and_never_guesses_active(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / 'CompleteSave.cfg'
            file.write_text('{}', encoding='utf-8')
            watcher = SaveMonitor()
            self.assertEqual(watcher.check(file, None), 'pending')
            self.assertEqual(watcher.check(file, None), 'changed')
            from profile_sync import save_signature
            self.assertEqual(watcher.check(file, save_signature(file)), 'unchanged')
            file.write_text('{"changed":true}', encoding='utf-8')
            self.assertEqual(watcher.check(file, None), 'pending')
            self.assertEqual(watcher.check(file, None), 'changed')
            file.unlink()
            self.assertEqual(watcher.check(file, None), 'missing')

    def test_invalid_game_save_keeps_prior_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            game = root / 'CompleteSave.cfg'
            game.write_text(json.dumps(self.sample()), encoding='utf-8')
            db = ProfileStore(root / 'app')
            key = profile_key(game)
            snap, sig = snapshot_save(game)
            db.save_game_snapshot(key, game, snap, sig)
            game.write_text('{not json', encoding='utf-8')
            with self.assertRaises(ValueError):
                snap2, sig2 = snapshot_save(game)
                db.save_game_snapshot(key, game, snap2, sig2)
            self.assertEqual(db.read(key)['game_snapshot'], snap)


if __name__ == '__main__':
    unittest.main()
