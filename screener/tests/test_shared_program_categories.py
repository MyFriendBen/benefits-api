"""
Tests for shared ProgramCategory rows (white_label = None).

A shared category is used by programs in every white label, so the guarantees
worth pinning down are that it stays reachable from each white label and that
it never leaks one white label's programs into another's response.
"""

from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from programs.models import CategoryIconName, Program, ProgramCategory
from programs.serializers import ProgramCategorySerializer
from screener.models import WhiteLabel
from translations.models import Translation

# Translation FKs on Program with null=False, so they must be supplied even when
# irrelevant to the test. Mirrors test_has_benefits_programs.py.
PROGRAM_REQUIRED_TRANSLATION_FIELDS = (
    "description_short",
    "description",
    "learn_more_link",
    "apply_button_link",
    "apply_button_description",
    "estimated_delivery_time",
    "estimated_application_time",
    "estimated_value",
    "name",
    "website_description",
)


def make_translation(label: str, default_message: str = "") -> Translation:
    return Translation.objects.add_translation(label, default_message=default_message)


def make_program(*, label_prefix: str, **overrides) -> Program:
    defaults = {
        field: make_translation(f"program.{label_prefix}-{field}") for field in PROGRAM_REQUIRED_TRANSLATION_FIELDS
    }
    defaults["external_name"] = label_prefix
    defaults.update(overrides)
    return Program.objects.create(**defaults)


class _FakeMember:
    """Stands in for a HouseholdMember; cap calculators only read frontend_id."""

    def __init__(self, frontend_id: str):
        self.frontend_id = frontend_id


class _FakeMemberEligibility:
    def __init__(self, member: _FakeMember, value: int):
        self.member = member
        self.value = value
        self.eligible = True


class _FakeEligibility:
    def __init__(self, value: int, eligible_members: list):
        self.value = value
        self.eligible_members = eligible_members
        self.eligible = True


def make_category(external_name: str, white_label=None, icon: str = None) -> ProgramCategory:
    icon_instance = CategoryIconName.objects.get_or_create(name=icon)[0] if icon else None
    return ProgramCategory.objects.create(
        white_label=white_label,
        external_name=external_name,
        icon=icon_instance,
        name=make_translation(f"program_category.{external_name}-name", "Cash Assistance"),
        description=make_translation(f"program_category.{external_name}-description"),
    )


class TestSharedCategoryModel(TestCase):
    def setUp(self):
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def test_category_can_have_no_white_label(self):
        category = make_category("cash")

        self.assertIsNone(category.white_label)

    def test_programs_in_different_white_labels_share_one_category(self):
        """The core requirement: a CO program and an MO program on the same row."""
        category = make_category("child_care")

        co_program = make_program(label_prefix="co_head_start", white_label=self.co, category=category)
        mo_program = make_program(label_prefix="mo_head_start", white_label=self.mo, category=category)

        self.assertEqual(co_program.category_id, mo_program.category_id)
        self.assertEqual(category.programs.count(), 2)

    def test_new_program_category_creates_a_shared_row(self):
        category = ProgramCategory.objects.new_program_category(
            white_label=None, external_name="savings", icon="savings"
        )

        self.assertIsNone(category.white_label)
        self.assertEqual(category.external_name, "savings")

    def test_new_program_category_still_scopes_when_given_a_white_label(self):
        category = ProgramCategory.objects.new_program_category(white_label="co", external_name="co_only", icon="cash")

        self.assertEqual(category.white_label, self.co)


class TestSharedCategorySerialization(TestCase):
    """
    A shared category holds every white label's programs, so the serializer has
    to narrow them to the requested white label. Without that, one state's
    results would list another state's programs.
    """

    def setUp(self):
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        self.category = make_category("cash", icon="cash")

        self.co_program = make_program(
            label_prefix="co_tanf",
            white_label=self.co,
            name_abbreviated="co_tanf",
            active=True,
            show_on_current_benefits=True,
            category=self.category,
        )
        self.mo_program = make_program(
            label_prefix="mo_tanf",
            white_label=self.mo,
            name_abbreviated="mo_tanf",
            active=True,
            show_on_current_benefits=True,
            category=self.category,
        )

    def _program_ids(self, white_label_code):
        data = ProgramCategorySerializer(self.category, context={"white_label": white_label_code}).data
        return {program["id"] for program in data["programs"]}

    def test_only_the_requested_white_labels_programs_are_returned(self):
        self.assertEqual(self._program_ids("co"), {self.co_program.id})
        self.assertEqual(self._program_ids("mo"), {self.mo_program.id})

    def test_without_a_white_label_in_context_all_programs_are_returned(self):
        """No context means no narrowing — used where the caller has already scoped."""
        data = ProgramCategorySerializer(self.category).data

        self.assertEqual({p["id"] for p in data["programs"]}, {self.co_program.id, self.mo_program.id})

    def test_inactive_programs_are_still_excluded(self):
        self.co_program.active = False
        self.co_program.save()

        self.assertEqual(self._program_ids("co"), set())


class TestSharedCategoryEndpoint(APITestCase):
    """GET /api/program_categories/{white_label}/"""

    def setUp(self):
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        self.shared = make_category("cash", icon="cash")

        self.programs = {
            code: make_program(
                label_prefix=code,
                white_label=wl,
                name_abbreviated=code,
                active=True,
                show_on_current_benefits=True,
                category=self.shared,
            )
            for code, wl in (("co_tanf", self.co), ("mo_tanf", self.mo))
        }

        self.user = User.objects.create_user(email_or_cell="cat@example.com", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_shared_category_is_returned_for_each_white_label(self):
        """It would be filtered out entirely if the view still scoped on the category's own white label."""
        for code in ("co", "mo"):
            response = self.client.get(f"/api/program_categories/{code}/")

            self.assertEqual(response.status_code, 200)
            self.assertEqual([c["name"]["default_message"] for c in response.data], ["Cash Assistance"])

    def test_a_white_label_sees_only_its_own_programs(self):
        response = self.client.get("/api/program_categories/co/")

        program_ids = [p["id"] for category in response.data for p in category["programs"]]
        self.assertEqual(program_ids, [self.programs["co_tanf"].id])


class TestSharedCategoryCapCalculators(TestCase):
    """
    child_care and health_care become shared rows while still carrying CO's cap
    calculators, which CO's active programs depend on. The caps are defined by
    program name, so they have to stay inert for other white labels.
    """

    def test_co_cap_calculators_are_a_noop_without_their_programs(self):
        from programs.categories import category_cap_calculators

        for name in ("co_preschool", "co_health_care"):
            calculator = category_cap_calculators[name]({})

            for cap in calculator.caps():
                self.assertEqual(cap.programs, [], f"{name} kept programs for a screen that has none")
                self.assertEqual(cap.household_cap, 0)
                self.assertEqual(cap.member_caps, {})

    def test_a_max_cap_survives_a_single_eligible_program(self):
        """
        calc_max_cap used to unpack the value list, so max(*[1200]) raised
        TypeError and took down the whole results request. One value is the
        common case: exactly one of the capped programs is present.
        """
        from programs.categories import category_cap_calculators

        member = _FakeMember("1")
        eligibility = {"cfhc": _FakeEligibility(1200, [_FakeMemberEligibility(member, 1200)])}

        caps = category_cap_calculators["co_health_care"](eligibility).caps()

        self.assertEqual([cap.member_caps for cap in caps], [{"1": 1200}])

    def test_a_max_cap_takes_the_highest_of_several_programs(self):
        from programs.categories import category_cap_calculators

        member = _FakeMember("1")
        eligibility = {
            "cfhc": _FakeEligibility(1200, [_FakeMemberEligibility(member, 1200)]),
            "awd_medicaid": _FakeEligibility(900, [_FakeMemberEligibility(member, 900)]),
        }

        caps = category_cap_calculators["co_health_care"](eligibility).caps()

        self.assertEqual([cap.member_caps for cap in caps], [{"1": 1200}])
