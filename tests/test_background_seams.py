"""Ensure the SnowRunner body has no cut-off left edge on any theme or page.

This does not require a display and therefore also protects CI/test runs.
"""
import unittest
from types import SimpleNamespace
import tempfile
from pathlib import Path
from PIL import ImageColor, Image
from appearance import PRESETS, normalize, preset_config
import game_ui

class BackgroundContinuityTests(unittest.TestCase):
    def render(self, preset='snow', custom_header=''):
        values=preset_config(preset)
        values['textures']=False
        values['mud']=False
        values['header_image']=custom_header
        # The real GameScreen always owns an Application. Supply that minimal
        # dependency in headless tests as well (introduced in v0.31.7).
        app=SimpleNamespace(config={'theme':'game'})
        game=SimpleNamespace(appearance=normalize(values),bg_cache={'old':None},app=app)
        old=game_ui.PANEL
        try:
            game_ui.GameScreen._apply_palette(game)
            game_ui.GameScreen._build_background(game)
            return game.base_image,ImageColor.getrgb(game_ui.PANEL)
        finally:
            game_ui.PANEL=old

    def test_workspace_is_seamless_for_all_approved_presets(self):
        for preset in PRESETS:
            with self.subTest(preset=preset):
                img,color=self.render(preset)
                for y in (126,142,159,180,210,400,593):
                    for x in (18,90,244,250,252,259,350,750,1010,1015,1110,1220,1307):
                        self.assertEqual(img.getpixel((x,y)), color,(preset,x,y))

    def test_custom_header_does_not_repaint_the_content_seam(self):
        with tempfile.TemporaryDirectory() as directory:
            header=Path(directory)/'custom.png'
            Image.new('RGB',(1450,300),'#DC1111').save(header)
            img,color=self.render('mud',str(header))
            for x in (20,225,250,500,700,1008,1015,1100,1307):
                self.assertEqual(img.getpixel((x,147)),color)
            # The same header still shows in the masthead itself.
            self.assertNotEqual(img.getpixel((720,70)),color)

    def test_masthead_remains_visible_without_truck_fragment_in_workspace(self):
        img,color=self.render('snow')
        self.assertNotEqual(img.getpixel((100,40)),color)
        self.assertNotEqual(img.getpixel((1150,60)),color)
        for x in (1000,1014,1015,1150,1307):
            self.assertEqual(img.getpixel((x,160)),color)

    def test_detail_title_band_reaches_right_inside_margin(self):
        recorded=[]
        fake=type('CanvasStub',(),{})()
        fake.round=lambda *args,**kwargs:recorded.append(('round',args))
        fake.txt=lambda *args,**kwargs:recorded.append(('text',args))
        game_ui.GameScreen.title_band(fake,779,248,'Рецепт',417)
        bar=next(args for kind,args in recorded if kind=='round')
        self.assertEqual(bar[0],779)
        self.assertEqual(bar[2],1298)

    def test_sidebar_footer_is_continuous_under_settings_for_all_presets(self):
        for preset in PRESETS:
            img,color=self.render(preset)
            for y in (590,610,649,685,703,719):
                for x in (4,12,30,70,145,219,249,250):
                    self.assertEqual(img.getpixel((x,y)), color,(preset,x,y))

    def test_legacy_track_and_mud_preferences_cannot_recreate_footer_cut(self):
        values=preset_config('snow')
        values.update({'textures':False, 'tracks':True, 'mud':True})
        app=SimpleNamespace(config={'theme':'game'})
        game=SimpleNamespace(appearance=normalize(values), bg_cache={}, app=app)
        old=game_ui.PANEL
        try:
            game_ui.GameScreen._apply_palette(game)
            game_ui.GameScreen._build_background(game)
            color=ImageColor.getrgb(game_ui.PANEL)
            for y in (620,670,705,720):
                for x in (20,65,145,220,247):
                    self.assertEqual(game.base_image.getpixel((x,y)), color)
        finally:
            game_ui.PANEL=old

if __name__=='__main__':unittest.main()
