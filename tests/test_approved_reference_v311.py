"""Non-GUI regression tests of the confirmed SnowRunner reference layout."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from core import ROOT
import approved_reference_v311 as layout

class ApprovedLayoutTests(unittest.TestCase):
    def test_background_asset_has_native_reference_size(self):
        with Image.open(ROOT/'assets/ui/approved_reference_v311.png') as art:
            self.assertEqual(art.size,(1319,747))
            self.assertEqual(art.mode,'RGB')

    def test_all_six_reference_navigation_icons_are_present(self):
        for name in ('home','cargo','recipes','garage','calculator','settings'):
            path=ROOT/'assets/ui/approved_nav'/f'{name}.png'
            with self.subTest(name=name),Image.open(path) as icon:
                self.assertEqual(icon.size,(48,48))
                self.assertEqual(icon.mode,'RGBA')

    def test_no_fictional_account_progress_or_money(self):
        app=SimpleNamespace(active_profile_key='local')
        result=layout._stats(SimpleNamespace(app=app))
        self.assertEqual(result['profile'],'Локальный профиль')
        for key in ('money','exp','objectives','trucks','garages'):
            self.assertIsNone(result[key])

    def test_profile_statistics_come_only_from_selected_snapshot(self):
        snapshot={'game_snapshot':{'statistics':{'money':1234,'experience':5678},
                'objectives':{'completed':3},'retained_trucks':{'available':True,'count':4},
                'garages':{'available':True,'open_count':2}}}
        profiles=SimpleNamespace(read=lambda key:snapshot)
        app=SimpleNamespace(active_profile_key='abcd1234',profiles=profiles)
        result=layout._stats(SimpleNamespace(app=app))
        self.assertEqual((result['money'],result['exp'],result['objectives'],result['trucks'],result['garages']),
                         (1234,5678,3,4,2))

    def test_reference_image_is_used_only_on_full_approved_viewport(self):
        from PIL import Image
        img=Image.new('RGB',(100,180),'#102938')
        self.assertIs(layout.decorate_background(img,'game'),img)

    def test_classic_canvas_does_not_get_approved_background(self):
        classic=Image.new('RGB',(1319,747),'#10171B')
        self.assertIs(layout.decorate_background(classic,'game'),classic)

    def test_only_display_hooks_installed(self):
        import inspect
        code=inspect.getsource(layout.install_approved_ui)
        for label in ('draw_nav','draw_toolbar','_draw_reference_cargo',
                      '_draw_reference_popup','_reference_visible_cargo','redraw'):
            self.assertIn(label,code)
        for not_modified in ('_sync_active_profile','close_app','save_profile_draft',
                             'update_launcher','game_connection_dialog'):
            self.assertNotIn('cls.'+not_modified+'=',code)

    def test_new_ui_has_actual_user_actions(self):
        import inspect
        code=inspect.getsource(layout)
        for label in ('app.refresh_game_data','app.change_cargo_icon',
                      'open_recipe','_choose_location','selected_cargo',
                      'visible_cargo','_v311_filter_map','_v311_filter_region'):
            self.assertIn(label,code)
        self.assertNotIn('TruckMasterRU',code)

if __name__=='__main__':unittest.main()
