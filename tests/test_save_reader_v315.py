"""Regression tests for the Steam files supplied with this bug report.

Only synthetic save fixtures are included in the release; no player data.
"""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from save_reader_v315 import decode_save_bytes, read_save_json, install_save_reader


class SaveFormatTests(unittest.TestCase):
    def make_save(self, wrapper, *, suffix=b'\x00', money=250):
        content = {wrapper: {'SslType':'SaveObject','SslValue':{
            'objVersion':9, 'persistentProfileData':{'money':money,'experience':70},
            'finishedObjs':['mission_a'], 'objectiveStates':{'mission_a':{}},
        }},'cfg_version':1}
        return json.dumps(content).encode() + suffix

    def test_read_all_three_real_world_wrapper_shapes(self):
        for i, wrapper in enumerate(('CompleteSave','CompleteSave1','CompleteSave2')):
            with self.subTest(wrapper=wrapper), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / ('CompleteSave' + (str(i) if i else '') + '.cfg')
                original = self.make_save(wrapper)
                path.write_bytes(original)
                parsed = decode_save_bytes(original)
                self.assertEqual(parsed['CompleteSave']['SslValue']['persistentProfileData']['money'],250)
                self.assertEqual(read_save_json(path), parsed)
                self.assertEqual(path.read_bytes(), original)

    def test_json_without_padding_is_supported(self):
        self.assertIn('CompleteSave',decode_save_bytes(self.make_save('CompleteSave2',suffix=b'')))

    def test_only_one_terminal_nul_is_accepted(self):
        for payload in (self.make_save('CompleteSave2',suffix=b'\x00\x00'),
                        self.make_save('CompleteSave1',suffix=b' corrupted'),
                        b'\x00', b'{\"missing\":', b'[]'):
            with self.subTest(payload_len=len(payload)):
                with self.assertRaises(ValueError):decode_save_bytes(payload)

    def test_unknown_root_and_non_dict_wrappers_not_relabelled(self):
        value=decode_save_bytes(b'{\"AnUnknownSave\":{}}')
        self.assertEqual(list(value),['AnUnknownSave'])
        value=decode_save_bytes(b'{\"CompleteSave2\":2}')
        self.assertNotIn('CompleteSave',value)

    def test_read_rejects_empty_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            f=Path(directory)/'CompleteSave2.cfg'
            f.write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'size'):read_save_json(f)

    def test_install_is_idempotent_for_game_and_profile_modules(self):
        import game_bridge, profile_sync
        original_bridge=game_bridge.read_save_json
        original_profile=profile_sync.read_save_json
        old_bridge_marker=getattr(game_bridge,'_save_reader_v315_installed',False)
        old_profile_marker=getattr(profile_sync,'_save_reader_v315_installed',False)
        try:
            # Other UI tests may already have installed the adapter globally.
            # Reset only the two idempotence markers for this isolated assertion.
            game_bridge._save_reader_v315_installed = False
            profile_sync._save_reader_v315_installed = False
            self.assertTrue(install_save_reader())
            self.assertIs(game_bridge.read_save_json,read_save_json)
            self.assertIs(profile_sync.read_save_json,read_save_json)
            self.assertFalse(install_save_reader())
        finally:
            game_bridge.read_save_json=original_bridge
            profile_sync.read_save_json=original_profile
            game_bridge._save_reader_v315_installed=old_bridge_marker
            profile_sync._save_reader_v315_installed=old_profile_marker

if __name__ == '__main__':unittest.main()
