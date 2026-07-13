"""
Tests for the ScreenSerializer current-benefits write path.

The frontend sends `current_benefits: ["snap", "tanf"]` (a list of
name_abbreviated, a required field), written to the CurrentBenefit join table via
a white-label-scoped Program lookup. These cover `_write_current_benefits()` (the
shared helper) directly and the serializer `create()` / `update()` paths end to end.
"""

from django.test import TestCase

from programs.models import Program
from screener.models import CurrentBenefit, HouseholdMember, IncomeStream, Insurance, Screen, WhiteLabel
from screener.serializers import ScreenSerializer, _write_current_benefits
from screener.tests.helpers import seed_program

# The Program.name_abbreviated column max_length. The serializer caps on a
# current-benefit name must match this so no DB-valid name is rejected before the
# white-label-scoped resolve. Read from the model so the tests track the column.
NAME_ABBREVIATED_MAX_LENGTH = 120


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

    def test_update_without_current_benefits_clears_join_table(self):
        """current_benefits is optional; an absent key is treated as empty, so a
        payload omitting it clears the join table (non-frontend clients don't 400)."""
        _write_current_benefits(self.screen, ["snap"])
        payload = self._base_payload()
        del payload["current_benefits"]

        serializer = ScreenSerializer(self.screen, data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(self._benefit_names(), set())

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

    def test_read_returns_join_table_names(self):
        """The serialized output echoes current_benefits as the sorted join-table names."""
        _write_current_benefits(self.screen, ["tanf", "snap"])

        data = ScreenSerializer(self.screen).data

        self.assertEqual(data["current_benefits"], ["snap", "tanf"])

    def test_read_empty_when_no_current_benefits(self):
        """A screen with no current benefits serializes current_benefits as []."""
        self.assertEqual(ScreenSerializer(self.screen).data["current_benefits"], [])

    def test_update_response_reflects_new_set_with_prefetched_instance(self):
        """Regression: updating current_benefits returns the NEW set in the response
        even when the instance was loaded with current_benefits__program prefetched
        (as the viewset loads it). Without cache invalidation after the write, the
        stale prefetch cache would echo the pre-write set."""
        _write_current_benefits(self.screen, ["snap"])

        # Load via the same prefetch the viewset uses — this is what makes the
        # relation cache stale after the write.
        instance = Screen.objects.prefetch_related("current_benefits__program").get(pk=self.screen.pk)

        serializer = ScreenSerializer(instance, data=self._base_payload(current_benefits=["tanf"]))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(serializer.data["current_benefits"], ["tanf"])


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

    def test_create_response_echoes_current_benefits(self):
        """The create response reflects the written current_benefits (sorted names)."""
        serializer = ScreenSerializer(data=self._base_payload(current_benefits=["tanf", "snap"]))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(serializer.data["current_benefits"], ["snap", "tanf"])

    def test_create_without_current_benefits_writes_no_rows(self):
        """current_benefits is optional; an absent key is treated as empty, so a
        screen created without it has no current-benefit rows (non-frontend clients
        like validation imports / screen-pull commands don't 400)."""
        payload = self._base_payload()
        del payload["current_benefits"]

        serializer = ScreenSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        self.assertEqual(self._benefit_names(screen), set())

    def test_create_empty_current_benefits_writes_no_rows(self):
        """A POST with an empty current_benefits list creates a screen with no rows."""
        serializer = ScreenSerializer(data=self._base_payload(current_benefits=[]))
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        self.assertEqual(self._benefit_names(screen), set())


class HouseholdMemberInsuranceTests(TestCase):
    """Regression coverage for the optional `insurance` field on household members.

    `insurance` is `required=False` on HouseholdMemberSerializer, so a client can omit
    the key entirely (distinct from sending `null`): on omission the key is absent from
    validated_data, on null it's present as None. A bare `member.pop("insurance")`
    KeyErrors on the omission case (a prod 500). create()/update() must treat an absent
    key the same as null — these pin both paths against that regression.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def _base_payload(self, members):
        return {
            "white_label": self.white_label.code,
            "household_members": members,
            "expenses": [],
            "current_benefits": [],
        }

    def _member(self, **extra):
        # income_streams is the only required nested field on a member; everything
        # else (including insurance) is optional. Tests override via **extra.
        member = {"relationship": "headOfHousehold", "age": 40, "income_streams": []}
        member.update(extra)
        return member

    def test_create_member_omitting_insurance_key_succeeds(self):
        """A member with no `insurance` key at all creates without error and writes no
        Insurance row (the prod KeyError regression)."""
        member = self._member()
        self.assertNotIn("insurance", member)

        serializer = ScreenSerializer(data=self._base_payload([member]))
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        hhm = HouseholdMember.objects.get(screen=screen)
        self.assertFalse(Insurance.objects.filter(household_member=hhm).exists())

    def test_create_member_with_null_insurance_succeeds(self):
        """An explicit `insurance: None` also creates no Insurance row."""
        serializer = ScreenSerializer(data=self._base_payload([self._member(insurance=None)]))
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        hhm = HouseholdMember.objects.get(screen=screen)
        self.assertFalse(Insurance.objects.filter(household_member=hhm).exists())

    def test_create_member_with_insurance_writes_row(self):
        """A provided insurance object is written with its flags."""
        serializer = ScreenSerializer(
            data=self._base_payload([self._member(insurance={"none": False, "medicaid": True, "medicare": True})])
        )
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        hhm = HouseholdMember.objects.get(screen=screen)
        row = Insurance.objects.get(household_member=hhm)
        self.assertTrue(row.medicaid)
        self.assertTrue(row.medicare)
        self.assertFalse(row.none)

    def test_update_member_omitting_insurance_key_succeeds(self):
        """update() already defaults the absent key; lock it so it can't regress to a
        bare pop (KeyError) like create() had."""
        screen = Screen.objects.create(white_label=self.white_label, zipcode="78701", household_size=1, completed=False)
        member = self._member()
        self.assertNotIn("insurance", member)

        serializer = ScreenSerializer(screen, data=self._base_payload([member]))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        hhm = HouseholdMember.objects.get(screen=screen)
        self.assertFalse(Insurance.objects.filter(household_member=hhm).exists())


class CurrentBenefitsNameLengthTests(TestCase):
    """The per-element cap on `current_benefits` must match the
    Program.name_abbreviated column so a DB-valid name is never rejected before the
    write path (which silently drops unknown names). Guards against the serializer
    cap and the column drifting apart."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def _payload(self, names):
        return {
            "white_label": self.white_label.code,
            "household_members": [],
            "expenses": [],
            "current_benefits": names,
        }

    def test_child_cap_matches_db_column(self):
        """The ListField child's max_length equals the Program.name_abbreviated column."""
        child = ScreenSerializer().fields["current_benefits"].child
        self.assertEqual(child.max_length, NAME_ABBREVIATED_MAX_LENGTH)

    def test_name_at_column_max_passes_validation(self):
        """A name as long as the column is accepted by validation (dropped later only
        if no Program matches — not rejected for length)."""
        serializer = ScreenSerializer(data=self._payload(["a" * NAME_ABBREVIATED_MAX_LENGTH]))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_name_over_column_max_is_rejected(self):
        """A name longer than the column is rejected by validation."""
        serializer = ScreenSerializer(data=self._payload(["a" * (NAME_ABBREVIATED_MAX_LENGTH + 1)]))
        self.assertFalse(serializer.is_valid())
        self.assertIn("current_benefits", serializer.errors)
