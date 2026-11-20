"""Visual-layout and interaction regressions for approved v0.31.14 UI.

Headless: checks the real coordinate transform and compatibility without
changing game save files or creating a GUI window on GitHub Actions.
"""
from __future__ import annotations
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from ui_repair_v312 import fitted_y, source_y, fitted_x, source_x, _fitted_page, _place_search_widgets
import approved_reference_v311 as approved

ROOT=Path(__file__).resolve().parents[1]

class ApprovedLayoutRepairTests(unittest.TestCase):
    def test_entire_old_workspace_fits_under_profile_and_above_footer(self):
        self.assertEqual(fitted_y(129),177)
        self.assertEqual(fitted_y(735),718)
        for original in (129,156,183,208,273,400,680,705,730,735):
            with self.subTest(y=original):
                self.assertGreaterEqual(fitted_y(original),177)
                self.assertLessEqual(fitted_y(original),718)
                self.assertAlmostEqual(source_y(fitted_y(original)),original,places=6)

    def test_horizontal_workspace_aligns_with_approved_panel_edges(self):
        self.assertEqual(fitted_x(262),197)
        self.assertEqual(fitted_x(1305),1295)
        for x in (262,275,327,760,1000,1305):
            self.assertAlmostEqual(source_x(fitted_x(x)),x)

    def test_painted_items_and_hitboxes_use_same_transform(self):
        captures=[];clicks=[]
        def old(s):
            captures.append(s.p(262,129))
            captures.append(s.p(705,730))
            s.hit(300,705,700,730,lambda:clicks.append('clicked'),('btn','bottom'))
        obj=SimpleNamespace(page='recipes',reference_ui=True,
            p=lambda x,y:(x,y),hit=lambda *args:captures.append(('hit',args)))
        _fitted_page(old)(obj)
        self.assertEqual(captures[0],(197,177))
        self.assertLessEqual(captures[1][1],718)
        bounds=captures[2][1]
        self.assertAlmostEqual(bounds[0],fitted_x(300))
        self.assertAlmostEqual(bounds[2],fitted_x(700))
        self.assertAlmostEqual(bounds[1],fitted_y(705))
        self.assertAlmostEqual(bounds[3],fitted_y(730))
        bounds[4]()
        self.assertEqual(clicks,['clicked'])
        self.assertNotIn('p',obj.__dict__) if hasattr(obj,'__dict__') and hasattr(type(obj),'p') else None

    def test_cargo_and_classic_layouts_are_not_transformed(self):
        for page,is_ref in (('cargo',True),('settings',False)):
            obj=SimpleNamespace(page=page,reference_ui=is_ref,p=lambda x,y:(x,y),
                hit=lambda *a:None)
            value=_fitted_page(lambda s:s.p(123,129))(obj)
            self.assertEqual(value,(123,129))

    def test_live_search_fields_move_with_painted_layout(self):
        def widget():
            target=Mock();target.winfo_manager.return_value='place'
            return target
        for page,expected in [('recipes',188),('calculator',194),('manual',188)]:
            s=SimpleNamespace(page=page,reference_ui=True,sy=1,oy=0,p=lambda x,y:(x,y),
                search_entry=widget(),search_placeholder=widget(),
                calc_search_entry=widget(),calc_search_placeholder=widget())
            _place_search_widgets(s)
            w=s.calc_search_entry if page=='calculator' else s.search_entry
            self.assertEqual(w.place_configure.call_args.kwargs['y'],round(fitted_y(expected)))
            self.assertEqual(w.place_configure.call_args.kwargs['x'],round(fitted_x(285 if page=='calculator' else 327)))

    def test_home_and_garage_navigation_are_in_approved_adapter(self):
        source=(ROOT/'approved_reference_v311.py').read_text(encoding='utf-8')
        for name in ('home','cargo','recipes','garage','calculator','settings'):
            self.assertIn("('"+name+"'",source)
        self.assertIn("self.app.game_connection_dialog",source)

    def test_user_icon_is_not_recolored_and_is_cached_by_file_path(self):
        source=(ROOT/'approved_reference_v311.py').read_text(encoding='utf-8')
        self.assertIn('if selected and not custom:',source)
        self.assertIn('key=(page,str(path),selected',source)

    def test_editor_no_longer_uses_old_four_or_five_tab_preview(self):
        source=(ROOT/'ui_repair_v312.py').read_text(encoding='utf-8')
        self.assertIn('approved_reference_v311.png',source)
        for name in ('home','cargo','recipes','garage','calculator','settings'):
            self.assertIn("('"+name+"'",source)
        self.assertIn('Editor._render_preview_image=_paint_preview',source)
        self.assertIn("for key in ('home','garage')",source)

    def test_duplicate_recipe_names_are_disambiguated_by_location(self):
        source=(ROOT/'approved_reference_v311.py').read_text(encoding='utf-8')
        self.assertIn('duplicates={title for title in titles if titles.count(title)>1}',source)
        self.assertIn('display_recipe_location(r,self.lang)',source)

    def test_ota_and_game_save_code_are_not_replaced(self):
        src=(ROOT/'ui_repair_v312.py').read_text(encoding='utf-8')
        self.assertNotIn('save_game_snapshot(',src)
        self.assertNotIn('update.json',src)
        self.assertNotIn('subprocess.run(',src)
        self.assertNotIn('os.remove(',src)

if __name__=='__main__':unittest.main()
