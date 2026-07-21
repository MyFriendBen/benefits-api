from django.conf import settings
from django.test import SimpleTestCase

from programs.programs.data.loader import load_data_layer_from_file

EXAMPLES_DIR = settings.BASE_DIR / "schemas" / "examples"


class TestLoadDataLayer(SimpleTestCase):
    def test_loads_unsourced_wic_co(self):
        data = load_data_layer_from_file(EXAMPLES_DIR / "wic_co.json")

        self.assertEqual(data.program, "wic")
        self.assertEqual(data.state, "co")
        self.assertEqual(data.category_amounts["INFANT"], 130)
        self.assertEqual(data.source.status, "unsourced")
        self.assertIsNone(data.source.citation)

    def test_loads_guessed_wic_nc(self):
        data = load_data_layer_from_file(EXAMPLES_DIR / "wic_nc.json")

        self.assertEqual(data.state, "nc")
        self.assertEqual(data.source.status, "guessed")
        self.assertIsNone(data.source.citation)
