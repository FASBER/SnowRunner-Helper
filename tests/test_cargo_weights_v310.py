"""Data-quality checks for documented *packed* cargo weights from MapRunner."""
import unittest
import json
from pathlib import Path
from cargo_weight_v317 import (
    MAPRUNNER_PACKED_MASS_KG, MAPRUNNER_SOURCE_URL, verified_mass_t,
    cargo_weight_label, cargo_weight_source)

ROOT=Path(__file__).resolve().parent.parent

class MaprunnerWeightsTests(unittest.TestCase):
    def test_source_and_coverage(self):
        self.assertEqual(MAPRUNNER_SOURCE_URL,'https://www.maprunner.info/cargo')
        self.assertEqual(len(MAPRUNNER_PACKED_MASS_KG),68)
        self.assertEqual(len([v for v in MAPRUNNER_PACKED_MASS_KG.values() if isinstance(v,tuple)]),3)

    def test_real_packed_mass_examples(self):
        # MapRunner cargo table: packed, NOT loose mass.
        self.assertEqual(cargo_weight_label({'id':'metal_beams'},'ru'),'5 т')
        self.assertEqual(cargo_weight_label({'id':'metal_rolls'},'ru'),'1 т')
        self.assertEqual(cargo_weight_label({'id':'wooden_planks'},'ru'),'0,5 т')
        self.assertEqual(cargo_weight_label({'id':'data_buoy'},'ru'),'2,341 т')
        self.assertEqual(cargo_weight_label({'id':'multistage_pump'},'en'),'5.75 t')
        self.assertEqual(cargo_weight_source({'id':'bricks'}),'maprunner_packed')

    def test_range_preserved_no_fabricated_average(self):
        self.assertEqual(cargo_weight_label({'id':'medium_logs'},'ru'),'5–8,3 т')
        self.assertEqual(cargo_weight_label({'id':'short_logs'},'ru'),'4–4,05 т')
        self.assertEqual(cargo_weight_label({'id':'burnt_logs'},'en'),'4–8.25 t')

    def test_ambiguous_variants_and_missing_remain_unknown(self):
        for cargo_id in ('repair_parts','water','wooden_planks_type2',
                         'wooden_planks_type4','service_spare_parts_special'):
            with self.subTest(cargo_id=cargo_id):
                self.assertEqual(cargo_weight_label({'id':cargo_id},'ru'),'Нет данных')
                self.assertIsNone(cargo_weight_source({'id':cargo_id}))
        self.assertEqual(cargo_weight_label({'slots':4},'ru'),'Нет данных')

    def test_attested_local_game_file_mass_has_priority(self):
        e={'id':'metal_beams','mass_t':4.25,'mass_source':'local_game_data'}
        self.assertEqual(verified_mass_t(e),4.25)
        self.assertEqual(cargo_weight_label(e,'ru'),'4,25 т')
        self.assertEqual(cargo_weight_source(e),'game_files')
        self.assertIsNone(verified_mass_t({'id':'metal_beams','mass_t':150,'mass_source':'random_website'}))
        self.assertEqual(cargo_weight_label({'id':'metal_beams','mass_t':150,'mass_source':'random_website'},'ru'),'5 т')

    def test_all_values_positive_and_catalog_ids_when_available(self):
        for k,v in MAPRUNNER_PACKED_MASS_KG.items():
            self.assertTrue(k and k.isascii())
            values=v if isinstance(v,tuple) else (v,)
            self.assertTrue(all(type(x) is int and x>0 for x in values))
        catalog=ROOT/'catalog.json'
        if catalog.is_file():
            entries=json.loads(catalog.read_text(encoding='utf-8'))['cargo']
            ids={x['id'] for x in entries}
            self.assertTrue(set(MAPRUNNER_PACKED_MASS_KG).issubset(ids))
            self.assertEqual(len(entries),73)
            self.assertEqual(len(ids-set(MAPRUNNER_PACKED_MASS_KG)),5)

if __name__=='__main__': unittest.main()
