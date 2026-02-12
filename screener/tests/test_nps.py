"""
Unit tests for NPS (Net Promoter Score) functionality.
"""

from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from screener.models import Screen, WhiteLabel, EligibilitySnapshot, NPSScore
from screener.serializers import NPSScoreSerializer, NPSScoreReasonSerializer


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


class TestNPSScoreReasonSerializer(TestCase):
    """Tests for NPSScoreReasonSerializer."""

    def setUp(self):
        """Set up test data."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=True
        )
        self.snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)
        # Create an existing NPS score to update
        self.nps_score = NPSScore.objects.create(eligibility_snapshot=self.snapshot, score=8, variant="floating")

    def test_valid_reason_submission(self):
        """Test submitting a valid score reason."""
        data = {"uuid": str(self.screen.uuid), "score_reason": "The tool was very helpful"}
        serializer = NPSScoreReasonSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        nps_score = serializer.update_reason(serializer.validated_data)

        self.assertEqual(nps_score.score_reason, "The tool was very helpful")
        self.assertEqual(nps_score.score, 8)  # Original score unchanged

    def test_reason_updates_existing_score(self):
        """Test that reason is added to an existing NPS score record."""
        data = {"uuid": str(self.screen.uuid), "score_reason": "Easy to use"}
        serializer = NPSScoreReasonSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        serializer.update_reason(serializer.validated_data)

        self.nps_score.refresh_from_db()
        self.assertEqual(self.nps_score.score_reason, "Easy to use")

    def test_reason_can_be_overwritten(self):
        """Test that a reason can be updated with a new value."""
        self.nps_score.score_reason = "First reason"
        self.nps_score.save()

        data = {"uuid": str(self.screen.uuid), "score_reason": "Updated reason"}
        serializer = NPSScoreReasonSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        serializer.update_reason(serializer.validated_data)

        self.nps_score.refresh_from_db()
        self.assertEqual(self.nps_score.score_reason, "Updated reason")

    def test_invalid_uuid_no_snapshot(self):
        """Test that invalid uuid returns error."""
        data = {"uuid": "00000000-0000-0000-0000-000000000000", "score_reason": "Some reason"}
        serializer = NPSScoreReasonSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        with self.assertRaises(Exception):
            serializer.update_reason(serializer.validated_data)

    def test_no_nps_score_exists(self):
        """Test that error is raised when no NPS score exists for the snapshot."""
        self.nps_score.delete()

        data = {"uuid": str(self.screen.uuid), "score_reason": "Some reason"}
        serializer = NPSScoreReasonSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        with self.assertRaises(Exception):
            serializer.update_reason(serializer.validated_data)

    def test_missing_score_reason(self):
        """Test that score_reason is required."""
        data = {"uuid": str(self.screen.uuid)}
        serializer = NPSScoreReasonSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("score_reason", serializer.errors)

    def test_missing_uuid(self):
        """Test that uuid is required."""
        data = {"score_reason": "Some reason"}
        serializer = NPSScoreReasonSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("uuid", serializer.errors)

    def test_uses_most_recent_snapshot(self):
        """Test that serializer uses the most recent non-error snapshot."""
        # Create a newer snapshot with its own NPS score
        newer_snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)
        newer_nps = NPSScore.objects.create(eligibility_snapshot=newer_snapshot, score=5, variant="inline")

        data = {"uuid": str(self.screen.uuid), "score_reason": "Recent feedback"}
        serializer = NPSScoreReasonSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        result = serializer.update_reason(serializer.validated_data)

        self.assertEqual(result.id, newer_nps.id)
        self.assertEqual(result.score_reason, "Recent feedback")

    def test_ignores_error_snapshots(self):
        """Test that snapshots with had_error=True are ignored."""
        self.snapshot.had_error = True
        self.snapshot.save()

        data = {"uuid": str(self.screen.uuid), "score_reason": "Some reason"}
        serializer = NPSScoreReasonSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(Exception):
            serializer.update_reason(serializer.validated_data)


class TestNPSScoreReasonView(APITestCase):
    """Tests for NPSScoreView PATCH endpoint (score reason)."""

    def setUp(self):
        """Set up test data."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=True
        )
        self.snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)
        self.nps_score = NPSScore.objects.create(eligibility_snapshot=self.snapshot, score=8, variant="floating")
        self.url = "/api/nps/"

    def test_patch_valid_reason(self):
        """Test successful reason submission via PATCH."""
        data = {"uuid": str(self.screen.uuid), "score_reason": "Great experience"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "success"})

        self.nps_score.refresh_from_db()
        self.assertEqual(self.nps_score.score_reason, "Great experience")

    def test_patch_missing_reason(self):
        """Test that missing score_reason returns 400."""
        data = {"uuid": str(self.screen.uuid)}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("score_reason", response.data)

    def test_patch_missing_uuid(self):
        """Test that missing uuid returns 400."""
        data = {"score_reason": "Some reason"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uuid", response.data)

    def test_patch_invalid_uuid(self):
        """Test that invalid uuid returns 400."""
        data = {"uuid": "00000000-0000-0000-0000-000000000000", "score_reason": "Some reason"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uuid", response.data)

    def test_patch_no_nps_score(self):
        """Test that PATCH fails when no NPS score exists."""
        self.nps_score.delete()

        data = {"uuid": str(self.screen.uuid), "score_reason": "Some reason"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uuid", response.data)

    def test_patch_no_authentication_required(self):
        """Test that PATCH endpoint is accessible without authentication."""
        data = {"uuid": str(self.screen.uuid), "score_reason": "No auth needed"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_full_nps_flow(self):
        """Test the full flow: POST score then PATCH reason."""
        # Delete the pre-created NPS score
        self.nps_score.delete()

        # Step 1: Submit NPS score
        score_data = {"uuid": str(self.screen.uuid), "score": 9, "variant": "inline"}
        response1 = self.client.post(self.url, score_data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Step 2: Submit followup reason
        reason_data = {"uuid": str(self.screen.uuid), "score_reason": "Very useful tool"}
        response2 = self.client.patch(self.url, reason_data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Verify both score and reason are saved
        nps = NPSScore.objects.get(eligibility_snapshot=self.snapshot)
        self.assertEqual(nps.score, 9)
        self.assertEqual(nps.variant, "inline")
        self.assertEqual(nps.score_reason, "Very useful tool")
