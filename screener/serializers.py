import logging
from datetime import date
from django.db import IntegrityError, transaction
from django.utils import timezone
from sentry_sdk import capture_message

logger = logging.getLogger(__name__)
from programs.models import Program, WarningMessage
from screener.models import (
    CurrentBenefit,
    EnergyCalculatorMember,
    EnergyCalculatorScreen,
    Screen,
    HouseholdMember,
    IncomeStream,
    Expense,
    Message,
    Insurance,
    WhiteLabel,
    EligibilitySnapshot,
    NPSScore,
)
from authentication.serializers import UserOffersSerializer
from rest_framework import serializers
from translations.serializers import TranslationSerializer
from validations.serializers import ValidationSerializer


class MessageSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Message
        fields = "__all__"


class InsuranceSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Insurance
        fields = "__all__"
        read_only_fields = ("household_member",)


class IncomeStreamSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = IncomeStream
        fields = "__all__"
        read_only_fields = ("screen", "household_member", "id")


class ExpenseSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ("screen", "household_member", "id")


class EnergyCalculatorMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyCalculatorMember
        fields = "__all__"
        read_only_fields = ("household_member", "id")


class EnergyCalculatorScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyCalculatorScreen
        fields = "__all__"
        read_only_fields = ("screen", "id")


class HouseholdMemberSerializer(serializers.ModelSerializer):
    income_streams = IncomeStreamSerializer(many=True)
    insurance = InsuranceSerializer(required=False, allow_null=True)
    birth_year = serializers.IntegerField(required=False, allow_null=True)
    birth_month = serializers.IntegerField(required=False, allow_null=True)
    energy_calculator = EnergyCalculatorMemberSerializer(required=False, allow_null=True)

    def validate(self, data):
        birth_year = data.pop("birth_year", None)
        birth_month = data.pop("birth_month", None)

        if birth_year is None or birth_month is None:
            return data

        if birth_month < 1 or birth_month > 12:
            raise serializers.ValidationError("Birth month must be between 1 and 12")

        birth_year_month = date(year=birth_year, month=birth_month, day=1)

        if birth_year_month > timezone.now().date():
            raise serializers.ValidationError("Birth year and month are in the future")

        data["birth_year_month"] = birth_year_month

        if "age" not in data or data["age"] is None:
            # No reference_date needed - member is being created, no screen/validations exist yet
            data["age"] = HouseholdMember.age_from_date(birth_year_month)

        return data

    class Meta:
        model = HouseholdMember
        fields = (
            "id",
            "screen",
            "frontend_id",
            "relationship",
            "age",
            "student",
            "student_full_time",
            "student_job_training_program",
            "student_has_work_study",
            "student_works_20_plus_hrs",
            "pregnant",
            "unemployed",
            "worked_in_last_18_mos",
            "visually_impaired",
            "disabled",
            "long_term_disability",
            "veteran",
            "medicaid",
            "disability_medicaid",
            "has_income",
            "income_streams",
            "insurance",
            "birth_year",
            "birth_month",
            "energy_calculator",
            "is_care_worker",
        )
        read_only_fields = ("screen", "id")


# SSI program variants across white labels. An sSI income stream implies SSI
# receipt regardless of whether the user ticked the tile, so all variants are
# listed here; the WL-scoped resolve in `_write_current_benefits()` drops the
# ones a given white label doesn't offer (e.g. `wa_ssi` on a CO screen).
_SSI_BENEFIT_NAMES = frozenset({"ssi", "tx_ssi", "wa_ssi", "cesn_ssi"})


def _derived_current_benefit_names(screen: Screen) -> set[str]:
    """`name_abbreviated` values implied by screen state, independent of the
    frontend's current-benefits toggles.

    OR'd into the frontend's `current_benefits` list inside `_write_current_benefits()`
    so the join table reflects benefits the household demonstrably receives even when
    the tile wasn't ticked (or was explicitly unticked) — preserving the long-standing
    compound semantics of `Screen.has_benefit()`.

    Today there is one rule: an sSI income stream implies SSI. The `chp` and
    `ma_mass_health` compounds are deliberately NOT here — those are member-level
    insurance checks (`HouseholdMember.has_benefit()` / `member.insurance.*`) and never
    flow through `current_benefits`. Add new derivable compounds here as they appear.
    """
    derived: set[str] = set()
    if screen.calc_gross_income("yearly", ("sSI",)) > 0:
        derived |= _SSI_BENEFIT_NAMES
    return derived


def _write_current_benefits(screen: Screen, current_benefits: list[str]) -> None:
    """
    Write the CurrentBenefit join table for `screen`, replacing any existing rows.

    `current_benefits` is a list of `name_abbreviated` strings (e.g. ["tx_snap",
    "tanf"]). Each is resolved to a Program via the (white_label, name_abbreviated)
    lookup and written directly; a name the current WL doesn't offer is silently
    skipped. Names derivable from screen state (currently SSI, via an sSI income
    stream) are OR'd in via `_derived_current_benefit_names()` so the join table
    reflects benefits the household demonstrably receives even when the tile wasn't
    ticked.

    Uses select_for_update() inside a transaction to serialize concurrent PATCH
    requests on the same screen and prevent races on the delete+bulk_create. The
    screen is re-fetched inside the atomic block so the write reflects the
    post-lock committed state.
    """
    with transaction.atomic():
        screen = Screen.objects.select_for_update().get(pk=screen.pk)

        # Frontend sent explicit program names, plus any names derivable from
        # screen state (e.g. SSI from an sSI income stream). Resolve each in this
        # screen's white label; silently drop any this WL doesn't offer.
        requested = set(current_benefits)
        derived = _derived_current_benefit_names(screen)
        resolved = Program.objects.filter(
            white_label=screen.white_label,
            name_abbreviated__in=requested | derived,
        ).values_list("id", "name_abbreviated")
        program_ids_to_write = [program_id for program_id, _ in resolved]

        # A *frontend-requested* name with no Program in this WL is dropped
        # rather than erroring (a WL only writes the programs it offers). That's
        # also how a typo'd / stale name_abbreviated vanishes — a config problem
        # worth surfacing, so report it to Sentry. capture_message groups identical
        # messages, so a recurring bad name collapses into one counted issue rather
        # than paging per request; level is "warning" (not "error") because a dropped
        # name is benign per request. Derived names (e.g. wa_ssi injected on a CO
        # screen) are excluded — those are expected cross-WL non-matches, not client
        # errors.
        dropped = requested - {name for _, name in resolved}
        if dropped:
            capture_message(
                f"current_benefits: dropped {len(dropped)} name(s) not offered by white_label "
                f"{screen.white_label_id}: {sorted(dropped)}",
                level="warning",
                extras={"white_label_id": screen.white_label_id, "dropped": sorted(dropped)},
            )

        CurrentBenefit.objects.filter(screen=screen).delete()
        if program_ids_to_write:
            CurrentBenefit.objects.bulk_create(
                [CurrentBenefit(screen=screen, program_id=pid) for pid in program_ids_to_write]
            )


class ScreenSerializer(serializers.ModelSerializer):
    household_members = HouseholdMemberSerializer(many=True)
    expenses = ExpenseSerializer(many=True)
    user = UserOffersSerializer(read_only=True)
    white_label = serializers.CharField(source="white_label.code")
    energy_calculator = EnergyCalculatorScreenSerializer(required=False, allow_null=True)
    # The current benefits the household receives, as a list of `name_abbreviated`
    # strings. Read and write use the same JSON key but different mechanisms:
    #
    #   * Write: this ListField (write_only). The value is popped in create()/update()
    #     and written to the CurrentBenefit join table by _write_current_benefits().
    #     An empty list clears the join table; an absent key is treated as empty
    #     (so non-frontend clients that build screens without it — validation
    #     imports, screen-pull commands — don't 400).
    #   * Read: to_representation() injects the value under the same key. The model
    #     attribute `current_benefits` is the reverse relation (a manager), not a
    #     list of names, so it can't be serialized directly.
    #
    # max_length bounds an otherwise-unbounded payload: there are ~130 distinct
    # name_abbreviated values across all white labels, so 256 is a comfortable
    # ceiling. Unknown names are dropped in _write_current_benefits(), so element
    # content needn't be validated here. The per-element cap mirrors the
    # Program.name_abbreviated column (max_length=120) so no DB-valid name is
    # rejected here.
    current_benefits = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
        write_only=True,
        max_length=256,
    )

    class Meta:
        model = Screen
        fields = (
            "id",
            "uuid",
            "white_label",
            "completed",
            "is_test",
            "is_test_data",
            "start_date",
            "submission_date",
            "frozen",
            "agree_to_tos",
            "is_13_or_older",
            "zipcode",
            "county",
            "referral_source",
            "referrer_code",
            "path",
            "household_size",
            "household_assets",
            "household_members",
            "last_email_request_date",
            "last_tax_filing_year",
            "expenses",
            "energy_calculator",
            "user",
            "external_id",
            "request_language_code",
            "current_benefits",
            "has_benefits",
            "needs_food",
            "needs_baby_supplies",
            "needs_housing_help",
            "needs_mental_health_help",
            "needs_child_dev_help",
            "needs_funeral_help",
            "needs_family_planning_help",
            "needs_job_resources",
            "needs_dental_care",
            "needs_legal_services",
            "needs_college_savings",
            "needs_veteran_services",
            "needs_disability_resources",
            "needs_aging_resources",
            "utm_id",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
        )
        read_only_fields = (
            "id",
            "uuid",
            "submision_date",
            "frozen",
            "last_email_request_date",
            "completed",
            "user",
            "is_test_data",
        )
        create_only_fields = (
            "external_id",
            "is_test",
            "referrer_code",
            "white_label",
            "utm_id",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
        )

    def __init__(self, *args, **kwargs):
        self.force = kwargs.pop("force", False)
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        white_label_code = attrs.pop("white_label")["code"]
        white_label = WhiteLabel.objects.get(code=white_label_code)
        attrs["white_label"] = white_label

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # current_benefits is write_only as a field; supply the read value here.
        # Iterate the relation (serves from the current_benefits__program prefetch
        # the viewset sets up; otherwise one query). create()/update() invalidate the
        # instance's current-benefits caches after writing, so this reflects the
        # committed rows even on a write request.
        data["current_benefits"] = sorted(cb.program.name_abbreviated for cb in instance.current_benefits.all())
        return data

    def create(self, validated_data):
        household_members = validated_data.pop("household_members")
        expenses = validated_data.pop("expenses")
        energy_calculator_screen = validated_data.pop("energy_calculator", None)
        # Not a Screen column — pop before the create() and write separately.
        # Absent (non-frontend clients) is treated as no current benefits.
        current_benefits = validated_data.pop("current_benefits", [])
        screen = Screen.objects.create(**validated_data, completed=False)
        screen.set_screen_is_test()
        for member in household_members:
            incomes = member.pop("income_streams")
            insurance = member.pop("insurance")
            energy_calculator_member = member.pop("energy_calculator", None)
            household_member = HouseholdMember.objects.create(**member, screen=screen)
            for income in incomes:
                IncomeStream.objects.create(**income, screen=screen, household_member=household_member)
            if insurance is not None:
                Insurance.objects.create(**insurance, household_member=household_member)
            if energy_calculator_member is not None:
                EnergyCalculatorMember.objects.create(**energy_calculator_member, household_member=household_member)
        for expense in expenses:
            Expense.objects.create(**expense, screen=screen)
        if energy_calculator_screen is not None:
            EnergyCalculatorScreen.objects.create(**energy_calculator_screen, screen=screen)
        _write_current_benefits(screen, current_benefits)
        screen.invalidate_current_benefits_cache()
        return screen

    def update(self, instance, validated_data):
        if instance.frozen:
            return instance

        household_members = validated_data.pop("household_members")
        expenses = validated_data.pop("expenses")
        energy_calculator_screen = validated_data.pop("energy_calculator", None)
        # Not a Screen column — pop before the bulk .update() and write separately.
        # Absent (non-frontend clients) is treated as no current benefits.
        current_benefits = validated_data.pop("current_benefits", [])

        # don't update create only fields
        for field in self.Meta.create_only_fields:
            if field in validated_data:
                validated_data.pop(field)

        Screen.objects.filter(pk=instance.id).update(**validated_data)
        HouseholdMember.objects.filter(screen=instance).delete()
        EnergyCalculatorScreen.objects.filter(screen=instance).delete()
        Expense.objects.filter(screen=instance).delete()
        for member in household_members:
            incomes = member.pop("income_streams")
            insurance = member.pop("insurance", None)
            energy_calculator_member = member.pop("energy_calculator", None)
            household_member = HouseholdMember.objects.create(**member, screen=instance)
            for income in incomes:
                IncomeStream.objects.create(**income, screen=instance, household_member=household_member)
            if insurance is not None:
                Insurance.objects.create(**insurance, household_member=household_member)
            if energy_calculator_member is not None:
                EnergyCalculatorMember.objects.create(**energy_calculator_member, household_member=household_member)
        for expense in expenses:
            Expense.objects.create(**expense, screen=instance)
        if energy_calculator_screen is not None:
            EnergyCalculatorScreen.objects.create(**energy_calculator_screen, screen=instance)
        instance.refresh_from_db()
        instance.set_screen_is_test()
        _write_current_benefits(instance, current_benefits)
        # The instance was loaded with current_benefits__program prefetched (the
        # viewset) and _write_current_benefits replaced those rows on a separately
        # locked Screen — so this instance's cached view is now stale. Invalidate so
        # to_representation re-reads the committed rows.
        instance.invalidate_current_benefits_cache()
        return instance


class CurrentBenefitToggleSerializer(serializers.Serializer):
    """Input for the single-benefit toggle endpoint (PATCH /screens/<uuid:screen_uuid>/current-benefits/).

    `name_abbreviated` is a program name_abbreviated value; `has` selects add (True) vs remove (False).
    Resolving the name to a Program and writing the join-table row happen in the
    view, which has the screen (and thus its white_label) in hand.

    `name_abbreviated`'s max_length mirrors the Program.name_abbreviated column (120) so no
    DB-valid name is rejected before the white-label-scoped lookup in the view.
    """

    name_abbreviated = serializers.CharField(max_length=120)
    has = serializers.BooleanField()


class NavigatorSerializer(serializers.Serializer):
    name = TranslationSerializer()
    phone_number = serializers.CharField()
    email = TranslationSerializer()
    assistance_link = TranslationSerializer()
    description = TranslationSerializer()
    languages = serializers.ListField()


class WarningMessageSerializer(serializers.ModelSerializer):
    message = TranslationSerializer()
    link_url = TranslationSerializer()
    link_text = TranslationSerializer()
    legal_statuses = serializers.SerializerMethodField()

    class Meta:
        model = WarningMessage
        fields = ("message", "link_url", "link_text", "legal_statuses")

    def get_legal_statuses(self, obj: WarningMessage):
        return [m.status for m in obj.legal_statuses.all()]


class MemberEligibilitySerializer(serializers.Serializer):
    frontend_id = serializers.UUIDField()
    eligible = serializers.BooleanField()
    value = serializers.IntegerField()
    already_has = serializers.BooleanField()


class EligibilitySerializer(serializers.Serializer):
    description_short = TranslationSerializer()
    name = TranslationSerializer()
    name_abbreviated = serializers.CharField()
    external_name = serializers.CharField()
    description = TranslationSerializer()
    value_type = serializers.CharField()
    learn_more_link = TranslationSerializer()
    apply_button_link = TranslationSerializer()
    apply_button_description = TranslationSerializer()
    estimated_value = serializers.IntegerField()
    household_value = serializers.IntegerField()
    estimated_delivery_time = TranslationSerializer()
    estimated_application_time = TranslationSerializer()
    legal_status_required = serializers.ListField()
    eligible = serializers.BooleanField()
    members = MemberEligibilitySerializer(many=True)
    failed_tests = serializers.ListField()
    passed_tests = serializers.ListField()
    navigators = NavigatorSerializer(many=True)
    already_has = serializers.BooleanField()
    new = serializers.BooleanField()
    low_confidence = serializers.BooleanField()
    documents = TranslationSerializer(many=True)
    multiple_tax_units = serializers.BooleanField()
    estimated_value_override = TranslationSerializer()
    warning_messages = WarningMessageSerializer(many=True)
    required_programs = serializers.ListField(child=serializers.IntegerField())
    value_format = serializers.CharField()

    class Meta:
        fields = "__all__"


class EligibilityTranslationSerializer(serializers.Serializer):
    translations = serializers.DictField()

    class Meta:
        fields = ("translations",)


class ProgramCategoryCapSerializer(serializers.Serializer):
    programs = serializers.ListSerializer(child=serializers.CharField())
    household_cap = serializers.IntegerField()
    member_caps = serializers.DictField()


class ProgramCategorySerializer(serializers.Serializer):
    external_name = serializers.CharField()
    icon = serializers.CharField()
    name = TranslationSerializer()
    description = TranslationSerializer()
    caps = ProgramCategoryCapSerializer(many=True)
    tax_category = serializers.BooleanField()
    priority = serializers.IntegerField()
    programs = serializers.ListField(child=serializers.IntegerField())


class UrgentNeedSerializer(serializers.Serializer):
    name = TranslationSerializer()
    description = TranslationSerializer()
    link = TranslationSerializer()
    category_type = TranslationSerializer()
    phone_number = serializers.CharField()


class ResultsSerializer(serializers.Serializer):
    programs = EligibilitySerializer(many=True)
    urgent_needs = UrgentNeedSerializer(many=True)
    screen_id = serializers.CharField()
    default_language = serializers.CharField()
    missing_programs = serializers.BooleanField()
    validations = ValidationSerializer(many=True)
    program_categories = ProgramCategorySerializer(many=True)
    pe_data = serializers.DictField(required=False, allow_null=True)


def get_latest_eligibility_snapshot(screen_uuid):
    """
    Get the most recent non-error eligibility snapshot for a screen.

    Args:
        screen_uuid: UUID of the screen

    Returns:
        EligibilitySnapshot or None if not found
    """
    return (
        EligibilitySnapshot.objects.filter(screen__uuid=screen_uuid, had_error=False)
        .order_by("-submission_date")
        .first()
    )


class NPSScoreSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(write_only=True)
    score = serializers.IntegerField(min_value=1, max_value=10)

    def create(self, validated_data: dict) -> NPSScore:
        uuid = validated_data.pop("uuid")
        snapshot = get_latest_eligibility_snapshot(uuid)

        if snapshot is None:
            raise serializers.ValidationError({"uuid": "No eligibility snapshot found for this screen"})

        # Try to create NPS score - database constraint prevents duplicates
        try:
            nps_score = NPSScore.objects.create(eligibility_snapshot=snapshot, **validated_data)
            logger.info(
                f"NPS score created: score={nps_score.score}, " f"snapshot_id={snapshot.id}, screen_uuid={uuid}"
            )
            return nps_score
        except IntegrityError:
            logger.warning(f"Duplicate NPS submission attempted for screen_uuid={uuid}")
            raise serializers.ValidationError({"uuid": "NPS score already submitted for this session"})


class NPSScoreReasonSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(write_only=True)
    score_reason = serializers.CharField(max_length=500, trim_whitespace=True)

    def update(self, instance: NPSScore, validated_data: dict) -> NPSScore:
        """
        Update an existing NPS score with a reason.
        Standard DRF update method for PATCH operations.
        """
        instance.score_reason = validated_data.get("score_reason", instance.score_reason)
        instance.save(update_fields=["score_reason"])
        logger.info(
            f"NPS reason updated: score={instance.score}, reason_length={len(instance.score_reason)}, "
            f"snapshot_id={instance.eligibility_snapshot_id}"
        )
        return instance

    def get_nps_score(self, uuid: str) -> NPSScore:
        """
        Helper method to retrieve NPS score by screen UUID.
        """
        snapshot = get_latest_eligibility_snapshot(uuid)

        if snapshot is None:
            raise serializers.ValidationError({"uuid": "No eligibility snapshot found for this screen"})

        try:
            return snapshot.nps_score
        except NPSScore.DoesNotExist:
            raise serializers.ValidationError({"uuid": "No NPS score found for this session"})


KG_TO_LBS = 2.20462


def _convert_emissions_to_lbs(emissions: dict) -> dict:
    """Convert each stat in an emissions dict from kgCO2e to lbCO2e."""
    return {key: {"value": (stat.get("value") or 0) * KG_TO_LBS, "unit": "lbCO2e"} for key, stat in emissions.items()}


class RemImpactSerializer(serializers.Serializer):
    """
    Strips the Rewiring America /api/v1/rem/address response to the two values
    the frontend needs: the total cost delta (bill impact) and the total
    emissions delta (CO₂e impact).

    Emissions are converted from kgCO2e → lbCO2e so the frontend can display
    lb values and feed them directly into the EPA equivalencies utility.

    Input: raw dict from RewiringAmericaClient.fetch_rem_impact()
    Output: { bill_delta: {...}, emissions_delta: {...} }
    """

    bill_delta = serializers.DictField()
    emissions_delta = serializers.DictField()

    def to_representation(self, instance: dict) -> dict:
        total_delta = instance.get("fuel_results", {}).get("total", {}).get("delta", {})
        return {
            "bill_delta": total_delta.get("cost", {}),
            "emissions_delta": _convert_emissions_to_lbs(total_delta.get("emissions", {})),
        }
