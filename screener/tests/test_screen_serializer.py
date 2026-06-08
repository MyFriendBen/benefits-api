"""
Tests for the ScreenSerializer current-benefits write path.

The frontend sends `current_benefits: ["snap", "tanf"]` (a list of
name_abbreviated, a required field), written to the CurrentBenefit join table via
a white-label-scoped Program lookup. These cover `_write_current_benefits()` (the
shared helper) directly and the serializer `create()` / `update()` paths end to end.
"""

from django.test import TestCase

from screener.models import CurrentBenefit, HouseholdMember, IncomeStream, Screen, WhiteLabel
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

    def test_new_path_injects_ssi_from_income_without_tile(self):
        """sSI income implies SSI even when the user didn't tick the SSI tile."""
        seed_program(self.white_label, "ssi")
        head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=40, has_income=True
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="sSI", amount=500, frequency="monthly"
        )

        # Frontend sends SNAP only — no SSI tile — but sSI income is present.
        _write_current_benefits(self.screen, ["snap"])

        self.assertEqual(self._benefit_names(self.screen), {"snap", "ssi"})

    def test_new_path_income_wins_over_explicit_deselect(self):
        """An explicit deselect can't remove SSI when sSI income is present (OR semantics)."""
        seed_program(self.white_label, "ssi")
        head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=40, has_income=True
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="sSI", amount=500, frequency="monthly"
        )

        # Deselect-all: empty list, yet income still forces SSI on.
        _write_current_benefits(self.screen, [])

        self.assertEqual(self._benefit_names(self.screen), {"ssi"})

    def test_new_path_no_ssi_without_income_or_tile(self):
        """No SSI tile and no sSI income → SSI is not written."""
        seed_program(self.white_label, "ssi")

        _write_current_benefits(self.screen, ["snap"])

        self.assertEqual(self._benefit_names(self.screen), {"snap"})

    def test_new_path_derived_ssi_variant_not_in_other_wl(self):
        """Derived SSI variants for other WLs (e.g. wa_ssi) aren't written to this WL."""
        seed_program(self.white_label, "ssi")  # this WL only offers "ssi"
        head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=40, has_income=True
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="sSI", amount=500, frequency="monthly"
        )

        _write_current_benefits(self.screen, [])

        # Only the variant this WL offers is written; tx_ssi / wa_ssi / cesn_ssi are dropped.
        self.assertEqual(self._benefit_names(self.screen), {"ssi"})


class ScreenSerializerUpdateTests(TestCase):
    """End-to-end coverage of `current_benefits` flowing through serializer.update()."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=False
        )
        seed_program(self.white_label, "snap", "tanf")

    def _base_payload(self, **extra):
        # current_benefits is required; default to an empty list so each test
        # can override it explicitly.
        payload = {
            "white_label": self.white_label.code,
            "household_members": [],
            "expenses": [],
            "current_benefits": [],
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

    def test_update_empty_current_benefits_clears_join_table(self):
        """A PATCH with an empty current_benefits list clears the join table."""
        _write_current_benefits(self.screen, ["snap"])

        serializer = ScreenSerializer(self.screen, data=self._base_payload(current_benefits=[]))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(self._benefit_names(), set())

    def test_update_without_current_benefits_is_invalid(self):
        """current_benefits is required: a payload omitting it fails validation."""
        payload = self._base_payload()
        del payload["current_benefits"]

        serializer = ScreenSerializer(self.screen, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("current_benefits", serializer.errors)

    def test_update_does_not_accept_has_columns(self):
        """current_benefits is authoritative; a stray has_snap in the payload is
        ignored (not a serializer field)."""
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


class ScreenSerializerCreateTests(TestCase):
    """End-to-end coverage of `current_benefits` flowing through serializer.create().

    create() pops and writes current_benefits independently of update(), so it
    needs its own coverage — a regression in one wouldn't be caught by the other.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        seed_program(self.white_label, "snap", "tanf")

    def _base_payload(self, **extra):
        # current_benefits is required; default to an empty list so each test
        # can override it explicitly.
        payload = {
            "white_label": self.white_label.code,
            "household_members": [],
            "expenses": [],
            "current_benefits": [],
        }
        payload.update(extra)
        return payload

    def _benefit_names(self, screen):
        return set(CurrentBenefit.objects.filter(screen=screen).values_list("program__name_abbreviated", flat=True))

    def test_create_with_current_benefits_writes_join_table(self):
        """A POST carrying current_benefits writes the join table directly."""
        serializer = ScreenSerializer(data=self._base_payload(current_benefits=["snap", "tanf"]))
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        self.assertEqual(self._benefit_names(screen), {"snap", "tanf"})

    def test_create_without_current_benefits_is_invalid(self):
        """current_benefits is required on create: omitting it fails validation."""
        payload = self._base_payload()
        del payload["current_benefits"]

        serializer = ScreenSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("current_benefits", serializer.errors)

    def test_create_empty_current_benefits_writes_no_rows(self):
        """A POST with an empty current_benefits list creates a screen with no rows."""
        serializer = ScreenSerializer(data=self._base_payload(current_benefits=[]))
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        self.assertEqual(self._benefit_names(screen), set())
