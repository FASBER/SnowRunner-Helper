import json
import tempfile
import unittest
from pathlib import Path
from save_diagnostics import structural_report, report_save_structure

class DiagnosticTests(unittest.TestCase):
    def test_values_and_user_identifiers_are_redacted(self):
        raw = {'CompleteSave': {'SslValue': {
            'persistentProfileData': {'money': 991239, 'private_user12345': 'Do Not Disclose!',
                                      'trucksInWarehouse': [{'type': 'secret_truck_model'}]},
            'objectiveStates': {'mission_secret987': {'isFinished': True}},
            'visitedLevels': ['hidden_level_123'],
            'levelStates': {'warehouse_private_1337': {'cargoAvailable': {'my_item': 7}}}}}}
        txt = structural_report(raw)
        for secret in ['991239','private_user12345','Do Not Disclose!', 'secret_truck_model',
                       'mission_secret987', 'warehouse_private_1337', 'hidden_level_123', 'my_item']:
            self.assertNotIn(secret, txt)
        self.assertIn('persistentProfileData', txt)
        self.assertIn('cargoAvailable', txt)
        self.assertIn('money: number', txt)

    def test_does_not_modify_game_source(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / 'CompleteSave.cfg'
            file.write_text(json.dumps({'CompleteSave': {'SslValue': {'gameTime': 17}}}))
            before = file.read_bytes()
            txt = report_save_structure(file)
            self.assertIn('gameTime: number', txt)
            self.assertEqual(file.read_bytes(), before)

    def test_bounds_complex_structures(self):
        sample = {'data': [{'random': [{'x': [i for i in range(200)]}]} for _ in range(300)]}
        txt = structural_report(sample, max_nodes=100)
        self.assertLess(len(txt), 10000)

if __name__ == '__main__':
    unittest.main()
