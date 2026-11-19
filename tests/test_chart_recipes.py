"""Official-only rules and imported game data, not crowd-sourced recipe counts."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from core import (CARGO, CARGO_DB, BUILTIN_RECIPES, load_game_recipes,
                  validate_recipe)
from official_import import import_recipes, describe_import_failure

class GameDataTests(unittest.TestCase):
    def test_no_community_recipes_present_as_official(self):
        self.assertEqual(len(CARGO_DB),73)
        self.assertEqual(len(BUILTIN_RECIPES),100)
        self.assertTrue(all(x.get("verified")=="local_game_data" for x in BUILTIN_RECIPES))

    def test_game_schema_import_from_json_and_archive(self):
        doc={'props':[{'craftSettings':[
             {'name':'metal_beams','craftCount':1,'cargoComponents':[
                {'name':'metal_rolls','count':2}]},
             {'name':'concrete_blocks','craftCount':1,'cargoComponents':[
                {'name':'cement','count':1}], 'energy':200},
             {'name':'never_heard_of_this','craftCount':1,'cargoComponents':[
                {'name':'cement','count':1}]},
             {'name':'metal_beams','craftCount':1,'cargoComponents':[
                {'name':'UNKNOWN_CARGO','count':2}]},
             ]}]}
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            source=folder/'zone.json'
            source.write_text(json.dumps(doc),encoding='utf8')
            result,report=import_recipes(source,CARGO)
            self.assertEqual(len(result),2)
            self.assertEqual(report['imported'],2)
            self.assertIn('never_heard_of_this',report['unknown_ids'])
            for item in result:
                self.assertTrue(validate_recipe(item))
                self.assertEqual(item['verified'],'local_game_data')
            self.assertTrue(result[1]['generator'])
            self.assertEqual(result[1]['energy'],200)
            archive=folder/'example.pak'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('map/_zones.json',json.dumps(doc))
            loaded,report2=import_recipes(archive,CARGO)
            self.assertEqual(len(loaded),2)
            self.assertEqual(report2['json_files'],1)

    def test_import_error_explains_missing_json_without_fake_unknown_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'level_test.pak'
            with zipfile.ZipFile(source,'w') as archive:
                archive.writestr('map/data.stg', b'not a JSON')
            loaded,report=import_recipes(source,CARGO)
            self.assertEqual(loaded,[])
            self.assertEqual(report['json_candidates'],0)
            msg=describe_import_failure(source, report, 'ru')
            self.assertIn('JSON-файлов в архиве: 0',msg)
            self.assertIn('нет доступных JSON',msg)
            self.assertNotIn('Неизвестные ID:',msg)

    def test_import_error_explains_json_without_craftsettings(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'level_test.pak'
            with zipfile.ZipFile(source,'w') as archive:
                archive.writestr('map/settings.json','{"props": []}')
            loaded,report=import_recipes(source,CARGO)
            self.assertEqual(loaded,[])
            self.assertEqual(report['json_candidates'],1)
            msg=describe_import_failure(source, report, 'ru')
            self.assertIn('Записей в craftSettings: 0',msg)
            self.assertIn('craftSettings',msg)

    def test_no_forged_official_data_without_craftsettings(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'bad.json'
            source.write_text(json.dumps({'name':'metal_beams','craftCount':1,
                              'cargoComponents':[{'name':'cement','count':1}]}))
            loaded,_=import_recipes(source,CARGO)
            self.assertEqual(loaded,[])

if __name__=='__main__':unittest.main()
