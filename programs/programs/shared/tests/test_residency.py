from django.test import SimpleTestCase

from programs.programs.shared.residency import lives_in
from screener.models import Screen


class TestLivesIn(SimpleTestCase):
    def test_matches_the_screen_location(self):
        self.assertTrue(lives_in(Screen(county="Cambridge"), "Cambridge"))

    def test_rejects_another_location(self):
        self.assertFalse(lives_in(Screen(county="Somerville"), "Cambridge"))

    def test_compares_exactly(self):
        # A county-suffixed form doesn't match a bare city name.
        self.assertFalse(lives_in(Screen(county="Cambridge County"), "Cambridge"))

    def test_no_location_never_matches(self):
        self.assertFalse(lives_in(Screen(county=None), "Cambridge"))
