import os, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import appearance

class AppearanceTests(unittest.TestCase):
    def test_presets_and_ranges(self):
        self.assertEqual(len(appearance.PRESETS),4)
        d=appearance.normalize({'preset':'invalid','ui_scale':500,'accent':'#xyz','row_height':10})
        self.assertEqual(d['preset'],'snow');self.assertEqual(d['ui_scale'],150)
        self.assertEqual(d['accent'],appearance.DEFAULT['accent']);self.assertEqual(d['row_height'],56)
    def test_import_export_and_preservation(self):
        with tempfile.TemporaryDirectory() as t:
            top=Path(t)
            with patch.object(appearance,'THEME_DIR',top/'themes'):
                img=top/'background.png';Image.new('RGB',(300,200),'navy').save(img)
                d=appearance.preset_config('ice');d['background_image']=str(img);d['accent']='#AABBCC'
                path=top/'saved.zip';appearance.export_theme(d,path,'My theme')
                with zipfile.ZipFile(path) as z:self.assertIn('theme.json',z.namelist())
                folder=appearance.import_theme(path)
                reopened=appearance.open_theme(folder)
                self.assertEqual(reopened['accent'],'#AABBCC')
                self.assertTrue(Path(reopened['background_image']).is_file())
    def test_zip_path_not_extracted(self):
        with tempfile.TemporaryDirectory() as t:
            top=Path(t)
            evil=top/'evil.zip'
            with zipfile.ZipFile(evil,'w') as z:
                z.writestr('../oops.txt','bad')
                z.writestr('theme.json','{"format":1,"settings":{}}')
            with patch.object(appearance,'THEME_DIR',top/'themes'):
                appearance.import_theme(evil)
                self.assertFalse((top/'oops.txt').exists())

if __name__=='__main__':unittest.main()
