from collections.abc import Collection
from typing import ClassVar, Optional
from datetime import date, datetime, timedelta
from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.functional import cached_property
from decimal import Decimal
import uuid
from authentication.models import User
from django.utils.translation import gettext_lazy as _
from programs.util import Dependencies
from django.conf import settings
from .feature_flags import FeatureFlagConfig, WHITELABEL_FEATURE_FLAGS
from .irs_parameters import get_qualifying_relative_threshold

# Built once: settings.LANGUAGES is fixed for the life of the process.
SUPPORTED_LANGUAGE_CODES = frozenset(code for code, _ in settings.LANGUAGES)

# Income stream types that represent money earned from work. Everything else the
# screener collects (SSDI, SSI, pension, unemployment, child support, ...) is
# unearned. Read by calc_gross_income()'s "earned"/"unearned" selectors and by
# PolicyEngine dependencies that need to reason about work rather than total
# income (e.g. TotalHoursWorkedDependency approximating weekly hours). Keep this
# as the single definition so those two never drift apart.
EARNED_INCOME_TYPES: frozenset[str] = frozenset(("wages", "selfEmployment"))

# Relationship values that are eligible for the dependent relationship checks
# currently modeled in this method (qualifying-child proxy + qualifying-relative
# proxy). NOTE:
# - domesticPartner is intentionally excluded because it is treated as a
#   spouse-equivalent in relationship_map()/is_spouse(), and therefore returns
#   False early in is_dependent().
# - roommate / boyfriendOrGirlfriend are intentionally excluded for the
#   qualifying-relative path as a conservative proxy because we do not collect
#   the full IRS non-relative tests (all-year residency + >50% support).
DEPENDENT_ELIGIBLE_RELATIONSHIPS: frozenset[str] = frozenset(
    {
        "child",
        "fosterChild",
        "stepChild",
        "grandChild",
        "parent",
        "stepParent",
        "grandParent",
        "sisterOrBrother",
        "stepSisterOrBrother",
        "relatedOther",
    }
)


class WhiteLabel(models.Model):
    FEATURE_FLAGS: ClassVar[dict[str, FeatureFlagConfig]] = WHITELABEL_FEATURE_FLAGS

    name = models.CharField(max_length=120, blank=False, null=False)
    code = models.CharField(max_length=32, blank=False, null=False)
    state_code = models.CharField(max_length=8, blank=True, null=True)
    cms_method = models.CharField(max_length=32, blank=True, null=True)
    feature_flags = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    def _get_flag_value(self, key: str) -> bool:
        """Internal: Get flag value with default fallback. Assumes key is valid."""
        return (self.feature_flags or {}).get(key, self.FEATURE_FLAGS[key].default)

    def has_feature(self, key: str) -> bool:
        """Check if a feature flag is enabled for this WhiteLabel."""
        if key not in self.FEATURE_FLAGS:
            raise KeyError(f"Unknown feature flag: {key}")
        return self._get_flag_value(key)


# The screen is the top most container for all information collected in the
# app and is synonymous with a household model. In addition to general
# application fields like submission_date, it also contains non-individual
# household fields. Screen -> HouseholdMember -> IncomeStream & Expense & Insurance
class Screen(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    white_label = models.ForeignKey(
        WhiteLabel,
        related_name="screens",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )
    completed = models.BooleanField(null=False, blank=False)
    submission_date = models.DateTimeField(blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    referral_source = models.CharField(max_length=320, default=None, blank=True, null=True)
    path = models.CharField(max_length=60, default=None, blank=True, null=True)
    referrer_code = models.CharField(max_length=320, default=None, blank=True, null=True)
    agree_to_tos = models.BooleanField(blank=True, null=True)
    is_13_or_older = models.BooleanField(blank=True, null=True)
    zipcode = models.CharField(max_length=5, blank=True, null=True)
    county = models.CharField(max_length=120, default=None, blank=True, null=True)
    # Matches the screener and both tax-credit apps, which cap a household at 8. HUD's income
    # limit tables stop at 8 too, so a larger household has no limit to compare against.
    MAX_HOUSEHOLD_SIZE: ClassVar[int] = 8
    household_size = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(MAX_HOUSEHOLD_SIZE)]
    )
    last_tax_filing_year = models.CharField(max_length=120, default=None, blank=True, null=True)
    household_assets = models.DecimalField(decimal_places=2, max_digits=10, default=None, blank=True, null=True)
    housing_situation = models.CharField(max_length=30, blank=True, null=True, default=None)
    last_email_request_date = models.DateTimeField(blank=True, null=True)
    is_test = models.BooleanField(default=False, blank=True)
    is_test_data = models.BooleanField(blank=True, null=True)
    alternate_path = models.CharField(max_length=60, blank=True, null=True)
    is_verified = models.BooleanField(default=False, blank=True)
    user = models.ForeignKey(User, related_name="screens", on_delete=models.SET_NULL, blank=True, null=True)
    external_id = models.CharField(max_length=120, blank=True, null=True)
    request_language_code = models.CharField(max_length=12, blank=True, null=True)
    # current_benefits: reverse FK from CurrentBenefit (related_name="current_benefits") — lists the specific programs already enrolled in
    has_benefits = models.CharField(max_length=32, default="preferNotToAnswer", blank=True, null=True)
    needs_food = models.BooleanField(default=False, blank=True, null=True)
    needs_baby_supplies = models.BooleanField(default=False, blank=True, null=True)
    needs_housing_help = models.BooleanField(default=False, blank=True, null=True)
    needs_mental_health_help = models.BooleanField(default=False, blank=True, null=True)
    needs_child_dev_help = models.BooleanField(default=False, blank=True, null=True)
    needs_funeral_help = models.BooleanField(default=False, blank=True, null=True)
    needs_family_planning_help = models.BooleanField(default=False, blank=True, null=True)
    needs_job_resources = models.BooleanField(default=False, blank=True, null=True)
    needs_dental_care = models.BooleanField(default=False, blank=True, null=True)
    needs_legal_services = models.BooleanField(default=False, blank=True, null=True)
    needs_college_savings = models.BooleanField(default=False, blank=True, null=True)
    needs_veteran_services = models.BooleanField(default=False, blank=True, null=True)
    needs_disability_resources = models.BooleanField(default=False, blank=True, null=True)
    needs_aging_resources = models.BooleanField(default=False, blank=True, null=True)
    needs_homeless_services = models.BooleanField(default=False, blank=True, null=True)
    needs_free_low_cost_medical_care = models.BooleanField(default=False, blank=True, null=True)
    needs_transportation = models.BooleanField(default=False, blank=True, null=True)
    needs_medical_expenses_and_debt = models.BooleanField(default=False, blank=True, null=True)
    utm_id = models.CharField(max_length=64, blank=True, null=True)
    utm_source = models.CharField(max_length=64, blank=True, null=True)
    utm_medium = models.CharField(max_length=64, blank=True, null=True)
    utm_campaign = models.CharField(max_length=128, blank=True, null=True)
    utm_content = models.CharField(max_length=128, blank=True, null=True)
    utm_term = models.CharField(max_length=128, blank=True, null=True)

    def get_reference_date(self) -> date:
        """
        Get the reference date for age calculations: the current date.

        Memoized per instance. Nothing invalidates the cache: an instance lives for one
        request, and a reference date that shifts mid-request is a bug in its own right,
        since the whole point is to keep ages consistent (two calls either side of
        midnight would otherwise disagree).
        """
        cached = getattr(self, "_reference_date", None)
        if cached is not None:
            return cached

        self._reference_date = timezone.now().date()
        return self._reference_date

    def calc_gross_income(self, frequency, types, exclude=[]):
        household_members = self.household_members.all()
        gross_income = 0

        for household_member in household_members:
            gross_income += household_member.calc_gross_income(frequency, types, exclude)
        return float(gross_income)

    def calc_expenses(self, frequency, types):
        expenses = self.expenses.all()
        total_expense = 0

        for expense in expenses:
            if "all" in types or expense.type in types:
                if frequency == "monthly":
                    total_expense += expense.monthly()
                elif frequency == "yearly":
                    total_expense += expense.yearly()

        return float(total_expense)

    def has_expense(self, expense_types):
        """
        Returns True if one household member has one of the expenses in expense_types
        """
        for expense_type in expense_types:
            household_expense_types = self.expenses.all()
            for expense in household_expense_types:
                if expense_type == expense.type:
                    return True
        return False

    def expense_type_names(self) -> list[str]:
        """
        Get list of unique expense types for this screen.
        Returns empty list if no expenses exist.
        """
        # Deduplicated in Python: a DISTINCT query would also select Expense's default
        # ordering column (id) and stop deduplicating. This also reads a prefetched expenses.
        return list(dict.fromkeys(e.type for e in self.expenses.all() if e.type is not None))

    def num_children(self, age_min=0, age_max=18, include_pregnant=False, child_relationship=["all"]):
        children = 0

        household_members = self.household_members.all()
        for household_member in household_members:
            has_child_relationship = household_member.relationship in child_relationship or "all" in child_relationship
            age = household_member.calc_age()
            if age is not None and age_min <= age <= age_max and has_child_relationship:
                children += 1
            if household_member.pregnant and include_pregnant:
                children += 1

        return children

    def num_adults(self, age_max=19):
        adults = 0
        household_members = self.household_members.all()
        for household_member in household_members:
            age = household_member.calc_age()
            if age is not None and age >= age_max:
                adults += 1
        return adults

    def num_guardians(self):
        parents = 0
        child_relationship = ["child", "fosterChild"]
        guardian_relationship = ["parent", "fosterParent"]
        hoh_child_exists = False

        household_members = self.household_members.all()
        for household_member in household_members:
            if household_member.relationship in child_relationship:
                hoh_child_exists = True
            elif household_member.relationship == "headOfHousehold":
                if household_member.pregnant:
                    hoh_child_exists = True
            elif household_member.pregnant:
                parents += 1
            elif household_member.relationship in guardian_relationship:
                parents += 1

        for household_member in household_members:
            if hoh_child_exists and household_member.relationship == "spouse":
                parents += 1
            elif hoh_child_exists and household_member.relationship == "headOfHousehold":
                parents += 1

        return parents

    def is_joint(self):
        is_joint = False
        household_members = self.household_members.all()
        for household_member in household_members:
            if household_member.relationship == "spouse":
                is_joint = True
        return is_joint

    def calc_net_income(self, frequency, income_types, expense_types):
        net_income = None
        if frequency == "monthly":
            gross_income = self.calc_gross_income(frequency, income_types)
            expenses = self.calc_expenses(frequency, expense_types)
            net_income = gross_income - expenses

        return float(net_income)

    def relationship_map(self):
        relationship_map = {}

        all_members = self.household_members.all()
        for member in all_members:
            if member.id in relationship_map and relationship_map[member.id] is not None:
                continue

            relationship = member.relationship
            probable_spouse = None

            if relationship == "headOfHousehold":
                for other_member in all_members:
                    if (
                        other_member.relationship in ("spouse", "domesticPartner")
                        and other_member.id not in relationship_map
                    ):
                        probable_spouse = other_member.id
                        break
            elif relationship in ("spouse", "domesticPartner"):
                for other_member in all_members:
                    if other_member.relationship == "headOfHousehold" and other_member.id not in relationship_map:
                        probable_spouse = other_member.id
                        break
            elif relationship in (
                "parent",
                "fosterParent",
                "stepParent",
                "grandParent",
            ):
                for other_member in all_members:
                    if (
                        other_member.relationship == relationship
                        and other_member.id != member.id
                        and other_member.id not in relationship_map
                    ):
                        probable_spouse = other_member.id
                        break

            relationship_map[member.id] = probable_spouse
            if probable_spouse is not None:
                relationship_map[probable_spouse] = member.id

        return relationship_map

    def other_tax_unit_structure(self):
        other_tax_unit: list[HouseholdMember] = []
        for member in self.household_members.all():
            if not member.is_in_tax_unit():
                other_tax_unit.append(member)

        unit = {"head": None, "spouse": None, "dependents": []}
        if len(other_tax_unit) == 0:
            return unit

        for member in other_tax_unit:
            if unit["head"] is None or (member.calc_age() or 0) > (unit["head"].calc_age() or 0):
                unit["head"] = member

        spouse_id = self.relationship_map()[unit["head"].id]

        for member in other_tax_unit:
            if member.id == unit["head"].id:
                continue

            if member.id == spouse_id:
                unit["spouse"] = member
            else:
                unit["dependents"].append(member)

        return unit

    def has_insurance_types(self, types, strict=True) -> bool:
        return any(member.has_insurance_types(types, strict) for member in self.household_members.all())

    # Keys in Insurance.insurance_map() that describe a coverage *source* rather than a
    # MyFriendBen program, so they never correspond to a Program row.
    NON_PROGRAM_INSURANCE_KEYS = frozenset({"dont_know", "none", "employer", "private"})

    def held_insurance_keys(self) -> set[str]:
        """The `insurance_map()` keys any household member reports holding.

        The member-level counterpart to `_current_benefit_names`. Enrollment lives in two
        systems: `CurrentBenefit` (household-level, see `has_benefit`) and `Insurance`
        (member-level), and medicaid / CHP / medicare / VA / emergency medicaid / family
        planning only ever appear in the latter — deliberately, see
        `serializers._derived_current_benefit_names`.

        Derived from `insurance_map()`'s own keys so adding a variant there is picked up
        automatically. Computed once per call rather than per program: callers used to
        re-walk every member and rebuild the 16-key map for each program they tested.
        """
        candidates = set(Insurance.insurance_map(Insurance()).keys()) - self.NON_PROGRAM_INSURANCE_KEYS
        return {key for key in candidates if self.has_insurance_types((key,), strict=False)}

    def has_benefit_from_list(self, names: list[str]):
        """True if the household receives any of `names`. Each entry may be an exact
        `name_abbreviated` or a `base_program` group — see has_benefit_or_variant()."""
        for program in names:
            if self.has_benefit_or_variant(program):
                return True

        return False

    @cached_property
    def _current_benefit_names(self) -> set[str]:
        # Serves from the prefetch cache when `current_benefits__program` is
        # prefetched (zero queries); otherwise one query on first access, cached
        # thereafter — so repeated has_benefit() checks across a calculator run are
        # cheap.
        #
        # Per-instance cache: a Screen loaded before a write won't reflect rows
        # written after, on the same instance. If you write current_benefits and
        # then read them back on the same Screen object, call
        # invalidate_current_benefits_cache() in between (the write path in
        # serializers.py does this). The eligibility hot path never writes mid-run,
        # so it needs no invalidation.
        return {cb.program.name_abbreviated for cb in self.current_benefits.all()}

    @cached_property
    def _current_benefit_base_programs(self) -> set[str]:
        # The `base_program` grouping of the household's current benefits — e.g. a
        # screen receiving wa_tanf / co_tanf / ma_tafdc all contribute "tanf". Backs
        # has_base_benefit(), letting callers ask "any variant of program X?" without
        # a hand-maintained name list that goes stale when a new state program is
        # added. Same prefetch / per-instance cache behavior (and staleness caveat)
        # as _current_benefit_names above; base_program is nullable, so drop None.
        return {cb.program.base_program for cb in self.current_benefits.all() if cb.program.base_program is not None}

    def invalidate_current_benefits_cache(self) -> None:
        """Drop the per-instance caches of this screen's current benefits so the
        next read reflects rows written after this instance was loaded.

        Clears all layers: the `_current_benefit_names` cached_property (backs
        has_benefit()), the `_current_benefit_base_programs` cached_property
        (backs has_base_benefit()), and the `current_benefits` relation prefetch
        cache (backs the serializer read). Call after writing the join table when
        the same instance will be read again in the request. Safe to call when
        none are populated."""
        self.__dict__.pop("_current_benefit_names", None)
        self.__dict__.pop("_current_benefit_base_programs", None)
        if hasattr(self, "_prefetched_objects_cache"):
            self._prefetched_objects_cache.pop("current_benefits", None)

    def has_benefit(self, name_abbreviated: str) -> bool:
        """
        Returns True if the user has declared they already receive the benefit
        identified by `name_abbreviated`. Drives the "already_has" flag on
        eligibility results so the frontend can filter the program out.

        Reads from the CurrentBenefit join table, written on every POST/PATCH by
        the serializer's `_write_current_benefits()`.

        Compound cases like SSI are resolved at write time by
        `_derived_current_benefit_names()`, so this read path needs no special-casing.
        """
        return name_abbreviated in self._current_benefit_names

    def has_base_benefit(self, base_program: str) -> bool:
        """
        Returns True if the household receives any current benefit whose
        `Program.base_program` matches — i.e. any white-label variant of that
        program. `has_base_benefit("tanf")` covers tanf / co_tanf / il_tanf /
        wa_tanf / ma_tafdc / … without enumerating the names.

        Prefer this over `has_benefit_from_list([...])` when the intent is "any
        variant of program X across white labels": it reads the structural
        `base_program` grouping, so a newly added state variant is included
        automatically as long as its `base_program` is set.
        """
        return base_program in self._current_benefit_base_programs

    def has_benefit_or_variant(self, name: str) -> bool:
        """True if `name` matches the household's current benefits either exactly
        (`name_abbreviated`) or structurally (`base_program`).

        For a single benefit prefer the precise method — `has_benefit("tx_snap")` for one
        state's program, `has_base_benefit("snap")` for any variant. This exists for the
        mixed lists: a `presumptive_eligibility` tuple naturally holds both kinds of name
        (the CO-only `andcs` next to the cross-state `snap`).
        """
        return self.has_benefit(name) or self.has_base_benefit(name)

    def set_screen_is_test(self):
        referral_source_tests = ["testorprospect", "test"]

        self.is_test_data = (
            self.is_test
            or (self.referral_source is not None and self.referral_source.lower() in referral_source_tests)
            or (self.referrer_code is not None and self.referrer_code.lower() in referral_source_tests)
        )
        self.save()

    def get_head(self):
        for member in self.household_members.all():
            if member.relationship == "headOfHousehold":
                return member

        raise Exception("No head of household")

    def get_language_code(self):
        language_code = settings.LANGUAGE_CODE

        if self.request_language_code:
            language_code = str(self.request_language_code).lower()

        return language_code

    def supported_language_code(self, requested: object = None) -> str:
        """A `settings.LANGUAGES` code for this screen, preferring `requested`.

        `requested` when it is a supported code, else the screen's own
        `request_language_code` when that is, else `settings.LANGUAGE_CODE`. Always
        lowercase. Unlike `get_language_code`, the screen's value is checked too: the
        serializer only enforces its `max_length`, and a stale frontend code (`zh`, now
        `zh-hans`) can be saved on it.
        """
        for candidate in (requested, self.request_language_code):
            code = str(candidate or "").lower()
            if code in SUPPORTED_LANGUAGE_CODES:
                return code

        return settings.LANGUAGE_CODE

    def has_members_outside_of_tax_unit(self):
        for member in self.household_members.all():
            if not member.is_in_tax_unit():
                return True

        return False

    def missing_fields(self):
        screen_fields = (
            "zipcode",
            "county",
            "household_size",
            "household_assets",
            "energy_calculator",
        )

        missing_fields = Dependencies()

        for field in screen_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                missing_fields.add(field)

        for member in self.household_members.all():
            missing_fields.update(member.missing_fields())

        for expence in self.expenses.all():
            missing_fields.update(expence.missing_fields())

        return missing_fields


class CurrentBenefit(models.Model):
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name="current_benefits")
    program = models.ForeignKey("programs.Program", on_delete=models.CASCADE)

    class Meta:
        db_table = "screener_current_benefits"
        unique_together = ("screen", "program")


# Log table for any messages sent by the application via text or email
class Message(models.Model):
    sent = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=30)
    screen = models.ForeignKey(Screen, related_name="messages", on_delete=models.CASCADE)
    content = models.CharField(max_length=320, blank=True, null=True)
    uid = models.IntegerField(blank=True, null=True)


# Table of fields specific to individual household members. Parent model is the
# Screen
class HouseholdMember(models.Model):
    screen = models.ForeignKey(Screen, related_name="household_members", on_delete=models.CASCADE)
    frontend_id = models.UUIDField(default=uuid.uuid4)
    relationship = models.CharField(max_length=30, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    birth_year_month = models.DateField(blank=True, null=True)
    student = models.BooleanField(blank=True, null=True)
    student_full_time = models.BooleanField(blank=True, null=True)
    student_job_training_program = models.BooleanField(blank=True, null=True)
    student_has_work_study = models.BooleanField(blank=True, null=True)
    student_works_20_plus_hrs = models.BooleanField(blank=True, null=True)
    pregnant = models.BooleanField(blank=True, null=True)
    unemployed = models.BooleanField(blank=True, null=True)
    worked_in_last_18_mos = models.BooleanField(blank=True, null=True)
    visually_impaired = models.BooleanField(blank=True, null=True)
    disabled = models.BooleanField(blank=True, null=True)
    long_term_disability = models.BooleanField(blank=True, null=True)
    # "Ever in foster care, even briefly" - a history fact, not a current status. Named to
    # match PolicyEngine's `was_in_foster_care` input, which pairs it with `age` to derive
    # the several former-foster-youth age windows (Medicaid to 26, SNAP ABAWD, CO EITC).
    was_in_foster_care = models.BooleanField(blank=True, null=True)
    veteran = models.BooleanField(blank=True, null=True)
    medicaid = models.BooleanField(blank=True, null=True)
    disability_medicaid = models.BooleanField(blank=True, null=True)
    has_income = models.BooleanField(blank=True, null=True)
    has_expenses = models.BooleanField(blank=True, null=True)
    is_care_worker = models.BooleanField(blank=True, null=True)

    class Meta:
        # Deterministic iteration everywhere, including prefetches. The PolicyEngine payload
        # lists members in iteration order and the cassette matcher compares request bodies
        # exactly, so an unordered query can make the same household stop matching.
        ordering = ["id"]

    def calc_gross_income(self, frequency: str, types: Collection[str], exclude: Collection[str] = ()) -> float:
        gross_income = 0

        income_streams = self.income_streams.all()
        for income_stream in income_streams:
            if income_stream.type in exclude:
                continue

            include_all = "all" in types
            specific_match = income_stream.type in types
            earned_income_match = "earned" in types and income_stream.type in EARNED_INCOME_TYPES
            # A blank type is unknown, not unearned; `missing_fields()` reports it.
            unearned_income_match = (
                "unearned" in types
                and bool(income_stream.type and str(income_stream.type).strip())
                and income_stream.type not in EARNED_INCOME_TYPES
            )
            if include_all or earned_income_match or unearned_income_match or specific_match:
                if frequency == "monthly":
                    gross_income += income_stream.monthly()
                elif frequency == "yearly":
                    gross_income += income_stream.yearly()
        return float(gross_income)

    def calc_expenses(self, frequency, types):
        total_expense = 0

        expenses = self.expenses.all()
        for expense in expenses:
            if "all" in types or expense.type in types:
                if frequency == "monthly":
                    total_expense += expense.monthly()
                elif frequency == "yearly":
                    total_expense += expense.yearly()
        return float(total_expense)

    def calc_net_income(self, frequency, income_types, expense_types):
        net_income = None
        if frequency == "monthly":
            gross_income = self.calc_gross_income(frequency, income_types)
            expenses = self.calc_expenses(frequency, expense_types)
            net_income = gross_income - expenses

        return float(net_income)

    def is_married(self):
        all_household_members = self.screen.household_members.all()
        if self.relationship in ("spouse", "domesticPartner"):
            return {"is_married": True, "married_to": self.screen.get_head()}
        if self.relationship == "headOfHousehold":
            for member in all_household_members:
                if member.relationship in ("spouse", "domesticPartner"):
                    return {"is_married": True, "married_to": member}
        return {"is_married": False}

    def has_disability(self):
        return self.disabled or self.visually_impaired or self.long_term_disability

    def is_head(self) -> bool:
        return self.relationship == "headOfHousehold"

    def is_spouse(self) -> bool:
        return self.screen.relationship_map()[self.screen.get_head().id] == self.id

    def is_dependent(self, tax_year: Optional[int] = None) -> bool:
        """
        Whether the member is a dependent in the head's tax unit. With ``tax_year``, judged as
        of December 31 of that year: age from ``age_at_end_of_year``, that year's qualifying-
        relative limit, and no one born after it. Without it, judged on the screening date.
        """
        if tax_year is not None and self.born_after(tax_year):
            return False

        is_tax_unit_spouse = self.is_spouse()
        is_tax_unit_head = self.is_head()
        if is_tax_unit_head or is_tax_unit_spouse:
            return False

        has_eligible_relationship = self.relationship in DEPENDENT_ELIGIBLE_RELATIONSHIPS
        age = self.calc_age() if tax_year is None else self.age_at_end_of_year(tax_year)

        # Path 1: Qualifying Child (income test removed per IRS rules)
        is_qualifying_child = has_eligible_relationship and (
            (age is not None and (age <= 18 or (self.student and age <= 23))) or self.has_disability()
        )

        # Path 2: Qualifying Relative (unchanged)
        threshold_year = self.screen.get_reference_date().year if tax_year is None else tax_year
        threshold = get_qualifying_relative_threshold(threshold_year)
        is_qualifying_relative = has_eligible_relationship and self.calc_gross_income("yearly", ["all"]) < threshold

        return is_qualifying_child or is_qualifying_relative

    def is_in_tax_unit(self):
        return self.is_head() or self.is_spouse() or self.is_dependent()

    def has_insurance(self, name_abbreviated: str) -> bool:
        return self.has_insurance_types((name_abbreviated,), strict=False)

    def has_insurance_types(self, types, strict=True) -> bool:
        if not hasattr(self, "insurance"):
            return False
        return self.insurance.has_insurance_types(types, strict)

    @property
    def birth_year(self) -> Optional[int]:
        if self.birth_year_month is None:
            return None

        return self.birth_year_month.year

    @property
    def birth_month(self) -> Optional[int]:
        if self.birth_year_month is None:
            return None

        return self.birth_year_month.month

    def calc_age(self) -> Optional[int]:
        if self.birth_year_month is None:
            return self.age

        reference_date = self.screen.get_reference_date()
        return self.age_from_date(self.birth_year_month, reference_date)

    def age_at_end_of_year(self, year: Optional[int]) -> Optional[int]:
        """
        Age on December 31 of ``year``, for rules judged over a tax or claim year
        rather than on the screening date. Falls back to ``calc_age()`` when the birth
        year or the year is unknown, and is None for someone born after ``year``, who had
        no age that year.
        """
        if self.birth_year is None or year is None:
            return self.calc_age()

        if self.born_after(year):
            return None

        return year - self.birth_year

    def born_after(self, year: int) -> bool:
        """Born after ``year``, so not in the household that year. False without a birth year."""
        return self.birth_year is not None and self.birth_year > year

    @staticmethod
    def age_from_date(birth_year_month: date, reference_date: Optional[date] = None) -> int:
        today = reference_date if reference_date else timezone.now()

        if today.month >= birth_year_month.month:
            return today.year - birth_year_month.year

        return today.year - birth_year_month.year - 1

    def fraction_age(self) -> Optional[float]:
        if self.birth_year_month is None:
            return float(self.age) if self.age is not None else None

        reference_date = self.screen.get_reference_date()

        current_year = reference_date.year + reference_date.month / 12
        birth_year = self.birth_year_month.year + self.birth_year_month.month / 12

        return current_year - birth_year

    def missing_fields(self):
        member_fields = (
            "relationship",
            "age",
            "student",
            "pregnant",
            "visually_impaired",
            "disabled",
            "long_term_disability",
            "insurance",
            "energy_calculator",
        )

        missing_fields = Dependencies()

        for field in member_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                missing_fields.add(field)

        for income in self.income_streams.all():
            missing_fields.update(income.missing_fields())

        return missing_fields


# HouseholdMember income streams
class IncomeStream(models.Model):
    screen = models.ForeignKey(Screen, related_name="income_streams", on_delete=models.CASCADE)
    household_member = models.ForeignKey(HouseholdMember, related_name="income_streams", on_delete=models.CASCADE)
    category = models.CharField(max_length=30, blank=True, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    frequency = models.CharField(max_length=30, blank=True, null=True)
    hours_worked = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def monthly(self):
        if self.frequency == "monthly":
            monthly = self.amount
        elif self.frequency == "weekly":
            monthly = self.amount * Decimal(4.35)
        elif self.frequency == "biweekly":
            monthly = self.amount * Decimal(2.175)
        elif self.frequency == "semimonthly":
            monthly = self.amount * 2
        elif self.frequency == "yearly":
            monthly = self.amount / 12
        elif self.frequency == "hourly":
            monthly = self._hour_to_month()

        return monthly

    def yearly(self):
        if self.frequency == "monthly":
            yearly = self.amount * 12
        elif self.frequency == "weekly":
            yearly = self.amount * Decimal(52.1429)
        elif self.frequency == "biweekly":
            yearly = self.amount * Decimal(26.01745)
        elif self.frequency == "semimonthly":
            yearly = self.amount * 24
        elif self.frequency == "yearly":
            yearly = self.amount
        elif self.frequency == "hourly":
            yearly = self._hour_to_month() * 12

        return yearly

    def _hour_to_month(self):
        return self.amount * self.hours_worked * Decimal(4.35)

    # The frequencies monthly() and yearly() convert. Any other value, "" included, matches
    # no branch and raises UnboundLocalError mid-calculation, so it gates like a null.
    SUPPORTED_FREQUENCIES: ClassVar[frozenset[str]] = frozenset(
        {"monthly", "weekly", "biweekly", "semimonthly", "yearly", "hourly"}
    )

    def missing_fields(self) -> Dependencies:
        missing_fields = Dependencies()

        if self.type is None:
            missing_fields.add("income_type")
        elif not str(self.type).strip():
            # A blank type matches no earned type in calc_gross_income, so it falls through
            # to the unearned catch-all and is silently counted as unearned income.
            missing_fields.add("income_type")
            missing_fields.report_malformed("income_type", self.type, "blank; would count as unearned income")

        if self.amount is None:
            missing_fields.add("income_amount")

        if self.frequency is None:
            missing_fields.add("income_frequency")
        elif self.frequency not in self.SUPPORTED_FREQUENCIES:
            missing_fields.add("income_frequency")
            missing_fields.report_malformed("income_frequency", self.frequency, "monthly()/yearly() can't convert it")
        elif self.frequency == "hourly" and self.hours_worked is None:
            # _hour_to_month needs hours_worked. Gated as income_amount because that is the
            # token calculators declare when they read an amount; nothing declares hours.
            missing_fields.add("income_amount")
            missing_fields.report_malformed("income_hours_worked", None, "hourly income with no hours_worked")

        return missing_fields


# HouseholdMember expenses
class Expense(models.Model):
    screen = models.ForeignKey(Screen, related_name="expenses", on_delete=models.CASCADE)
    household_member = models.ForeignKey(HouseholdMember, related_name="expenses", on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    frequency = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ["id"]

    def monthly(self):
        if self.frequency == "monthly":
            monthly = self.amount
        elif self.frequency == "weekly":
            monthly = self.amount * Decimal(4.35)
        elif self.frequency == "biweekly":
            monthly = self.amount * Decimal(2.175)
        elif self.frequency == "semimonthly":
            monthly = self.amount * 2
        elif self.frequency == "yearly":
            monthly = self.amount / 12
        return monthly

    def yearly(self):
        if self.frequency == "monthly":
            yearly = self.amount * 12
        elif self.frequency == "weekly":
            yearly = self.amount * Decimal(52.1429)
        elif self.frequency == "biweekly":
            yearly = self.amount * Decimal(26.01745)
        elif self.frequency == "semimonthly":
            yearly = self.amount * 24
        elif self.frequency == "yearly":
            yearly = self.amount

        return yearly

    # IncomeStream.SUPPORTED_FREQUENCIES without "hourly": these monthly()/yearly() have no
    # hourly branch.
    SUPPORTED_FREQUENCIES: ClassVar[frozenset[str]] = frozenset(
        {"monthly", "weekly", "biweekly", "semimonthly", "yearly"}
    )

    def missing_fields(self) -> Dependencies:
        missing_fields = Dependencies()

        if self.type is None:
            missing_fields.add("expense_type")
        elif not str(self.type).strip():
            missing_fields.add("expense_type")
            missing_fields.report_malformed("expense_type", self.type, "blank; matches no expense type")

        if self.amount is None:
            missing_fields.add("expense_amount")

        if self.frequency is None:
            missing_fields.add("expense_frequency")
        elif self.frequency not in self.SUPPORTED_FREQUENCIES:
            missing_fields.add("expense_frequency")
            missing_fields.report_malformed("expense_frequency", self.frequency, "monthly()/yearly() can't convert it")

        return missing_fields


class Insurance(models.Model):
    household_member = models.OneToOneField(
        HouseholdMember, related_name="insurance", null=False, on_delete=models.CASCADE
    )
    dont_know = models.BooleanField(default=False)
    none = models.BooleanField(default=True)
    employer = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    chp = models.BooleanField(default=False)
    medicaid = models.BooleanField(default=False)  # low income health insurance
    medicare = models.BooleanField(default=False)  # elderly health insurance
    emergency_medicaid = models.BooleanField(default=False)
    family_planning = models.BooleanField(default=False)
    va = models.BooleanField(default=False)
    # NOTE: Massachusetts combines Medicaid and CHIP into one program called MassHealth
    mass_health = models.BooleanField(default=False)

    def has_insurance_types(self, types, strict=True) -> bool:
        if "none" in types:
            types = (*types, "dont_know")

        insurance = self.insurance_map()
        for hi_type in types:
            if hi_type not in insurance:
                if strict:
                    raise KeyError(f"{hi_type} not in insurance types")
                continue

            if insurance[hi_type]:
                return True

        return False

    def insurance_map(self):
        return {
            "dont_know": self.dont_know,
            "none": self.none,
            "employer": self.employer,
            "private": self.private,
            "chp": self.chp,
            "medicaid": self.medicaid,
            "nc_medicaid": self.medicaid,
            "co_medicaid": self.medicaid,
            "wa_apple_health_medicaid": self.medicaid,
            # Each state's CHIP program, so a child reporting CHIP coverage is marked as already
            # having it. Every CHIP calculator's code must be here; a test checks.
            "wa_apple_health_for_kids": self.chp,
            "ks_chip": self.chp,
            "tx_chip": self.chp,
            "il_all_kids": self.chp,
            "nj_chip": self.chp,
            "ma_mass_health": self.mass_health or self.medicaid,
            "medicare": self.medicare,
            "emergency_medicaid": self.emergency_medicaid,
            "family_planning": self.family_planning,
            "va": self.va,
        }


class EnergyCalculatorScreen(models.Model):
    screen = models.OneToOneField(Screen, related_name="energy_calculator", null=False, on_delete=models.CASCADE)
    is_home_owner = models.BooleanField(default=False, null=True, blank=True)
    is_renter = models.BooleanField(default=False, null=True, blank=True)
    electric_provider = models.CharField(max_length=200, null=True, blank=True)
    electric_provider_name = models.CharField(max_length=200, null=True, blank=True)  # The human readable version
    gas_provider = models.CharField(max_length=200, null=True, blank=True)
    gas_provider_name = models.CharField(max_length=200, null=True, blank=True)  # The human readable version
    electricity_is_disconnected = models.BooleanField(default=False, null=True, blank=True)
    has_past_due_energy_bills = models.BooleanField(default=False, null=True, blank=True)
    has_old_car = models.BooleanField(default=False, null=True, blank=True)
    needs_water_heater = models.BooleanField(default=False, null=True, blank=True)
    needs_hvac = models.BooleanField(default=False, null=True, blank=True)
    needs_stove = models.BooleanField(default=False, null=True, blank=True)
    needs_dryer = models.BooleanField(default=False, null=True, blank=True)

    def has_electricity_provider(self, providers: list[str]):
        for provider in providers:
            if provider == self.electric_provider:
                return True

        return False

    def has_gas_provider(self, providers: list[str]):
        for provider in providers:
            if provider == self.gas_provider:
                return True

        return False

    def has_utility_provider(self, providers: list[str]):
        return self.has_electricity_provider(providers) or self.has_gas_provider(providers)


class EnergyCalculatorMember(models.Model):
    household_member = models.OneToOneField(
        HouseholdMember,
        related_name="energy_calculator",
        null=False,
        on_delete=models.CASCADE,
    )
    surviving_spouse = models.BooleanField(default=False, null=True, blank=True)
    receives_ssi = models.BooleanField(default=False, null=True, blank=True)
    medical_equipment = models.BooleanField(default=False, null=True, blank=True)


# A point in time log table to capture the exact eligibility and value results
# for a completed screen. This table is currently used primarily for analytics
# but will eventually drive new benefit update notifications
class EligibilitySnapshot(models.Model):
    screen = models.ForeignKey(Screen, related_name="eligibility_snapshots", on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now=True)
    is_batch = models.BooleanField(default=False)
    had_error = models.BooleanField(default=False)

    #: Programs left out of this screen's results, as ``{name_abbreviated: reason}``.
    #:
    #: The results payload carries a single ``missing_programs`` boolean, which says that
    #: something was omitted but not what or why. The reasons are not interchangeable — a
    #: PolicyEngine outage, a screener field the household skipped, and a gated upstream
    #: whose row was deactivated all look identical from the response, and only the first
    #: is outside our control. Recording them per program is what makes the difference
    #: answerable from production data instead of by reading the calculator tree.
    #:
    #: Reasons are the ``DROPPED_*`` constants below. Code that knows this field always
    #: writes a dict — empty when nothing was dropped — so an empty dict and a null mean
    #: different things: "nothing was dropped" against "written by code that predates this
    #: field".
    #:
    #: Nullable for deploy safety, which is the only reason it is not simply NOT NULL.
    #: Django applies ``default`` in Python and drops the database default after adding the
    #: column, so a NOT NULL column is written only by code that declares the field. The
    #: release phase migrates before the new dynos take over, so for that window — and for
    #: the whole of any code rollback that leaves the migration applied — the old code
    #: inserts no value at all and every eligibility calculation fails on the constraint.
    dropped_programs = models.JSONField(default=dict, blank=True, null=True)

    #: The program's own `can_calc` failed: a screener field it needs is missing. Not a
    #: failure — the household was never asked.
    DROPPED_MISSING_FIELD = "missing_screener_field"

    #: A strict gate raised because the program it reads was not calculated.
    DROPPED_UPSTREAM_ABSENT = "gated_upstream_absent"

    #: A PolicyEngine program absent from the batch result: the call failed, the payload
    #: could not be assembled, the request was abandoned on the time budget, or the
    #: resolved model does not define its output.
    DROPPED_POLICY_ENGINE = "policy_engine_unavailable"

    #: A force-calculated upstream raised something other than `DependencyError`. Never a
    #: program the household would have seen; recorded because it means a gate that should
    #: have been decoupled fell back to dropping its dependents.
    DROPPED_UPSTREAM_ERROR = "force_calculated_upstream_error"

    #: An active row with no calculator registered under its name: the calculator was
    #: deleted from the code, or the row was imported ahead of it. Reported to Sentry.
    DROPPED_NO_CALCULATOR = "no_calculator"

    #: A displayed program's calculator raised something other than `DependencyError`: a
    #: bug, or screen data it could not handle. Reported to Sentry.
    DROPPED_CALCULATOR_ERROR = "calculator_error"


class NPSScore(models.Model):
    eligibility_snapshot = models.OneToOneField(EligibilitySnapshot, related_name="nps_score", on_delete=models.CASCADE)
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    score_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(score__gte=1) & models.Q(score__lte=10),
                name="nps_score_range",
            )
        ]
        indexes = [
            models.Index(fields=["-created_at"], name="nps_created_at_idx"),
        ]

    def __str__(self):
        return f"NPS {self.score} for snapshot {self.eligibility_snapshot_id}"


# Eligibility results for each specific program per screen. These are
# aggregated per screen using the EligibilitySnapshot id
class ProgramEligibilitySnapshot(models.Model):
    eligibility_snapshot = models.ForeignKey(
        EligibilitySnapshot, related_name="program_snapshots", on_delete=models.CASCADE
    )
    new = models.BooleanField(default=False)
    name = models.CharField(max_length=320)
    name_abbreviated = models.CharField(max_length=120)
    estimated_value = models.DecimalField(decimal_places=2, max_digits=10)
    estimated_delivery_time = models.CharField(max_length=120, blank=True, null=True)
    estimated_application_time = models.CharField(max_length=120, blank=True, null=True)
    eligible = models.BooleanField()
    failed_tests = models.JSONField(blank=True, null=True)
    passed_tests = models.JSONField(blank=True, null=True)


# --- Benbot (Benji) conversation state ---
#
# These two tables are the persistent home for Benji's conversation history. They
# are UNUSUAL in one important way: Django owns the *schema*, but Django is not the
# *writer*. mfb-ai-service connects to this same database and writes these rows
# itself through its `ConversationStore` interface (see the ai-service repo's
# `app/store_postgres.py`).
#
# Why they live here rather than in a database of ai-service's own: the whole
# analytics pipeline (data-queries/dbt -> Metabase) reads a single Postgres and
# joins across the `screener_*` tables. Postgres cannot join across databases, so a
# separate conversation store would have put every question worth asking about
# Benji — does using it correlate with completing an application, which programs get
# asked about versus which the household was eligible for, how that splits by white
# label — outside reach of the only tool that answers them.
#
# Consequences of the split ownership, all of which are load-bearing:
#
#   1. NO auto_now / auto_now_add on the timestamps. Those are ORM-level behaviors
#      and would silently do nothing on ai-service's inserts, leaving NULLs (or, for
#      updated_at, a value frozen at creation). Both columns are written explicitly
#      by whoever inserts the row; the defaults here only serve Django-side creation
#      in tests and the admin.
#   2. A column rename here breaks ai-service at runtime, not at deploy time. That's
#      why ai-service validates this schema at startup and refuses to boot if the
#      columns it expects aren't present — a loud failure on deploy instead of a
#      500 on someone's first message.
#   3. The constraints below are the real enforcement of invariants ai-service's API
#      only *documents*. Its SQLite store guards them with a process-local lock,
#      which stops working the moment there is more than one dyno.
#
# RETENTION: indefinite, by decision rather than by omission (2026-09-01, closing
# ADR-001 action item 6). Storage for conversation text is negligible, and the value
# of the history is not — following a household across a multi-week application is
# the entire premise of the assistant, and the longitudinal record is what shows
# whether it works. A time-based purge was built and then deliberately removed: an
# unscheduled one is worse than none, because it implies a coverage that does not
# exist. If an individual deletion request ever arrives, `AssistantMessage`'s foreign
# key cascades in the database (migration 0163), so deleting a screen's conversations
# is a one-statement job to add at that point.
#
# What that decision assumes: `messages.text` is unbounded free text typed by
# households, so it can contain anything they choose to disclose — more than the
# screener itself ever asks for. The controls on it are access controls, not expiry:
# the admin below is read-only and superuser-only, and LOG_PAYLOADS stays off in
# deployed environments.
#
# The schema deliberately mirrors ai-service's original SQLite schema field for
# field, so moving from that file to this table was a new implementation of the same
# interface rather than a data-model change.


class AssistantChannel(models.TextChoices):
    WEB = "web", "Web widget"
    SMS = "sms", "Text message"


class AssistantConversationStatus(models.TextChoices):
    """A conversation's lifecycle. Only `active` conversations take new turns.

    `closed` means superseded: a newer conversation replaced it, as when an SMS on-ramp
    from another screen takes over a phone's binding. `expired` means it ran out of
    time: an SMS conversation with no inbound text for 90 days. Neither is set by
    anything yet; the SMS work sets both (MFB-1916 proposal v2, decision 3). Web
    conversations never expire.

    Not enforced with a check constraint, unlike `channel`: this column predates the
    vocabulary, and production rows were not re-read to prove they all fit it.
    """

    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"
    EXPIRED = "expired", "Expired"


class AssistantConversation(models.Model):
    """One Benji conversation, plus the screen-context snapshot the model saw.

    `screen_uuid` is a plain indexed column and NOT a ForeignKey to Screen, because
    `Screen.uuid` carries no unique constraint (see the field on Screen — it has
    never had one), and a FK needs a unique target. Analytics joins it to
    `screener_screen.uuid` directly.

    Conversation history is retained indefinitely, deliberately — see the retention
    note in the block comment above.
    """

    # Generated by ai-service (uuid4) and returned to the browser, so it is supplied
    # on insert rather than defaulted here.
    conversation_id = models.UUIDField(primary_key=True)
    screen_uuid = models.UUIDField(db_index=True)
    # The WhiteLabel *code* ("co", "tx"), not a FK: ai-service receives it as a
    # string in the start payload and has no way to resolve a row id. Analytics joins
    # it to screener_whitelabel.code.
    white_label = models.CharField(max_length=32, blank=True, null=True)
    locale = models.CharField(max_length=12, blank=True, null=True)
    # "live" (model-generated replies) or "stub" (scripted). Kept per conversation
    # because it changes how the transcript should be read.
    mode = models.CharField(max_length=16, blank=True, null=True)
    prompt_version = models.CharField(max_length=64, blank=True, null=True)
    # Where the conversation happens (MFB-2432). A screen can hold one active
    # conversation per channel, so a texted conversation and the web widget's can
    # coexist on one screen as separate rows (MFB-1916 proposal v2, decision 3).
    #
    # Migration 0170 also keeps a DATABASE-level DEFAULT 'web' on this column, which
    # Django 4.2 cannot express in the model. It is what let benefits-api migrate
    # before ai-service knew the column existed: ai-service's inserts named no
    # channel, and a NOT NULL column without a database default would have rejected
    # every one of them.
    channel = models.CharField(max_length=8, choices=AssistantChannel.choices, default=AssistantChannel.WEB)
    status = models.CharField(
        max_length=16,
        choices=AssistantConversationStatus.choices,
        default=AssistantConversationStatus.ACTIVE,
    )
    # Snapshot of the household/program context the prompt was built from. PII: see
    # ADR-001 in the ai-service repo. jsonb, so analytics can index into it.
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            # `POST /v1/conversations` is documented as idempotent per screen, and
            # ai-service implements that as "find the active conversation, else
            # create one" — a read-then-write race. Two tabs, or a retried request,
            # could previously produce two active conversations for one screen and
            # split the history between them. Enforce it in the one place that can:
            # the database.
            #
            # Per channel since MFB-2432: one active web conversation and one active
            # SMS conversation on the same screen is the intended state, not a race.
            models.UniqueConstraint(
                fields=["screen_uuid", "channel"],
                condition=models.Q(status="active"),
                name="assistant_one_active_conv_per_screen_channel",
            ),
            # ai-service writes this column with raw SQL, so the choices above are no
            # guard at all on its inserts. This is.
            models.CheckConstraint(
                check=models.Q(channel__in=["web", "sms"]),
                name="assistant_conv_channel_valid",
            ),
        ]
        indexes = [
            # Last activity is how these are read: the admin lists newest-first, and
            # "which conversations are live right now" is the first analytics question.
            # created_at is not a substitute — a conversation opened months ago and
            # used yesterday sorts wrongly under it.
            models.Index(fields=["updated_at"], name="assistant_conv_updated_idx"),
        ]

    def __str__(self) -> str:
        return f"Benji conversation {self.conversation_id} (screen {self.screen_uuid})"


class AssistantMessage(models.Model):
    """One turn in a Benji conversation.

    Assistant rows carry the reply metadata (`model`, token counts, `latency_ms`,
    `error`) that makes cost and quality answerable per turn; user rows leave those
    NULL.
    """

    message_id = models.UUIDField(primary_key=True)
    conversation = models.ForeignKey(
        AssistantConversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    # Monotonic per conversation, assigned by the store on write. Ordering key for
    # the transcript — created_at is not safe for that, since a user message and its
    # reply are written in the same transaction and can share a timestamp.
    seq = models.IntegerField()
    role = models.CharField(max_length=16)  # 'user' | 'assistant'
    text = models.TextField()
    # Client-supplied idempotency key, so a retried send replays the stored exchange
    # instead of paying for a second completion.
    client_message_id = models.CharField(max_length=64, blank=True, null=True)
    suggested_actions = models.JSONField(default=list, blank=True)
    # --- assistant-reply metadata; NULL on user turns ---
    model = models.CharField(max_length=128, blank=True, null=True)
    prompt_tokens = models.IntegerField(blank=True, null=True)
    completion_tokens = models.IntegerField(blank=True, null=True)
    latency_ms = models.IntegerField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    # --- user feedback on the reply; NULL on user turns and on unrated replies ---
    # Deliberately +1/-1 rather than a boolean, because NULL has to stay available as
    # a third state: "nobody rated this" is the overwhelming majority of rows and is a
    # different fact from "rated badly". A nullable boolean would carry the same three
    # states, but the integer sums — AVG(rating) over a white label or a
    # prompt_version is the report query, and it needs no CASE.
    #
    # Clearing a rating writes NULL back, so a rated-then-cleared row is
    # indistinguishable from a never-rated one in this column alone. `rated_at` is what
    # separates them: it is set on every write INCLUDING the clear, and never reset. So
    # `rating IS NULL AND rated_at IS NULL` is "never touched", and `rating IS NULL AND
    # rated_at IS NOT NULL` is "rated, then withdrawn" — which is a real signal about
    # the reply and not the same as silence.
    RATING_UP = 1
    RATING_DOWN = -1
    RATING_CHOICES = ((RATING_UP, "Thumbs up"), (RATING_DOWN, "Thumbs down"))
    rating = models.SmallIntegerField(choices=RATING_CHOICES, blank=True, null=True)
    rated_at = models.DateTimeField(blank=True, null=True)
    # Why the reply was rated down. NULL means either "not rated down" or "rated down
    # and the household skipped the question", which is the common case — the chips are
    # offered after the thumbs-down is already saved, so declining them costs nothing.
    #
    # A bare thumbs-down says someone was unhappy and nothing about what to change. This
    # column is what makes the signal actionable, and the codes are drawn from the
    # failure modes `_SHARED_GUARDRAILS` in ai-service's prompts.py already names —
    # fabricated rules, programs outside the closed list, invented links — rather than
    # from a generic list.
    #
    # FIVE, not the seven this started with. Seven chips stacked to seven lines in a
    # panel capped at 45vh, which is a lot of furniture under every thumbs-down. The two
    # cut:
    #
    #   bad_link  — the only failure mode here we can detect WITHOUT asking anyone. The
    #               guardrails forbid inventing URLs and phone numbers, and a sweep over
    #               stored replies finds them directly, so spending a chip on it buys a
    #               signal we can already get.
    #   wrong_tone — real, and it matters for this population, but it is the least often
    #               articulated as a distinct complaint; it lands in `other`, whose rate
    #               is what will say if that was wrong.
    #
    # STORED CODE, NOT DISPLAYED TEXT. The frontend renders a translated label per code
    # (`chatbot.reason.*`), so the wording can be revised, or translated differently per
    # locale, without a migration and without splitting a code's history in two. Codes
    # are therefore append-only in spirit: retire one by dropping it from the UI, not by
    # renaming it, or old rows stop meaning what they said.
    #
    # NEGATIVE RATINGS ONLY, enforced below. Positive reasons were considered and
    # dropped: they are far less diagnostic, and a second step on the cheap positive
    # action suppresses the volume that makes the positive signal worth having.
    REASON_INACCURATE = "inaccurate"
    REASON_NOT_MY_RESULTS = "not_my_results"
    REASON_UNANSWERED = "unanswered"
    REASON_HARD_TO_FOLLOW = "hard_to_follow"
    REASON_OTHER = "other"
    RATING_REASON_CHOICES = (
        # Fabricated rules or numbers — the class the trap suite in ai-service's evals/
        # exists to measure, and the highest-severity one.
        (REASON_INACCURATE, "Not accurate"),
        # The closed-world break: a program outside the list it was given, or one the
        # household already receives. MFB-1427 / MFB-1788.
        (REASON_NOT_MY_RESULTS, "Not about my results"),
        # The commonest complaint about any assistant, and the one with no narrower home.
        (REASON_UNANSWERED, "Didn't answer me"),
        # Length, formatting and readability, which a household experiences as one thing.
        (REASON_HARD_TO_FOLLOW, "Confusing or too long"),
        # Kept deliberately. On its own it teaches little, but ITS RATE is the signal
        # that the four above are the wrong four.
        (REASON_OTHER, "Something else"),
    )
    rating_reason = models.CharField(max_length=32, choices=RATING_REASON_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            # ai-service assigns seq as MAX(seq)+1. Under the SQLite store that was
            # serialized by a lock local to one process; across dynos it is a race.
            # The Postgres store takes a row lock on the conversation to serialize
            # it, and this constraint is the backstop that turns a missed lock into a
            # failed insert rather than two turns silently sharing a position.
            models.UniqueConstraint(
                fields=["conversation", "seq"],
                name="assistant_msg_seq_unique",
            ),
            # Partial, because the vast majority of rows have no client id and NULLs
            # would otherwise all collide under a plain unique constraint.
            models.UniqueConstraint(
                fields=["conversation", "client_message_id"],
                condition=models.Q(client_message_id__isnull=False),
                name="assistant_msg_client_id_unique",
            ),
            # The rating API validates its input, but this table has two writers —
            # ai-service inserts every row, benefits-api updates this column — and a
            # column the weekly report AVERAGES cannot be left to whichever of them
            # happens to be right. A stray 5 would not error anywhere; it would just
            # quietly move the mean.
            models.CheckConstraint(
                check=models.Q(rating__isnull=True) | models.Q(rating__in=(1, -1)),
                name="assistant_msg_rating_valid",
            ),
            # Only assistant turns are rateable. The buttons are rendered on assistant
            # bubbles only, so a rating on a user turn means a hand-crafted request or
            # a bug — and either way it would be counted as feedback on a reply that
            # the household wrote themselves.
            models.CheckConstraint(
                check=models.Q(rating__isnull=True) | models.Q(role="assistant"),
                name="assistant_msg_rating_assistant_only",
            ),
            # A reason is only meaningful against a thumbs-down. Switching to a
            # thumbs-up, or clearing the rating, must take the reason with it — a reason
            # left stranded on a positive or unrated row would be counted as a
            # complaint about a reply nobody complained about.
            #
            # The `rating__isnull=False` term is load-bearing and is NOT redundant with
            # `rating=-1`, however much it reads that way. A CHECK passes in Postgres
            # unless it evaluates to FALSE, and NULL is not FALSE: with a stranded
            # reason on a row where `rating IS NULL`, `rating = -1` evaluates to NULL,
            # so `FALSE OR NULL` is NULL and the constraint ACCEPTS the row. That is the
            # exact case this constraint exists to refuse, and the first version of it
            # let that row straight through. Spelling the null check out makes the
            # disjunct FALSE instead of NULL.
            models.CheckConstraint(
                check=models.Q(rating_reason__isnull=True) | (models.Q(rating__isnull=False) & models.Q(rating=-1)),
                name="assistant_msg_reason_needs_thumbs_down",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role} message {self.seq} of {self.conversation_id}"


# --- Benji over SMS (MFB-2435; MFB-1916 proposal v3, decisions 3, 4 and 5) ----------
#
# Four tables, all written by benefits-api only. ai-service never sees a phone number,
# a hash, or these rows.
#
# THE PHONE NUMBER IS NEVER STORED. `phone_hash` is an HMAC-SHA256 of the E.164 number
# under BENJI_SMS_HASH_KEY (integrations/services/communications/benji_sms_hash.py).
# That is still personal data, reversible by anyone holding the key and a candidate
# number, so the hash is treated like the number: superuser-only, never searchable in
# the admin (a search puts it in the URL), and never in Sentry, alarms, the weekly
# report or the job queue (privacy companion §2).
#
# PER PHONE vs PER BINDING. What is true of a phone whatever screen it is bound to
# (revoked, marked shared) lives on `BenjiSmsPhone`, once. What is true of one on-ramp
# (screen, consent, lifecycle) lives on `BenjiSmsBinding`. Keeping the phone's state on
# its bindings would leave it on closed rows (a shared mark set by an on-ramp that opens
# no binding, a revocation START cleared on only the newest) and make every check
# aggregate across them.
#
# RETENTION follows the conversation. A deletion request ("remove my texts") is
# `manage.py find_benji_sms_phone --delete`, which runs
# `BenjiSmsPhone.delete_with_conversations()`: the phone's SMS conversations (their
# messages, bindings, deliveries and dead letters cascade, in the ORM and in the
# database through migrations 0172 and 0174), its stranger row, then the phone row, in
# one transaction.
# `BenjiSmsBinding.phone` is PROTECT so the phone row can never go first and leave
# conversations behind. Stranger rows, and delivery rows that belong to no binding,
# live one day (`BenjiSmsStrangerReply.objects.purge_expired()`).

# How long a stranger row, and a delivery row with no binding, are kept.
BENJI_SMS_UNBOUND_RETENTION = timedelta(days=1)


class BenjiSmsPhoneManager(models.Manager):
    def for_number(self, number: str) -> Optional["BenjiSmsPhone"]:
        """The phone row for a number, as typed on a form or as Twilio sends it, or None.

        The one place a number becomes a lookup, so the on-ramp, the webhook and
        support all normalize and hash it the same way. Raises `InvalidPhoneNumber`
        and `ImproperlyConfigured` as `phone_hash` does.
        """
        return self.filter(phone_hash=_phone_hash(number)).first()


def _phone_hash(number: str) -> str:
    # Imported here: integrations.services.communications imports screener.models.
    from integrations.services.communications.benji_sms_hash import phone_hash

    return phone_hash(number)


class BenjiSmsPhone(models.Model):
    """One phone, by hash: the state that belongs to the number, not to an on-ramp.

    Created by the first on-ramp for the number. A number that only ever texts as a
    stranger gets no row here (see `BenjiSmsStrangerReply`).
    """

    objects = BenjiSmsPhoneManager()

    phone_hash = models.CharField(max_length=64)
    # Set by STOP, or by a revocation in any wording. Every send checks it, and the
    # on-ramp refuses the phone while it is set. START clears it if the newest
    # binding's conversation has not expired.
    revoked_at = models.DateTimeField(blank=True, null=True)
    # Shared-phone guard: while in the future, inbound texts get the fixed "linked to
    # more than one set of results" reply and no model turn, and the on-ramp opens no
    # binding. The nightly sweep clears marks past the window.
    shared_until = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            # A Meta constraint rather than unique=True on the field: on Postgres the
            # field form adds a varchar_pattern_ops index for LIKE queries that nothing
            # runs against a hash.
            models.UniqueConstraint(fields=["phone_hash"], name="benji_sms_phone_hash_unique"),
        ]

    def __str__(self) -> str:
        # No hash: __str__ ends up in admin breadcrumbs, logs and error pages.
        return f"Benji SMS phone {self.pk}"

    def delete_with_conversations(self) -> int:
        """Serve a deletion request ("remove my texts") for this phone. Returns the
        number of conversations deleted.

        In one transaction: the SMS conversations of every binding, whose messages,
        bindings and deliveries cascade; the number's stranger row; then this row.
        Only SMS conversations are deleted. A binding can only point at one (see
        `BenjiSmsBinding.save`), and if one ever pointed elsewhere it would survive the
        first step, PROTECT would refuse the last, and the whole request would roll
        back rather than delete a web transcript.
        """
        with transaction.atomic():
            conversation_ids = set(self.bindings.values_list("conversation_id", flat=True))
            AssistantConversation.objects.filter(pk__in=conversation_ids, channel=AssistantChannel.SMS).delete()
            BenjiSmsStrangerReply.objects.filter(phone_hash=self.phone_hash).delete()
            self.delete()
        return len(conversation_ids)


class BenjiSmsBinding(models.Model):
    """Links a phone to one screen's SMS conversation, with its consent record.

    One active binding per phone: a new on-ramp from a different screen closes the
    previous binding and opens a new one, unseeded. A phone with several closed
    bindings over time is a normal state.

    One binding per conversation, ever, so a conversation belongs to one phone for
    good. ai-service keeps one active SMS conversation per screen (MFB-2432), so a
    second phone's on-ramp on the same screen would otherwise be handed the first
    phone's conversation: two people's texts in one transcript, the second phone's
    prompt built from the first's, and a deletion request for one phone deleting the
    other's transcript. Not only one *active* binding: a closed binding for phone A and
    an active one for phone B on the same conversation has all the same problems. The
    on-ramp has to open a new conversation for a new phone. A phone that resumes a
    conversation (START) reactivates its own binding rather than adding one.

    A binding's phone and conversation are fixed once it exists (`save`).

    The screen is `conversation.screen_uuid`, not a column here: a copy could drift
    from the conversation the replies are actually built from.

    Status reuses `AssistantConversationStatus`: a binding's lifecycle is its SMS
    conversation's (`closed` when superseded, `expired` after the quiet interval).
    """

    phone = models.ForeignKey(BenjiSmsPhone, related_name="bindings", on_delete=models.PROTECT)
    # A real FK, unlike AssistantConversation's code string: benefits-api writes these
    # rows, and every send needs the WhiteLabel for the benji_sms flag check.
    white_label = models.ForeignKey(WhiteLabel, related_name="benji_sms_bindings", on_delete=models.PROTECT)
    # One-to-one: enforced by the database, so two on-ramps racing for one conversation
    # cannot both win, which a check in save() could not promise.
    conversation = models.OneToOneField(
        AssistantConversation,
        related_name="sms_binding",
        on_delete=models.CASCADE,
    )
    # --- consent (decision 4). The User's TCPA columns are neither read nor written.
    # Revocation is per phone: BenjiSmsPhone.revoked_at. ---
    consented_at = models.DateTimeField()
    # The consent sentence's translation label plus a revision, so the exact words
    # consented to can be reproduced later.
    consent_version = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16,
        choices=AssistantConversationStatus.choices,
        default=AssistantConversationStatus.ACTIVE,
    )
    created_at = models.DateTimeField(default=timezone.now)
    # What expiry is measured from, falling back to created_at. NULL until the first
    # reply after the on-ramp text.
    last_inbound_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            # Inbound routing resolves a phone to exactly one binding. Two on-ramps
            # racing for one phone would otherwise leave two active rows.
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(status=AssistantConversationStatus.ACTIVE),
                name="benji_sms_one_active_binding_per_phone",
            ),
            # A new table, so unlike AssistantConversation.status this can be enforced.
            models.CheckConstraint(
                check=models.Q(status__in=AssistantConversationStatus.values),
                name="benji_sms_binding_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Benji SMS binding {self.pk} ({self.status})"

    def save(self, *args: object, **kwargs: object) -> None:
        """Refuse a non-SMS conversation, and any change of phone or conversation.

        A binding routes texts into its conversation. Pointed at the web widget's
        conversation, a person's texts would land in a transcript the browser shows to
        anyone holding the results link; re-pointed at another phone's, they would mix
        two people's texts. A check constraint cannot reach across tables, so the
        guard is here, on every save through the ORM. `QuerySet.update()` bypasses it;
        nothing in the SMS code updates these two columns, and a deletion request
        rolls back rather than delete a web transcript if one ever did.
        """
        if self.conversation.channel != AssistantChannel.SMS:
            raise ValueError("A Benji SMS binding must point at an SMS conversation")
        if not self._state.adding:
            stored = BenjiSmsBinding.objects.filter(pk=self.pk).values("phone_id", "conversation_id").first()
            if stored and (stored["phone_id"], stored["conversation_id"]) != (self.phone_id, self.conversation_id):
                raise ValueError("A Benji SMS binding's phone and conversation cannot change")
        super().save(*args, **kwargs)

    def end(self, status: str) -> None:
        """Close or expire this binding and its conversation together.

        `status` and the conversation's `status` are two copies of one lifecycle (the
        constraints above need it on this table). Changing one without the other would
        leave an active binding on a dead conversation, routing texts to stale context
        and blocking the phone's next on-ramp. Every lifecycle change goes through here.
        """
        if status not in (AssistantConversationStatus.CLOSED, AssistantConversationStatus.EXPIRED):
            raise ValueError(f"Not an ending status: {status}")
        with transaction.atomic():
            BenjiSmsBinding.objects.filter(pk=self.pk).update(status=status)
            AssistantConversation.objects.filter(pk=self.conversation_id).update(status=status)
        self.status = status


class BenjiSmsDeliveryKind(models.TextChoices):
    """What an outbound text was. Only model replies have an AssistantMessage."""

    REPLY = "reply", "Model reply"
    # The held-back part of a capped reply, sent on MORE. Same message as its reply.
    REMAINDER = "remainder", "Reply remainder (MORE)"
    ONRAMP = "onramp", "On-ramp text"
    DISCLOSURE = "disclosure", "AI disclosure"
    # STOP, HELP, START, stranger, shared, expired, picture, daily cap, apology.
    FIXED = "fixed", "Fixed reply"


# Kinds that answer the person in a conversation. They need a binding: it is what
# every send checks for revocation, and what per-phone caps and audits count by.
_CONVERSATION_KINDS = [BenjiSmsDeliveryKind.REPLY, BenjiSmsDeliveryKind.REMAINDER, BenjiSmsDeliveryKind.DISCLOSURE]
# Kinds that carry model-written text. They need their message.
_MODEL_KINDS = [BenjiSmsDeliveryKind.REPLY, BenjiSmsDeliveryKind.REMAINDER]


class BenjiSmsDeliveryStatus(models.TextChoices):
    """Twilio's message statuses, as its status callback reports them.

    Not a check constraint: Twilio can add a status, and a callback carrying one should
    be recorded rather than rejected. The column is wider than the longest known value
    (`partially_delivered`, 19) for the same reason.
    """

    ACCEPTED = "accepted", "Accepted"
    SCHEDULED = "scheduled", "Scheduled"
    QUEUED = "queued", "Queued"
    SENDING = "sending", "Sending"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    PARTIALLY_DELIVERED = "partially_delivered", "Partially delivered"
    UNDELIVERED = "undelivered", "Undelivered"
    FAILED = "failed", "Failed"
    READ = "read", "Read"
    CANCELED = "canceled", "Canceled"
    RECEIVING = "receiving", "Receiving"
    RECEIVED = "received", "Received"


class BenjiSmsDelivery(models.Model):
    """One outbound Benji text and what happened to it. No bodies, no numbers.

    `remainder_text` is the exception to "no bodies": the part of a reply over the
    450-character cap, held for MORE. It is model-generated text of the same class as
    the reply it belongs to, under the same controls (privacy companion §2).

    A reply stored with no `outbound_sid` is retryable. One with an `outbound_sid` and
    no `delivery_status` after a fixed interval is an alarm.
    """

    kind = models.CharField(max_length=16, choices=BenjiSmsDeliveryKind.choices)
    # Set for replies and remainders. NULL for everything else, which no model wrote.
    message = models.ForeignKey(
        AssistantMessage,
        related_name="sms_deliveries",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    # Required for replies, remainders and the disclosure. NULL only for an on-ramp text
    # that opened no binding (shared phone) and fixed replies to a number with none.
    # Rows with no binding can be tied to no phone, so like stranger rows they are kept
    # one day (BenjiSmsStrangerReply.objects.purge_expired): their Twilio SIDs resolve
    # to the number at Twilio.
    binding = models.ForeignKey(
        BenjiSmsBinding,
        related_name="deliveries",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    # The inbound MessageSid this send answers; NULL for the on-ramp text. Not unique:
    # one inbound can produce the disclosure and the reply.
    inbound_sid = models.CharField(max_length=34, blank=True, null=True)
    # Unique (Meta), because the status callback finds its row by it.
    outbound_sid = models.CharField(max_length=34, blank=True, null=True)
    delivery_status = models.CharField(
        max_length=32,
        choices=BenjiSmsDeliveryStatus.choices,
        blank=True,
        null=True,
    )
    # Twilio's ErrorCode on undelivered or failed, e.g. 30007 (carrier filtered).
    delivery_error_code = models.IntegerField(blank=True, null=True)
    # Twilio's NumSegments: what the text cost.
    segments = models.SmallIntegerField(blank=True, null=True)
    remainder_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(blank=True, null=True)
    # When `delivery_status` last changed.
    status_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        # Indexes and uniqueness declared here, not on the fields: the field forms add a
        # varchar_pattern_ops index on Postgres that nothing runs a LIKE against.
        constraints = [
            # NULLs are distinct, so unsent rows do not collide.
            models.UniqueConstraint(fields=["outbound_sid"], name="benji_sms_delivery_outbound_sid_unique"),
            models.CheckConstraint(
                check=models.Q(kind__in=BenjiSmsDeliveryKind.values),
                name="benji_sms_delivery_kind_valid",
            ),
            # A reply without its message could not be traced back to what was said.
            models.CheckConstraint(
                check=~models.Q(kind__in=_MODEL_KINDS) | models.Q(message__isnull=False),
                name="benji_sms_delivery_reply_has_message",
            ),
            models.CheckConstraint(
                check=~models.Q(kind__in=_CONVERSATION_KINDS) | models.Q(binding__isnull=False),
                name="benji_sms_delivery_conversation_kind_has_binding",
            ),
        ]
        indexes = [
            models.Index(fields=["inbound_sid"], name="benji_sms_delivery_inbound_idx"),
            # "Sent, no status after N minutes" and daily segment spend both scan by it.
            models.Index(fields=["sent_at"], name="benji_sms_delivery_sent_idx"),
        ]

    def __str__(self) -> str:
        return f"Benji SMS {self.kind} {self.pk} ({self.delivery_status or 'no status'})"


class BenjiSmsStrangerReplyManager(models.Manager):
    def for_number(self, number: str) -> models.QuerySet:
        """The number's stranger row, if any, as a queryset. Raises as `phone_hash` does."""
        return self.filter(phone_hash=_phone_hash(number))

    def purge_expired(self, now: Optional[datetime] = None) -> tuple[int, int]:
        """Delete stranger rows, and delivery rows with no binding, older than a day.

        For the nightly sweep. Returns (stranger rows, delivery rows) deleted. The two
        go together because a stranger's reply leaves both, and a delivery row's Twilio
        SIDs resolve to the number at Twilio as surely as the stranger row's hash does.
        Daily spend and delivery alarms must read the day's rows before this runs.
        """
        cutoff = (now or timezone.now()) - BENJI_SMS_UNBOUND_RETENTION
        with transaction.atomic():
            strangers, _ = self.filter(replied_at__lt=cutoff).delete()
            deliveries, _ = BenjiSmsDelivery.objects.filter(binding__isnull=True, created_at__lt=cutoff).delete()
        return strangers, deliveries


class BenjiSmsStrangerReply(models.Model):
    """When a number with no binding last got the fixed stranger reply.

    Kept apart from `BenjiSmsPhone` on purpose: these rows are purged after a day, and
    a texter who never used the on-ramp should leave no lasting trace. That includes
    the reply's delivery row, which `purge_expired` removes with it.

    At most one reply per number per day, remembered in Postgres so it holds under a
    Redis outage (privacy companion §9). One row per hash, so two webhooks racing for
    one number cannot both claim the reply: the reply path inserts, or moves an
    over-a-day-old `replied_at` forward, and replies only if it won. The nightly sweep
    purges rows older than a day.
    """

    phone_hash = models.CharField(max_length=64)
    replied_at = models.DateTimeField(default=timezone.now)

    objects = BenjiSmsStrangerReplyManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["phone_hash"], name="benji_sms_stranger_hash_unique"),
        ]
        indexes = [
            # The nightly purge.
            models.Index(fields=["replied_at"], name="benji_sms_stranger_replied_idx"),
        ]

    def __str__(self) -> str:
        return f"Benji SMS stranger reply {self.pk}"


class BenjiSmsDeadLetterManager(models.Manager):
    def record(
        self,
        *,
        task_name: str,
        task_id: str,
        attempts: int,
        error_type: str,
        conversation_id: Optional[str] = None,
        inbound_sid: Optional[str] = None,
    ) -> "BenjiSmsDeadLetter":
        """Record a job that failed for good (screener.tasks.BenjiSmsTask.dead_letter).

        A conversation deleted while its job was queued or retrying (a deletion request)
        leaves nothing to point at, so the row keeps neither the conversation nor the
        inbound SID: a SID resolves to the number at Twilio, and the row would outlive
        the deletion it belongs to. The conversation row is locked from the check to the
        insert, so a deletion cannot land in between and fail the insert.
        """
        with transaction.atomic():
            if (
                conversation_id is None
                or not AssistantConversation.objects.select_for_update().filter(pk=conversation_id).exists()
            ):
                conversation_id = None
                inbound_sid = None
            return self.create(
                task_name=task_name,
                task_id=task_id,
                attempts=attempts,
                error_type=error_type,
                conversation_id=conversation_id,
                inbound_sid=inbound_sid,
            )


class BenjiSmsDeadLetter(models.Model):
    """A Benji SMS job that failed every attempt (MFB-2436; proposal v3, decision 5).

    Ids and the error's class only, like the job payload: never the message text, the
    phone number or its hash, and never the exception's message, which can quote any of
    them. Retention follows the conversation: it cascades with it, in the ORM and in the
    database through migration 0174, so a deletion request takes these rows too.
    Writing a row also logs an ERROR, which is the alarm.
    """

    # The Celery task name, e.g. "screener.benji_sms_turn".
    task_name = models.CharField(max_length=64)
    # Celery's id for the job. Retries keep it, so it names the job, not an attempt.
    task_id = models.CharField(max_length=64)
    conversation = models.ForeignKey(
        AssistantConversation,
        related_name="sms_dead_letters",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    # The inbound MessageSid the job was answering.
    inbound_sid = models.CharField(max_length=34, blank=True, null=True)
    attempts = models.PositiveSmallIntegerField()
    # Qualified class name of the last attempt's exception, e.g. "requests.exceptions.Timeout".
    error_type = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)

    objects = BenjiSmsDeadLetterManager()

    class Meta:
        constraints = [
            # A SID with no conversation could outlive the deletion that removed the
            # conversation it came from (see BenjiSmsDeadLetterManager.record).
            models.CheckConstraint(
                check=models.Q(inbound_sid__isnull=True) | models.Q(conversation__isnull=False),
                name="benji_sms_dead_letter_sid_has_conversation",
            ),
        ]
        indexes = [
            models.Index(fields=["created_at"], name="benji_sms_dead_letter_at_idx"),
            # benji_sms_worker_check --fail finds its job's row by it.
            models.Index(fields=["task_id"], name="benji_sms_dead_letter_task_idx"),
        ]

    def __str__(self) -> str:
        return f"Benji SMS dead letter {self.pk} ({self.task_name}, {self.error_type})"
