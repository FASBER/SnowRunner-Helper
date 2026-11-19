"""Regression test: Settings navigation is bottom-anchored and clickable."""
import unittest
from types import SimpleNamespace
import game_ui

class SettingsNavPositionTests(unittest.TestCase):
    def test_settings_is_separated_from_main_navigation(self):
        self.assertEqual([game_ui.NAV_Y[page] for page in game_ui.NAV[:4]], [183,255,327,399])
        self.assertGreaterEqual(game_ui.NAV_Y['settings'], 600)
        self.assertLessEqual(game_ui.NAV_Y['settings'] + 58, 703)
        self.assertGreater(game_ui.NAV_Y['settings'], game_ui.NAV_Y['manual'] + 80)

    def test_click_target_moves_together_with_settings_button(self):
        calls=[]
        fake=SimpleNamespace(page='recipes')
        fake.round=lambda *args: calls.append(('round',args))
        fake.rect=lambda *args: calls.append(('rect',args))
        fake.nav_image=lambda *args: calls.append(('image',args))
        fake.txt=lambda *args,**kw: calls.append(('text',args))
        fake.t=lambda page: page
        fake.hit=lambda *args: calls.append(('hit',args))
        fake.show=lambda page: calls.append(('show',(page,)))
        game_ui.GameScreen.draw_nav(fake)
        hits=[args for kind,args in calls if kind=='hit']
        self.assertEqual(len(hits),5)
        sx1, sy1, sx2, sy2, cb, key = hits[-1]
        self.assertEqual((sx1, sy1, sx2, sy2), (29,game_ui.NAV_Y['settings'],245,game_ui.NAV_Y['settings']+58))
        self.assertEqual(key,('nav','settings'))
        cb()
        self.assertIn(('show',('settings',)),calls)

if __name__=='__main__': unittest.main()
