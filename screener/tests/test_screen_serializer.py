"""
Tests for the ScreenSerializer current-benefits write path (Step 5a / MFB-869).

The CurrentBenefit join table is the primary write target. Two write paths feed it:

* New frontend — `current_benefits: ["snap", "tanf"]` (list of name_abbreviated),
  written directly via a WL-scoped Program lookup.
* Old frontend (backward compat) — legacy `has_*` columns, mirrored into the join
  table through `_benefit_map_from_has_columns()`. Removed in Step 6 (MFB-720).

These cover `_write_current_benefits()` (the shared helper) directly and the
serializer `update()` path end to end.
"""

from django.test import TestCase

from screener.models import CurrentBenefit, Screen, WhiteLabel
from screener.serializers import ScreenSerializer, _write_current_benefits
from screener.tests.helpers import seed_program


class WriteCurrentBenefitsTests(TestCase):
    """Direct coverage of the `_write_current_benefits()` helper."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=False
        )
        seed_program(self.white_label, "snap", "tanf", "wic")

    def _benefit_names(self, screen):
        return set(CurrentBenefit.objects.filter(screen=screen).values_list("program__name_abbreviated", flat=True))

    def test_new_path_writes_requested_programs(self):
        """An explicit current_benefits list writes exactly those join-table rows."""
        _write_current_benefits(self.screen, ["snap", "tanf"])

        self.assertEqual(self._benefit_names(self.screen), {"snap", "tanf"})

    def test_new_path_empty_list_clears_rows(self):
        """An empty current_benefits list removes all rows (deselect-all)."""
        _write_current_benefits(self.screen, ["snap"])
        _write_current_benefits(self.screen, [])

        self.assertEqual(self._benefit_names(self.screen), set())

    def test_new_path_replaces_existing_rows(self):
        """A second write replaces the prior set rather than appending."""
        _write_current_benefits(self.screen, ["snap", "tanf"])
        _write_current_benefits(self.screen, ["wic"])

        self.assertEqual(self._benefit_names(self.screen), {"wic"})

    def test_new_path_skips_unknown_program_names(self):
        """Names with no Program in this WL are silently dropped, not errored."""
        _write_current_benefits(self.screen, ["snap", "not_a_real_program"])

        self.assertEqual(self._benefit_names(self.screen), {"snap"})

    def test_new_path_is_white_label_scoped(self):
        """A program name that exists only in another WL is not written."""
        other_wl = WhiteLabel.objects.create(name="Other", code="other", state_code="OT")
        seed_program(other_wl, "other_only")

        _write_current_benefits(self.screen, ["snap", "other_only"])

        self.assertEqual(self._benefit_names(self.screen), {"snap"})

    def test_backward_compat_path_mirrors_has_columns(self):
        """current_benefits=None mirrors the legacy has_* columns (fan-out included)."""
        seed_program(self.white_label, "co_snap")
        self.screen.has_snap = True
        self.screen.save()

        _write_current_benefits(self.screen, None)

        # has_snap fans out to every snap variant Program in this WL.
        self.assertEqual(self._benefit_names(self.screen), {"snap", "co_snap"})

    def test_backward_compat_path_compound_ssi_via_income(self):
        """current_benefits=None resolves the ssi compound condition from sSI income."""
        from screener.models import HouseholdMember, IncomeStream

        seed_program(self.white_label, "ssi")
        head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=40, has_income=True
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="sSI", amount=500, frequency="monthly"
        )

        _write_current_benefits(self.screen, None)

        self.assertIn("ssi", self._benefit_names(self.screen))


class ScreenSerializerUpdateTests(TestCase):
    """End-to-end coverage of `current_benefits` flowing through serializer.update()."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=False
        )
        seed_program(self.white_label, "snap", "tanf")

    def _base_payload(self, **extra):
        payload = {
            "white_label": self.white_label.code,
            "household_members": [],
            "expenses": [],
        }
        payload.update(extra)
        return payload

    def _benefit_names(self):
        return set(
            CurrentBenefit.objects.filter(screen=self.screen).values_list("program__name_abbreviated", flat=True)
        )

    def test_update_with_current_benefits_writes_join_table(self):
        """A PATCH carrying current_benefits writes the join table directly."""
        serializer = ScreenSerializer(self.screen, data=self._base_payload(current_benefits=["snap", "tanf"]))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(self._benefit_names(), {"snap", "tanf"})

    def test_update_without_current_benefits_falls_back_to_has_columns(self):
        """A PATCH with no current_benefits key mirrors from has_* (old frontend)."""
        serializer = ScreenSerializer(self.screen, data=self._base_payload(has_snap=True))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(self._benefit_names(), {"snap"})

    def test_update_current_benefits_takes_precedence_over_has_columns(self):
        """When both are sent, the explicit current_benefits list is authoritative."""
        serializer = ScreenSerializer(
            self.screen,
            data=self._base_payload(current_benefits=["tanf"], has_snap=True),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(self._benefit_names(), {"tanf"})

    def test_current_benefits_is_write_only(self):
        """current_benefits is a write-only field — it is not echoed in serialized output."""
        self.assertNotIn("current_benefits", ScreenSerializer(self.screen).data)
