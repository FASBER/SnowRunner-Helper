"""Regression tests for v0.31.7: manual refresh, persistent theme, honest mass."""
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
import sys
import types

from cargo_weight_v317 import cargo_weight_label, verified_mass_t
from theme_v317 import theme_color, theme_background, THEME_LABELS

ROOT = Path(__file__).resolve().parent.parent

class WeightSourceChecks(unittest.TestCase):
    def test_unknown_is_explicit(self):
        self.assertEqual(cargo_weight_label({'slots':3},'ru'), 'Нет данных')
        self.assertEqual(cargo_weight_label({'slots':3},'en'), 'No data')
        self.assertIsNone(verified_mass_t({'mass_t':5.8,'slots':2}))

    def test_only_verified_numeric_mass(self):
        self.assertEqual(cargo_weight_label({'mass_t':1.25,'mass_source':'local_game_data'},'ru'),'1,25 т')
        self.assertEqual(cargo_weight_label({'mass_t':2.0,'mass_source':'official_game_files'},'en'),'2 t')
        for bad in (float('nan'),float('inf'),0,-1,True,'2.0',None):
            with self.subTest(bad=bad):
                self.assertIsNone(verified_mass_t({'mass_source':'local_game_data','mass_t':bad}))
        self.assertIsNone(verified_mass_t({'mass_source':'random_website','mass_t':200}))

class ThemeChecks(unittest.TestCase):
    def test_all_palettes_and_snowrunner_unchanged(self):
        self.assertEqual(len(THEME_LABELS),4)
        self.assertEqual(theme_color('#10171B','game'),'#10171B')
        backgrounds={theme_color('#10171B',theme) for theme in THEME_LABELS}
        self.assertEqual(len(backgrounds),4)
        self.assertEqual(theme_color('', 'light'), '')

    def test_background_keeps_masthead(self):
        from PIL import Image
        im=Image.new('RGB',(100,180),'#111C29')
        im.paste('#BFC1C3',(0,0,100,92))
        changed=theme_background(im,'light')
        self.assertEqual(im.getpixel((50,20)),changed.getpixel((50,20)))
        self.assertNotEqual(im.getpixel((50,140)),changed.getpixel((50,140)))
        self.assertEqual(im.getpixel((50,140)),Image.new('RGB',(1,1),'#111C29').getpixel((0,0)))

class RefreshChecks(unittest.TestCase):
    def refresh(self,profile,archives=(),entries=(),fail_save=False):
        import features_v317
        app=types.SimpleNamespace()
        app.config={'lang':'ru'}
        app.active_profile_key=profile
        app.root=object()
        app.load=[('metal_beams',2)]
        app.official=[{'id':'old_verified'}]
        app._save_profile_draft=MagicMock(side_effect=ValueError('disk full') if fail_save else None)
        app._sync_active_profile=MagicMock(return_value={'cargo':5})
        app._local_game_paths=MagicMock(return_value=(list(archives),[]))
        app.render=MagicMock()
        app._last_profile_sync_issue=''
        core=types.ModuleType('core')
        core.CARGO={'metal_beams':{'slots':2}}
        core.BUILTIN_RECIPES=[{'id':'builtin'}]
        core.IMPORTED_FILE=Path('/not/written.json')
        core.save_json=MagicMock()
        imp=types.ModuleType('official_import')
        imp.import_recipes=MagicMock(return_value=(list(entries),{'unknown_ids':[]}))
        with patch.dict(sys.modules,{'core':core,'official_import':imp}), patch('tkinter.messagebox.showinfo') as info,patch('tkinter.messagebox.showerror') as err,patch('tkinter.messagebox.showwarning') as warn:
            result=features_v317.refresh_game_data(app)
        return app,result,core,imp,info,err,warn

    def test_local_draft_preserved_and_recipe_merge(self):
        app,result,core,imp,*_=self.refresh('local',archives=['game.pak'],entries=[{'id':'new_game'},{'id':'builtin'}])
        self.assertEqual(app.active_profile_key,'local')
        self.assertEqual(app.load,[('metal_beams',2)])
        app._sync_active_profile.assert_not_called()
        self.assertTrue(result['saved'])
        self.assertEqual(result['recipes'],2)
        self.assertEqual({r['id'] for r in app.official},{'old_verified','new_game'})
        core.save_json.assert_called_once()
        app.render.assert_called_once()

    def test_selected_profile_only_and_no_guess(self):
        app,result,_,imp,*_=self.refresh('steam_slot_3',archives=['a.pak','b.pak'])
        app._sync_active_profile.assert_called_once()
        self.assertEqual(result['profile'],'steam_slot_3')
        self.assertEqual(app.active_profile_key,'steam_slot_3')
        imp.import_recipes.assert_not_called()
        self.assertTrue(result['errors'])

    def test_unsaved_draft_blocks_refresh(self):
        app,result,_,imp,*_=self.refresh('local',fail_save=True)
        self.assertFalse(result['saved'])
        app.render.assert_not_called()
        imp.import_recipes.assert_not_called()
        app._sync_active_profile.assert_not_called()

@unittest.skipUnless((ROOT / 'app.py').is_file(), 'full project sources not available locally')
class IntegrationSourceChecks(unittest.TestCase):
    def test_theme_not_forced_and_game_skin_shared(self):
        s=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertNotIn("self.config['theme']='game'  # The SnowRunner canvas",s)
        self.assertIn("self.config.get('ui_design') == 'expedition'",s)
        self.assertIn('def refresh_game_data(self):',s)
    def test_buttons_weights_and_theme_palette(self):
        s=(ROOT/'game_ui.py').read_text(encoding='utf-8')
        self.assertIn('self.app.refresh_game_data',s)
        self.assertIn('cargo_weight_label(item,self.lang)',s)
        self.assertIn('THEME_LABELS.get(theme',s)
        self.assertIn('theme_background(self.base_image',s)

if __name__=='__main__': unittest.main()
