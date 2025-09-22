"""
Integration test for SNAP lifetime benefit value calculation.
Tests the complete flow from household data to lifetime prediction.
"""

from django.test import TestCase
from decimal import Decimal
from programs.models import Program, ProgramDurationMultiplier, LifetimeValuePrediction
from programs.services.lifetime_value_service import LifetimeValueService
from screener.models import Screen, WhiteLabel, HouseholdMember


class TestSNAPLifetimeValueIntegration(TestCase):
    """Integration test for complete SNAP lifetime benefit value calculation flow"""

    def setUp(self):
        """Set up realistic household data for SNAP lifetime value testing"""
        # Get or create Colorado white label
        self.white_label, _ = WhiteLabel.objects.get_or_create(
            code="co", defaults={"name": "Colorado", "state_code": "CO"}
        )

        # Get or create SNAP program
        try:
            self.snap_program = Program.objects.get(name_abbreviated="co_snap")
        except Program.DoesNotExist:
            self.snap_program = Program.objects.new_program("co", "co_snap")

        # Create duration multiplier with real research data
        self.duration_multiplier, _ = ProgramDurationMultiplier.objects.get_or_create(
            program=self.snap_program,
            white_label=self.white_label,
            defaults={
                "average_duration_months": 15.0,
                "confidence_range_lower": 0.67,
                "confidence_range_upper": 1.33,
                "data_source": "USDA 2024 SNAP Participation Report - Working Households with Children",
                "notes": "Based on research from snap_research_20241219_143052.csv",
            },
        )

        # Create realistic household screen
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=True,
            zipcode="80205",
            county="Denver County",
            household_size=3,
            household_assets=1500,  # Below SNAP asset limits
            housing_situation="rent",
        )

        # Create household members - working parent with two children
        self.parent = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=32,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
            has_income=True,
            has_expenses=False,
        )

        self.child1 = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=8,
            student=True,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
            has_income=False,
            has_expenses=False,
        )

        self.child2 = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=5,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
            has_income=False,
            has_expenses=False,
        )

    def test_complete_snap_lifetime_value_flow(self):
        """Test complete flow from household data to lifetime prediction"""
        # Simulate typical SNAP benefit calculation result
        # For a family of 3 with low income, typical SNAP benefit is ~$250/month
        monthly_snap_benefit = Decimal("250.00")

        # Generate lifetime prediction
        service = LifetimeValueService()
        prediction = service.generate_prediction(
            screen=self.screen, program=self.snap_program, monthly_benefit=monthly_snap_benefit
        )

        # Verify prediction data
        self.assertEqual(prediction.screen, self.screen)
        self.assertEqual(prediction.program, self.snap_program)
        self.assertEqual(prediction.predicted_duration_months, 15.0)
        self.assertEqual(prediction.estimated_lifetime_value, Decimal("3750.00"))  # 250 * 15

        # Verify confidence intervals
        self.assertAlmostEqual(prediction.confidence_interval_lower, 10.05, places=1)  # 15 * 0.67
        self.assertAlmostEqual(prediction.confidence_interval_upper, 19.95, places=1)  # 15 * 1.33

        # Verify explanation contains key information
        explanation = prediction.explanation_text
        self.assertIn("SNAP", explanation)
        self.assertIn("15", explanation)  # Duration
        self.assertIn("250", explanation)  # Monthly benefit
        self.assertIn("3,750", explanation)  # Lifetime value

        # Verify risk assessment
        risk_assessment = prediction.risk_assessment
        self.assertIn("10", risk_assessment)  # Lower bound
        self.assertIn("20", risk_assessment)  # Upper bound
        self.assertIn("income", risk_assessment)  # Risk factor

        # Verify metadata
        self.assertEqual(prediction.calculation_method, "simple_multiplier")
        self.assertEqual(prediction.multiplier_version, "1.0")

    def test_snap_lifetime_value_for_elderly_household(self):
        """Test SNAP lifetime value for elderly household (expected longer duration)"""
        # Create elderly household member
        elderly_screen = Screen.objects.create(
            white_label=self.white_label,
            completed=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=3000,
            housing_situation="own",
        )

        elderly_member = HouseholdMember.objects.create(
            screen=elderly_screen,
            relationship="headOfHousehold",
            age=68,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=True,  # Elderly and disabled
            veteran=False,
            has_income=True,
            has_expenses=False,
        )

        # Update duration multiplier for elderly/disabled (longer duration)
        elderly_multiplier = self.duration_multiplier
        elderly_multiplier.average_duration_months = 24.0  # Longer for elderly/disabled
        elderly_multiplier.confidence_range_lower = 0.75
        elderly_multiplier.confidence_range_upper = 1.25
        elderly_multiplier.data_source = "USDA 2024 Report - Elderly/Disabled Households"
        elderly_multiplier.notes = "Adjusted for elderly/disabled demographics"
        elderly_multiplier.save()

        # Higher SNAP benefit for elderly household
        monthly_benefit = Decimal("300.00")

        service = LifetimeValueService()
        prediction = service.generate_prediction(
            screen=elderly_screen, program=self.snap_program, monthly_benefit=monthly_benefit
        )

        # Should have longer duration and higher lifetime value
        self.assertEqual(prediction.predicted_duration_months, 24.0)
        self.assertEqual(prediction.estimated_lifetime_value, Decimal("7200.00"))  # 300 * 24

    def test_snap_prediction_caching(self):
        """Test that predictions are cached and retrievable"""
        monthly_benefit = Decimal("250.00")
        service = LifetimeValueService()

        # Generate first prediction
        prediction1 = service.generate_prediction(
            screen=self.screen, program=self.snap_program, monthly_benefit=monthly_benefit
        )

        # Get cached prediction
        cached_prediction = service.get_cached_prediction(self.screen, self.snap_program)

        # Should be the same prediction
        self.assertEqual(cached_prediction.id, prediction1.id)
        self.assertEqual(cached_prediction.estimated_lifetime_value, prediction1.estimated_lifetime_value)

    def test_snap_prediction_validation(self):
        """Test input validation for SNAP prediction generation"""
        service = LifetimeValueService()

        # Valid inputs
        self.assertTrue(
            service.validate_prediction_inputs(
                screen=self.screen, program=self.snap_program, monthly_benefit=Decimal("250.00")
            )
        )

        # Invalid monthly benefit (zero)
        self.assertFalse(
            service.validate_prediction_inputs(
                screen=self.screen, program=self.snap_program, monthly_benefit=Decimal("0.00")
            )
        )

        # Invalid monthly benefit (negative)
        self.assertFalse(
            service.validate_prediction_inputs(
                screen=self.screen, program=self.snap_program, monthly_benefit=Decimal("-100.00")
            )
        )

        # Invalid screen (no household size)
        invalid_screen = Screen.objects.create(
            white_label=self.white_label, completed=True, household_size=None  # Invalid
        )
        self.assertFalse(
            service.validate_prediction_inputs(
                screen=invalid_screen, program=self.snap_program, monthly_benefit=Decimal("250.00")
            )
        )

    def test_snap_duration_multiplier_requirements(self):
        """Test that duration multipliers are required for predictions"""
        # Create a new program without duration data
        test_program = Program.objects.new_program("co", "test_program")

        service = LifetimeValueService()

        # Should raise ValueError when no duration data exists
        with self.assertRaises(ValueError) as context:
            service.generate_prediction(screen=self.screen, program=test_program, monthly_benefit=Decimal("250.00"))

        self.assertIn("No duration multiplier found", str(context.exception))

    def test_snap_lifetime_value_calculation_accuracy(self):
        """Test accuracy of lifetime value calculation"""
        # Test with specific values
        test_cases = [
            {"monthly": Decimal("100.00"), "duration": 12.0, "expected": Decimal("1200.00")},
            {"monthly": Decimal("350.50"), "duration": 18.0, "expected": Decimal("6309.00")},
            {"monthly": Decimal("175.25"), "duration": 24.5, "expected": Decimal("4293.625")},
        ]

        for case in test_cases:
            # Update existing duration multiplier with test case data
            self.duration_multiplier.average_duration_months = case["duration"]
            self.duration_multiplier.confidence_range_lower = 0.8
            self.duration_multiplier.confidence_range_upper = 1.2
            self.duration_multiplier.data_source = "Test Case"
            self.duration_multiplier.notes = f"Test case for {case['monthly']} monthly benefit"
            self.duration_multiplier.save()

            service = LifetimeValueService()
            prediction = service.generate_prediction(
                screen=self.screen, program=self.snap_program, monthly_benefit=case["monthly"]
            )

            self.assertEqual(prediction.estimated_lifetime_value, case["expected"])
            self.assertEqual(prediction.predicted_duration_months, case["duration"])
