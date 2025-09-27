from django.test import TestCase
from decimal import Decimal
from programs.models import Program, ProgramDurationMultiplier, LifetimeValuePrediction
from programs.services.duration_calculation_service import SimpleDurationService
from programs.services.lifetime_value_service import LifetimeValueService
from screener.models import Screen, WhiteLabel, HouseholdMember


class TestSNAPLifetimeValueCalculation(TestCase):
    """Test SNAP-specific lifetime benefit value calculation"""

    def setUp(self):
        """Set up test data for SNAP lifetime value calculation"""
        # Create white label for testing
        self.white_label = WhiteLabel.objects.create(name="Test Colorado", code="test_co", state_code="CO")

        # Use the ProgramManager to create a SNAP program properly
        self.snap_program = Program.objects.new_program("test_co", "test_snap")

        # Create test household screen
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=1000,
        )

        # Create household members
        self.head_of_household = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
        )

        self.child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=8,
            student=True,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
        )

    def test_program_duration_multiplier_model_exists(self):
        """Test that ProgramDurationMultiplier model can be created for SNAP"""
        # This test will fail until we create the model
        duration_multiplier = ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=15.0,  # Research-based average
            confidence_range_lower=0.67,  # 10 months (15 * 0.67)
            confidence_range_upper=1.33,  # 20 months (15 * 1.33)
            data_source="USDA 2024 SNAP Participation Report",
            notes="Based on working households with children demographic",
        )

        self.assertEqual(duration_multiplier.program, self.snap_program)
        self.assertEqual(duration_multiplier.average_duration_months, 15.0)
        self.assertIn("USDA", duration_multiplier.data_source)

    def test_lifetime_value_prediction_model_exists(self):
        """Test that LifetimeValuePrediction model can be created"""
        # This test will fail until we create the model
        prediction = LifetimeValuePrediction.objects.create(
            screen=self.screen,
            program=self.snap_program,
            predicted_duration_months=15.0,
            confidence_interval_lower=10.0,
            confidence_interval_upper=20.0,
            estimated_lifetime_value=Decimal("4350.00"),  # $290/month * 15 months
            explanation_text="Based on similar households, you might receive SNAP for about 15 months.",
            risk_assessment="Duration may vary based on employment changes.",
            multiplier_version="1.0",
            calculation_method="simple_multiplier",
        )

        self.assertEqual(prediction.screen, self.screen)
        self.assertEqual(prediction.program, self.snap_program)
        self.assertEqual(prediction.predicted_duration_months, 15.0)
        self.assertEqual(prediction.estimated_lifetime_value, Decimal("4350.00"))

    def test_simple_duration_service_calculates_snap_duration(self):
        """Test SimpleDurationService calculates SNAP duration from multiplier"""
        # Create duration multiplier for SNAP
        ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=15.0,
            confidence_range_lower=0.67,
            confidence_range_upper=1.33,
            data_source="USDA 2024 Report",
        )

        # Test SimpleDurationService
        service = SimpleDurationService()
        duration_data = service.calculate_duration(self.snap_program, self.white_label)

        expected_data = {
            "average_duration_months": 15.0,
            "confidence_range": (10.05, 19.95),  # 15 * 0.67, 15 * 1.33
            "data_source": "USDA 2024 Report",
        }

        self.assertEqual(duration_data["average_duration_months"], expected_data["average_duration_months"])
        self.assertAlmostEqual(duration_data["confidence_range"][0], expected_data["confidence_range"][0], places=2)
        self.assertAlmostEqual(duration_data["confidence_range"][1], expected_data["confidence_range"][1], places=2)
        self.assertEqual(duration_data["data_source"], expected_data["data_source"])

    def test_lifetime_value_service_generates_snap_prediction(self):
        """Test LifetimeValueService generates complete SNAP lifetime prediction"""
        # Create duration multiplier
        ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=15.0,
            confidence_range_lower=0.67,
            confidence_range_upper=1.33,
            data_source="USDA 2024 Report",
        )

        # Test LifetimeValueService
        service = LifetimeValueService()
        monthly_benefit = Decimal("290.00")  # Typical SNAP benefit for family of 2 (adult + child)

        prediction = service.generate_prediction(
            screen=self.screen, program=self.snap_program, monthly_benefit=monthly_benefit
        )

        # Assertions for prediction values
        self.assertEqual(prediction.screen, self.screen)
        self.assertEqual(prediction.program, self.snap_program)
        self.assertEqual(prediction.predicted_duration_months, 15.0)
        self.assertEqual(prediction.estimated_lifetime_value, Decimal("4350.00"))  # 290 * 15
        self.assertEqual(prediction.calculation_method, "simple_multiplier")
        self.assertIn("SNAP", prediction.explanation_text)
        self.assertTrue(len(prediction.explanation_text) > 50)  # Should have meaningful explanation

    # TODO: Implement these remaining tests
    # def test_snap_lifetime_value_with_demographic_adjustments(self):
    # def test_snap_lifetime_value_confidence_intervals(self):
    # def test_snap_lifetime_value_caching(self):
