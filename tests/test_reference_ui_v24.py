"""Checks for the approved photo-matched cargo UI and its real data paths."""
import unittest
from types import SimpleNamespace
from PIL import Image
from core import ROOT,CARGO
from game_ui import GameScreen,NAV

class ReferenceV24Tests(unittest.TestCase):
    def stub(self,query='',category=''):
        screen=SimpleNamespace(
            search=SimpleNamespace(get=lambda:query),
            cargo_category=category,
            app=SimpleNamespace(config={'sort':'name_asc'}),
            lang='ru',page='cargo',
            REFERENCE_FEATURED=GameScreen.REFERENCE_FEATURED,
            _reference_category=lambda c:GameScreen._reference_category(None,c),
        )
        return screen

    def test_approved_header_is_bundled(self):
        with Image.open(ROOT/'assets/ui/v24_approved_header.png') as banner:
            self.assertEqual(banner.size,(1319,92))
            self.assertEqual(banner.mode,'RGB')

    def test_approved_eight_first_rows_are_real_catalog_entries(self):
        s=self.stub()
        entries=GameScreen._reference_visible_cargo(s)
        self.assertEqual([a['id'] for a in entries[:8]],list(GameScreen.REFERENCE_FEATURED))
        self.assertEqual({a['id'] for a in entries},set(CARGO))

    def test_search_and_category_are_functional(self):
        filtered=GameScreen._reference_visible_cargo(self.stub(query='кирпич'))
        self.assertTrue(filtered)
        self.assertTrue(all('кирпич' in a['ru'].lower() for a in filtered))
        wood=GameScreen._reference_visible_cargo(self.stub(category='wood'))
        self.assertTrue(wood)
        self.assertTrue(all(a['category']=='wood' for a in wood))

    def test_unknown_mass_is_not_installed_as_fake_catalog_data(self):
        # The mockup displays example weights; no game mass was verified.
        self.assertTrue(all('mass_t' not in a for a in CARGO.values()))

    def test_navigation_retains_all_five_functions(self):
        self.assertEqual(NAV,['cargo','recipes','calculator','manual','settings'])

if __name__=='__main__':unittest.main()
