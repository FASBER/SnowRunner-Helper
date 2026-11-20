"""Functional regressions for the switchable Expedition HUD skin."""
import unittest
from types import SimpleNamespace
from PIL import Image
from game_ui import GameScreen, NAV


class NewUIDesignTests(unittest.TestCase):
    def test_uses_non_screenshot_header_without_footer_seam(self):
        fake=SimpleNamespace(new_ui=True,base_image=None,bg_cache={'old':1})
        GameScreen._build_expedition_background(fake)
        img=fake.base_image
        self.assertIsInstance(img,Image.Image)
        self.assertEqual(img.size,(1319,747))
        self.assertEqual(img.getpixel((90,590)),img.getpixel((90,712)))
        self.assertNotEqual(img.getpixel((90,590)),(255,194,27))
        self.assertEqual(fake.bg_cache,{})

    def test_navigation_target_preserved_for_every_section(self):
        rects=[];targets=[]
        stub=SimpleNamespace(new_ui=True,lang='ru',page='calculator')
        stub.txt=lambda *a,**kw:None
        stub.line=lambda *a,**kw:None
        stub.round=lambda *a,**kw:rects.append(a)
        stub.nav_image=lambda *a,**kw:None
        stub.t=lambda s:s
        stub.hit=lambda *a,**kw:targets.append(a)
        stub.show=lambda page:None
        GameScreen.draw_nav(stub)
        self.assertEqual(len(targets),len(NAV))
        self.assertEqual(targets[-1][:4],(24,634,239,690))
        self.assertEqual([a[0] for a in targets], [24]*5)

    def test_classic_remains_available(self):
        # v0.31.7's GameScreen reads the owning Application's selected theme.
        stub=SimpleNamespace(new_ui=False,appearance={
            'panel_alpha':94,'panel':'#151C20','row':'#222B31','fg':'#F1F2F0',
            'muted':'#BAC3C6','accent':'#FFC21B','border':'#45525A'
        },app=SimpleNamespace(config={'theme':'game'}))
        GameScreen._apply_palette(stub)
        from game_ui import BG
        self.assertEqual(BG,'#10171b')

    def test_selected_light_theme_palette_is_respected(self):
        """The test double includes the same theme/config interface as Application."""
        colors={'bg':'#ECEAE3','fg':'#2A2D30','muted':'#626B70','accent':'#C38322'}
        app=SimpleNamespace(config={'theme':'light'},c=colors.__getitem__)
        stub=SimpleNamespace(new_ui=True,appearance={
            'panel_alpha':94,'panel':'#151C20','row':'#222B31','fg':'#F1F2F0',
            'muted':'#BAC3C6','accent':'#FFC21B','border':'#45525A'
        },app=app)
        import game_ui
        previous={key:getattr(game_ui,key) for key in ('BG','PANEL','ROW','ROW_HOVER','FG','MUTED','YELLOW','BORDER')}
        try:
            GameScreen._apply_palette(stub)
            self.assertEqual((game_ui.BG,game_ui.FG,game_ui.MUTED,game_ui.YELLOW),
                             (colors['bg'],colors['fg'],colors['muted'],colors['accent']))
        finally:
            for key,value in previous.items():setattr(game_ui,key,value)


if __name__=='__main__':unittest.main()
