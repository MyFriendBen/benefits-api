from types import SimpleNamespace

from django.test import SimpleTestCase

from programs.programs.config.loader import ConfigLayer
from programs.programs.factories.calculator_factory import CalculatorFactory, DuplicateRegistrationError
from programs.util import Dependencies


def make_config(program="p"):
    return ConfigLayer(program=program, state="s", pe_name="x", pe_entity="spm_unit", pe_period_month=None)


class TestCalculatorFactory(SimpleTestCase):
    def test_registered_callable_accepts_exactly_the_real_call_site_signature(self):
        factory = CalculatorFactory()
        config = make_config()
        Calc = factory.register("p", config)

        screen = SimpleNamespace()
        program = SimpleNamespace()
        # Matches screener/views.py:424's real call: Calculator(screen, program, missing_dependencies) --
        # 3 positional args, nothing else. config/benefit_data must already be bound.
        instance = Calc(screen, program, Dependencies())

        self.assertIs(instance.config, config)
        self.assertIsNone(instance.benefit_data)

    def test_get_returns_the_registered_callable(self):
        factory = CalculatorFactory()
        config = make_config()
        Calc = factory.register("p", config)

        self.assertIs(factory.get("p"), Calc)

    def test_as_dict_is_mergeable_like_a_per_state_calculator_dict(self):
        factory = CalculatorFactory()
        factory.register("p1", make_config("p1"))
        factory.register("p2", make_config("p2"))

        merged = {**factory.as_dict(), "existing_program": object}

        self.assertEqual(set(merged.keys()), {"p1", "p2", "existing_program"})

    def test_duplicate_registration_raises(self):
        factory = CalculatorFactory()
        config = make_config()
        factory.register("p", config)

        with self.assertRaises(DuplicateRegistrationError):
            factory.register("p", config)
