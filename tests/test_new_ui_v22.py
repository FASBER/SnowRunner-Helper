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
        stub=SimpleNamespace(new_ui=False,appearance={
            'panel_alpha':94,'panel':'#151C20','row':'#222B31','fg':'#F1F2F0',
            'muted':'#BAC3C6','accent':'#FFC21B','border':'#45525A'
        })
        GameScreen._apply_palette(stub)
        from game_ui import BG
        self.assertEqual(BG,'#10171b')


if __name__=='__main__':unittest.main()
