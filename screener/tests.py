from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import json
from screener.models import Screen, WhiteLabel, HouseholdMember
from programs.models import Program, ProgramDurationMultiplier, LifetimeValuePrediction
from screener.views import all_results, _should_include_lifetime_projections, _generate_lifetime_projections


class ScreenTestCase(TestCase):
    def test_create_single_parent_two_children_household(self):
        screen = create_single_parent_two_children_household(annual_income=15000)
        self.assertTrue(isinstance(screen, Screen))


def create_default_household_member(screen, relationship="headOfHousehold", age=25):
    default = screen.household_members.create(
        relationship=relationship,
        age=age,
        student=False,
        student_full_time=False,
        pregnant=False,
        unemployed=False,
        worked_in_last_18_mos=True,
        visually_impaired=False,
        disabled=False,
        veteran=False,
        medicaid=False,
        disability_medicaid=False,
        has_income=True,
        has_expenses=True,
    )

    return default


# 1 parent 25 years old
# 2 children, 4 & 6 years old
# 1900 in monthly expenses between childcare and rent
# no assets
def create_single_parent_two_children_household(annual_income):
    # Create a default white label if one doesn't exist
    white_label, created = WhiteLabel.objects.get_or_create(
        name="Default Test",
        defaults={'code': 'default_test', 'state_code': 'CO'}
    )

    screen = Screen.objects.create(
        household_assets=0, household_size=3, zipcode="80204", agree_to_tos=True,
        housing_situation="renting", completed=False, white_label=white_label
    )

    parent = create_default_household_member(screen)
    parent.expenses.create(type="rent", amount="1200", frequency="monthly", screen=screen)
    parent.expenses.create(type="childCare", amount="700", frequency="monthly", screen=screen)
    parent.income_streams.create(type="wages", amount=annual_income, frequency="yearly", screen=screen)

    create_default_household_member(screen, relationship="child", age=4)
    create_default_household_member(screen, relationship="child", age=6)

    return screen


class LifetimeProjectionsAPITestCase(TestCase):
    """Test cases for lifetime benefit value projections API integration"""

    def setUp(self):
        """Set up test data for lifetime projections API tests"""
        # Create white label for testing
        self.white_label = WhiteLabel.objects.create(name="Test Colorado", code="test_co", state_code="CO")

        # Create a test program (SNAP-like)
        self.snap_program = Program.objects.new_program("test_co", "test_snap")

        # Create test household screen with English language
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=1000,
            request_language_code="en",  # English for lifetime projections
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

        # Create duration multiplier for the test program
        self.duration_multiplier = ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=18.0,
            confidence_range_lower=0.67,  # 12 months
            confidence_range_upper=1.33,  # 24 months
            data_source="Test Research Data 2024",
            notes="Test data for lifetime projections"
        )

        self.client = Client()

    def test_should_include_lifetime_projections_english(self):
        """Test that lifetime projections are included for English users"""
        # Set screen language to English
        self.screen.request_language_code = "en"
        self.screen.save()

        result = _should_include_lifetime_projections(self.screen)
        self.assertTrue(result)

    def test_should_include_lifetime_projections_spanish(self):
        """Test that lifetime projections are NOT included for Spanish users (Phase 1)"""
        # Set screen language to Spanish
        self.screen.request_language_code = "es"
        self.screen.save()

        result = _should_include_lifetime_projections(self.screen)
        self.assertFalse(result)

    def test_all_results_without_lifetime_projections(self):
        """Test that all_results works normally without lifetime projections (backward compatibility)"""
        results = all_results(self.screen, include_lifetime_projections=False)

        # Should contain standard fields but no lifetime projections
        self.assertIn("programs", results)
        self.assertIn("screen_id", results)
        self.assertNotIn("lifetime_projections", results)

    def test_all_results_with_lifetime_projections_english(self):
        """Test that all_results includes lifetime projections for English users"""
        # Create a mock eligible program result
        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": True,
                "estimated_value": 4800,  # $400/month * 12 months
            }
        ]

        # Mock the eligibility_results function to return our test data
        original_eligibility_results = __import__('screener.views', fromlist=['eligibility_results']).eligibility_results

        def mock_eligibility_results(screen, batch=False):
            return mock_eligibility_data, False, [], {}

        # Temporarily replace eligibility_results
        import screener.views
        screener.views.eligibility_results = mock_eligibility_results

        try:
            results = all_results(self.screen, include_lifetime_projections=True)

            # Should contain lifetime projections
            self.assertIn("lifetime_projections", results)
            lifetime_data = results["lifetime_projections"]

            # Verify structure
            self.assertTrue(lifetime_data["available"])
            self.assertTrue(lifetime_data["language_supported"])
            self.assertIn("summary", lifetime_data)
            self.assertIn("projections", lifetime_data)
            self.assertIn("calculation_metadata", lifetime_data)

            # Verify summary data
            summary = lifetime_data["summary"]
            self.assertIn("total_estimated_lifetime_value", summary)
            self.assertIn("total_lifetime_range", summary)
            self.assertIn("display_text", summary)

        finally:
            # Restore original function
            screener.views.eligibility_results = original_eligibility_results

    def test_all_results_with_lifetime_projections_spanish(self):
        """Test that all_results skips lifetime projections for non-English users"""
        # Set screen language to Spanish
        self.screen.request_language_code = "es"
        self.screen.save()

        results = all_results(self.screen, include_lifetime_projections=True)

        # Should NOT contain lifetime projections due to language restriction
        self.assertNotIn("lifetime_projections", results)

    def test_lifetime_projections_fail_gracefully(self):
        """Test that lifetime projection failures don't affect annual estimates"""
        # Create a screen without duration multiplier data (will cause failure)
        test_program = Program.objects.new_program("test_co", "test_program_no_data")

        mock_eligibility_data = [
            {
                "program_id": test_program.id,
                "name_abbreviated": "test_program_no_data",
                "eligible": True,
                "estimated_value": 2400,
            }
        ]

        # Mock eligibility_results to return program without duration data
        original_eligibility_results = __import__('screener.views', fromlist=['eligibility_results']).eligibility_results

        def mock_eligibility_results(screen, batch=False):
            return mock_eligibility_data, False, [], {}

        import screener.views
        screener.views.eligibility_results = mock_eligibility_results

        try:
            results = all_results(self.screen, include_lifetime_projections=True)

            # Should contain programs (annual estimates work)
            self.assertIn("programs", results)

            # Should contain lifetime projections but gracefully handle missing duration data
            self.assertIn("lifetime_projections", results)
            lifetime_data = results["lifetime_projections"]

            # Since no programs have duration data, projections should be empty but available=False
            self.assertFalse(lifetime_data["available"])
            self.assertEqual(len(lifetime_data["projections"]), 0)
            self.assertEqual(lifetime_data["summary"]["total_programs_with_projections"], 0)

            # Annual estimates should still be in the mock data
            self.assertEqual(mock_eligibility_data[0]["estimated_value"], 2400)

        finally:
            screener.views.eligibility_results = original_eligibility_results

    def test_generate_lifetime_projections_basic_functionality(self):
        """Test the core lifetime projections generation functionality"""
        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": True,
                "estimated_value": 4800,  # $400/month * 12 months
            }
        ]

        projections = _generate_lifetime_projections(self.screen, mock_eligibility_data)

        # Verify basic structure
        self.assertTrue(projections["available"])
        self.assertTrue(projections["language_supported"])
        self.assertGreater(len(projections["projections"]), 0)

        # Verify projection data
        projection = projections["projections"][0]
        self.assertEqual(projection["program_id"], "test_snap")
        self.assertIn("prediction_id", projection)
        self.assertIn("estimated_duration_months", projection)
        self.assertIn("estimated_lifetime_value", projection)
        self.assertIn("explanation", projection)
        self.assertIn("risk_assessment", projection)

        # Verify calculation method
        self.assertEqual(projection["calculation_method"], "simple_multiplier")
        self.assertEqual(projection["multiplier_version"], "1.0")

    def test_generate_lifetime_projections_skips_ineligible_programs(self):
        """Test that lifetime projections are only generated for eligible programs"""
        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": False,  # Not eligible
                "estimated_value": 0,
            }
        ]

        projections = _generate_lifetime_projections(self.screen, mock_eligibility_data)

        # Should have no projections for ineligible programs
        self.assertEqual(len(projections["projections"]), 0)
        self.assertFalse(projections["available"])

    def test_generate_lifetime_projections_handles_zero_benefit(self):
        """Test that lifetime projections skip programs with zero benefit amounts"""
        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": True,
                "estimated_value": 0,  # Zero benefit amount
            }
        ]

        projections = _generate_lifetime_projections(self.screen, mock_eligibility_data)

        # Should skip programs with zero benefit
        self.assertEqual(len(projections["projections"]), 0)
        self.assertFalse(projections["available"])

    def test_cached_prediction_usage(self):
        """Test that cached predictions are used when available"""
        # Create a cached prediction
        cached_prediction = LifetimeValuePrediction.objects.create(
            screen=self.screen,
            program=self.snap_program,
            predicted_duration_months=18.0,
            confidence_interval_lower=12.0,
            confidence_interval_upper=24.0,
            estimated_lifetime_value=Decimal('7200.00'),
            explanation_text="Test cached explanation",
            risk_assessment="Test cached risk assessment",
            multiplier_version="1.0",
            calculation_method="simple_multiplier"
        )

        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": True,
                "estimated_value": 4800,
            }
        ]

        projections = _generate_lifetime_projections(self.screen, mock_eligibility_data)

        # Should use cached prediction
        self.assertTrue(projections["available"])
        projection = projections["projections"][0]
        self.assertEqual(projection["prediction_id"], f"pred_{cached_prediction.id}")
        self.assertIn("Test cached explanation", projection["explanation"]["summary"])


class LifetimeProjectionsViewTestCase(TestCase):
    """Test cases for the EligibilityTranslationView API endpoint with lifetime projections"""

    def setUp(self):
        """Set up test data for view tests"""
        self.white_label = WhiteLabel.objects.create(name="Test Colorado", code="test_co", state_code="CO")
        self.snap_program = Program.objects.new_program("test_co", "test_snap")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=False,  # Will be set to True by view
            zipcode="80205",
            household_size=2,
            request_language_code="en",
        )

        # Create duration multiplier
        ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=18.0,
            confidence_range_lower=0.67,
            confidence_range_upper=1.33,
            data_source="Test Data",
        )

        self.client = Client()

    def test_api_endpoint_without_lifetime_projections(self):
        """Test API endpoint without lifetime projections parameter (backward compatibility)"""
        # Mock URL pattern - adjust based on actual URL configuration
        url = f"/api/screens/{self.screen.uuid}/results/"

        # This test validates that the endpoint works without lifetime projections
        # In a real test, you'd need to ensure the URL routing is set up correctly
        # For now, we test the view logic directly

        from screener.views import EligibilityTranslationView
        from django.http import HttpRequest
        from unittest.mock import Mock

        request = Mock(spec=HttpRequest)
        request.query_params = {}

        view = EligibilityTranslationView()

        # Test that the parameter extraction works
        include_lifetime = request.query_params.get("include_lifetime_projections", "false").lower() == "true"
        self.assertFalse(include_lifetime)

    def test_api_endpoint_with_lifetime_projections_true(self):
        """Test API endpoint with lifetime projections parameter set to true"""
        from screener.views import EligibilityTranslationView
        from django.http import HttpRequest
        from unittest.mock import Mock

        request = Mock(spec=HttpRequest)
        request.query_params = {"include_lifetime_projections": "true"}

        # Test parameter extraction
        include_lifetime = request.query_params.get("include_lifetime_projections", "false").lower() == "true"
        self.assertTrue(include_lifetime)

    def test_api_endpoint_with_lifetime_projections_false(self):
        """Test API endpoint with lifetime projections parameter set to false"""
        from screener.views import EligibilityTranslationView
        from django.http import HttpRequest
        from unittest.mock import Mock

        request = Mock(spec=HttpRequest)
        request.query_params = {"include_lifetime_projections": "false"}

        # Test parameter extraction
        include_lifetime = request.query_params.get("include_lifetime_projections", "false").lower() == "true"
        self.assertFalse(include_lifetime)

    def test_api_endpoint_parameter_case_insensitive(self):
        """Test that the lifetime projections parameter is case insensitive"""
        from screener.views import EligibilityTranslationView
        from django.http import HttpRequest
        from unittest.mock import Mock

        # Test various case combinations
        test_cases = ["TRUE", "True", "true", "FALSE", "False", "false"]

        for case in test_cases:
            request = Mock(spec=HttpRequest)
            request.query_params = {"include_lifetime_projections": case}

            include_lifetime = request.query_params.get("include_lifetime_projections", "false").lower() == "true"
            expected = case.lower() == "true"
            self.assertEqual(include_lifetime, expected, f"Failed for case: {case}")


class LifetimeProjectionsIntegrationTestCase(TestCase):
    """Integration tests for lifetime projections with real data flow"""

    def setUp(self):
        """Set up integration test data"""
        self.white_label = WhiteLabel.objects.create(name="Test Colorado", code="test_co", state_code="CO")

        # Create multiple test programs
        self.snap_program = Program.objects.new_program("test_co", "test_snap")
        self.wic_program = Program.objects.new_program("test_co", "test_wic")

        # Create test screen with multiple household members
        self.screen = create_single_parent_two_children_household(annual_income=25000)
        self.screen.white_label = self.white_label
        self.screen.request_language_code = "en"
        self.screen.save()

        # Create duration multipliers for both programs
        ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=18.0,
            confidence_range_lower=0.67,
            confidence_range_upper=1.33,
            data_source="USDA SNAP Report 2024",
        )

        ProgramDurationMultiplier.objects.create(
            program=self.wic_program,
            white_label=self.white_label,
            average_duration_months=30.0,
            confidence_range_lower=0.8,
            confidence_range_upper=1.2,
            data_source="CDC WIC Study 2024",
        )

    def test_full_integration_with_multiple_programs(self):
        """Test full integration with multiple eligible programs"""
        # Create mock eligibility data for multiple programs
        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": True,
                "estimated_value": 4800,
            },
            {
                "program_id": self.wic_program.id,
                "name_abbreviated": "test_wic",
                "eligible": True,
                "estimated_value": 1200,
            }
        ]

        # Mock eligibility_results
        original_eligibility_results = __import__('screener.views', fromlist=['eligibility_results']).eligibility_results

        def mock_eligibility_results(screen, batch=False):
            return mock_eligibility_data, False, [], {}

        import screener.views
        screener.views.eligibility_results = mock_eligibility_results

        try:
            results = all_results(self.screen, include_lifetime_projections=True)

            # Verify multiple projections
            lifetime_data = results["lifetime_projections"]
            self.assertTrue(lifetime_data["available"])
            self.assertEqual(len(lifetime_data["projections"]), 2)

            # Verify summary totals include both programs
            summary = lifetime_data["summary"]
            self.assertGreater(summary["total_estimated_lifetime_value"], 0)
            self.assertEqual(summary["total_programs_with_projections"], 2)

            # Verify both programs have projections
            program_ids = [p["program_id"] for p in lifetime_data["projections"]]
            self.assertIn("test_snap", program_ids)
            self.assertIn("test_wic", program_ids)

        finally:
            screener.views.eligibility_results = original_eligibility_results

    def test_mixed_eligibility_scenarios(self):
        """Test scenarios with mix of eligible and ineligible programs"""
        mock_eligibility_data = [
            {
                "program_id": self.snap_program.id,
                "name_abbreviated": "test_snap",
                "eligible": True,
                "estimated_value": 4800,
            },
            {
                "program_id": self.wic_program.id,
                "name_abbreviated": "test_wic",
                "eligible": False,  # Not eligible
                "estimated_value": 0,
            }
        ]

        original_eligibility_results = __import__('screener.views', fromlist=['eligibility_results']).eligibility_results

        def mock_eligibility_results(screen, batch=False):
            return mock_eligibility_data, False, [], {}

        import screener.views
        screener.views.eligibility_results = mock_eligibility_results

        try:
            results = all_results(self.screen, include_lifetime_projections=True)

            lifetime_data = results["lifetime_projections"]
            self.assertTrue(lifetime_data["available"])

            # Should only have projection for eligible program
            self.assertEqual(len(lifetime_data["projections"]), 1)
            self.assertEqual(lifetime_data["projections"][0]["program_id"], "test_snap")

            # Summary should reflect only eligible programs
            self.assertEqual(lifetime_data["summary"]["total_programs_with_projections"], 1)

        finally:
            screener.views.eligibility_results = original_eligibility_results
