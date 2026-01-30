"""
Unit tests for NPS (Net Promoter Score) functionality.
"""

from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from screener.models import Screen, WhiteLabel, EligibilitySnapshot, NPSScore
from screener.serializers import NPSScoreSerializer


class TestNPSScoreSerializer(TestCase):
    """Tests for NPSScoreSerializer."""

    def setUp(self):
        """Set up test data."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=True
        )
        self.snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)

    def test_valid_score_submission(self):
        """Test submitting a valid NPS score."""
        data = {"uuid": str(self.screen.uuid), "score": 8, "variant": "floating"}
        serializer = NPSScoreSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        nps_score = serializer.save()

        self.assertEqual(nps_score.score, 8)
        self.assertEqual(nps_score.variant, "floating")
        self.assertEqual(nps_score.eligibility_snapshot, self.snapshot)

    def test_score_range_minimum(self):
        """Test that score of 0 is valid."""
        data = {"uuid": str(self.screen.uuid), "score": 0, "variant": "inline"}
        serializer = NPSScoreSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        nps_score = serializer.save()
        self.assertEqual(nps_score.score, 0)

    def test_score_range_maximum(self):
        """Test that score of 10 is valid."""
        data = {"uuid": str(self.screen.uuid), "score": 10, "variant": "inline"}
        serializer = NPSScoreSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        nps_score = serializer.save()
        self.assertEqual(nps_score.score, 10)

    def test_score_below_minimum_invalid(self):
        """Test that score below 0 is invalid."""
        data = {"uuid": str(self.screen.uuid), "score": -1, "variant": "floating"}
        serializer = NPSScoreSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("score", serializer.errors)

    def test_score_above_maximum_invalid(self):
        """Test that score above 10 is invalid."""
        data = {"uuid": str(self.screen.uuid), "score": 11, "variant": "floating"}
        serializer = NPSScoreSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("score", serializer.errors)

    def test_invalid_uuid_no_snapshot(self):
        """Test that invalid uuid returns error."""
        data = {"uuid": "00000000-0000-0000-0000-000000000000", "score": 5, "variant": "floating"}
        serializer = NPSScoreSerializer(data=data)

        self.assertTrue(serializer.is_valid())  # UUID format is valid
        with self.assertRaises(Exception):
            serializer.save()  # But no snapshot exists

    def test_duplicate_submission_rejected(self):
        """Test that submitting NPS twice for same snapshot is rejected."""
        data = {"uuid": str(self.screen.uuid), "score": 8, "variant": "floating"}

        # First submission should work
        serializer1 = NPSScoreSerializer(data=data)
        self.assertTrue(serializer1.is_valid())
        serializer1.save()

        # Second submission should fail
        serializer2 = NPSScoreSerializer(data={"uuid": str(self.screen.uuid), "score": 9, "variant": "inline"})
        self.assertTrue(serializer2.is_valid())  # Data is valid
        with self.assertRaises(Exception):
            serializer2.save()  # But save should fail

    def test_variant_optional(self):
        """Test that variant field is optional."""
        data = {"uuid": str(self.screen.uuid), "score": 7}
        serializer = NPSScoreSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        nps_score = serializer.save()
        self.assertIsNone(nps_score.variant)

    def test_uses_most_recent_snapshot(self):
        """Test that serializer uses the most recent non-error snapshot."""
        # Create an older snapshot
        older_snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)

        # The setUp created self.snapshot which should be more recent
        data = {"uuid": str(self.screen.uuid), "score": 6, "variant": "inline"}
        serializer = NPSScoreSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        nps_score = serializer.save()

        # Should be linked to the most recent snapshot (self.snapshot)
        self.assertEqual(nps_score.eligibility_snapshot, self.snapshot)

    def test_ignores_error_snapshots(self):
        """Test that snapshots with had_error=True are ignored."""
        # Mark the good snapshot as error
        self.snapshot.had_error = True
        self.snapshot.save()

        data = {"uuid": str(self.screen.uuid), "score": 5, "variant": "floating"}
        serializer = NPSScoreSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(Exception):
            serializer.save()  # No valid snapshot exists


class TestNPSScoreView(APITestCase):
    """Tests for NPSScoreView API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=True
        )
        self.snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)
        self.url = "/api/nps/"

    def test_post_valid_nps_score(self):
        """Test successful NPS score submission."""
        data = {"uuid": str(self.screen.uuid), "score": 9, "variant": "floating"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"status": "success"})
        self.assertTrue(NPSScore.objects.filter(eligibility_snapshot=self.snapshot).exists())

    def test_post_invalid_score(self):
        """Test that invalid score returns 400."""
        data = {"uuid": str(self.screen.uuid), "score": 15, "variant": "floating"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("score", response.data)

    def test_post_missing_required_fields(self):
        """Test that missing required fields returns 400."""
        data = {"variant": "floating"}  # Missing uuid and score
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_invalid_uuid(self):
        """Test that invalid uuid returns 400."""
        data = {"uuid": "00000000-0000-0000-0000-000000000000", "score": 5, "variant": "inline"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uuid", response.data)

    def test_post_duplicate_submission(self):
        """Test that duplicate submission returns 400."""
        data = {"uuid": str(self.screen.uuid), "score": 8, "variant": "floating"}

        # First submission
        response1 = self.client.post(self.url, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second submission
        response2 = self.client.post(self.url, data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_authentication_required(self):
        """Test that endpoint is accessible without authentication."""
        # Client has no authentication set up
        data = {"uuid": str(self.screen.uuid), "score": 7, "variant": "inline"}
        response = self.client.post(self.url, data, format="json")

        # Should succeed without auth
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
