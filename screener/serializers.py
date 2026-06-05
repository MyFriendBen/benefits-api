import logging
from datetime import date
from django.db import IntegrityError, transaction
from django.utils import timezone

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


def _benefit_map_from_has_columns(screen) -> dict:
    """
    Returns the full `name_abbreviated → bool` map for a screen derived from its
    legacy `has_*` columns, including the fan-out (one `has_*` column → many WL
    program variants, e.g. `has_tanf` → tanf / co_tanf / il_tanf / …) and the
    compound conditions (`ssi` via has_ssi OR sSI income; `ma_mass_health` via
    has_medicaid OR has_medicaid_hi).

    Only used by the backward-compat write path in `_write_current_benefits()`:
    when an old frontend PATCHes `has_*` fields (and no `current_benefits` list),
    we mirror those columns into the CurrentBenefit join table so `has_benefit()`
    (which reads the join table per Step 3a / MFB-719) stays correct.

    Relocated here from `Screen._build_benefit_map()` in Step 5a (MFB-869). Dies
    together with the `has_*` write path in Step 6 (MFB-720), once the frontend
    sends `current_benefits` exclusively.
    """
    has_ssi_or_ssi_income = screen.has_ssi or screen.calc_gross_income("yearly", ("sSI",)) > 0

    return {
        "tanf": screen.has_tanf,
        "nc_tanf": screen.has_tanf,
        "co_tanf": screen.has_tanf,
        "il_tanf": screen.has_tanf,
        "tx_tanf": screen.has_tanf,
        "wic": screen.has_wic,
        "co_wic": screen.has_wic,
        "il_wic": screen.has_wic,
        "nc_wic": screen.has_wic,
        "tx_wic": screen.has_wic,
        "snap": screen.has_snap,
        "sunbucks": screen.has_sunbucks,
        "co_snap": screen.has_snap,
        "nc_snap": screen.has_snap,
        "il_snap": screen.has_snap,
        "tx_snap": screen.has_snap,
        "wa_snap": screen.has_snap,
        "lifeline": screen.has_lifeline,
        "tx_lifeline": screen.has_lifeline,
        "wa_lifeline": screen.has_lifeline,
        "acp": screen.has_acp,
        "eitc": screen.has_eitc,
        "tx_eitc": screen.has_eitc,
        "coeitc": screen.has_coeitc,
        "il_eitc": screen.has_il_eitc,
        "nslp": screen.has_nslp,
        "tx_nslp": screen.has_nslp,
        "wa_nslp": screen.has_nslp,
        "ctc": screen.has_ctc,
        "tx_ctc": screen.has_ctc,
        "wa_ctc": screen.has_ctc,
        "il_ctc": screen.has_il_ctc,
        "il_transit_reduced_fare": screen.has_il_transit_reduced_fare,
        "il_bap": screen.has_il_bap,
        "il_csfp": screen.has_csfp,
        "il_hbwd": screen.has_il_hbwd,
        "il_ccap": screen.has_ccap,
        "cesn_cope": screen.has_project_cope,
        "cesn_heap": screen.has_cesn_heap,
        "rtdlive": screen.has_rtdlive,
        "cccap": screen.has_ccap,
        "mydenver": screen.has_mydenver,
        "ssi": has_ssi_or_ssi_income,
        "tx_ssi": has_ssi_or_ssi_income,
        "wa_ssi": has_ssi_or_ssi_income,
        "tx_csfp": screen.has_csfp,
        "tx_harris_rides": screen.has_harris_county_rides,
        "andcs": screen.has_andcs,
        "co_head_start": screen.has_head_start,
        "cpcr": screen.has_cpcr,
        "cesn_cpcr": screen.has_cpcr,
        "cdhcs": screen.has_cdhcs,
        "dpp": screen.has_dpp,
        "ede": screen.has_ede,
        "erc": screen.has_erc,
        "leap": screen.has_leap,
        "cesn_leap": screen.has_leap,
        "ma_heap": screen.has_ma_heap,
        "il_liheap": screen.has_il_liheap,
        "nc_lieap": screen.has_nc_lieap,
        "oap": screen.has_oap,
        "nccip": screen.has_nccip,
        "nc_scca": screen.has_ncscca,
        "nc_head_start": screen.has_head_start,
        "coctc": screen.has_coctc,
        "upk": screen.has_upk,
        "ssdi": screen.has_ssdi,
        "pell_grant": screen.has_pell_grant,
        "rag": screen.has_rag,
        "co_nfp": screen.has_nfp,
        "il_nfp": screen.has_nfp,
        "fatc": screen.has_fatc,
        "ma_cha": screen.has_section_8,
        "cowap": screen.has_cowap,
        "cesn_cowap": screen.has_cowap,
        "ncwap": screen.has_ncwap,
        "wa_wap": screen.has_wa_wap,
        "ubp": screen.has_ubp,
        "cesn_ubp": screen.has_ubp,
        "nfp": screen.has_nfp,
        "section_8": screen.has_section_8,
        "co_section_8": screen.has_section_8,
        "ma_section_8": screen.has_section_8,
        "aca": screen.has_aca,
        "medicaid": screen.has_medicaid,
        "nc_aca": screen.has_aca,
        "ma_aca": screen.has_aca,
        "tx_aca": screen.has_aca,
        "ma_mbta": screen.has_ma_mbta,
        "ma_snap": screen.has_snap,
        "ma_ccdf": screen.has_ccdf,
        "ma_wic": screen.has_wic,
        "ma_eaedc": screen.has_ma_eaedc,
        "ma_maeitc": screen.has_ma_maeitc,
        "ma_cfc": screen.has_ma_macfc,
        "ma_homebridge": screen.has_ma_homebridge,
        "ma_dhsp_afterschool": screen.has_ma_dhsp_afterschool,
        "ma_door_to_door": screen.has_ma_door_to_door,
        "ma_taxi_discount": screen.has_ma_taxi_discount,
        "ma_cpp": screen.has_ma_cpp,
        "ma_middle_income_rental": screen.has_ma_middle_income_rental,
        "ma_cmsp": screen.has_ma_cmsp,
        "ma_tafdc": screen.has_tanf,
        "ma_mass_health": screen.has_medicaid or screen.has_medicaid_hi,
        "ma_head_start": screen.has_head_start,
        "tx_head_start": screen.has_head_start,
        "wa_head_start": screen.has_head_start,
        "ma_csfp": screen.has_csfp,
        "ma_early_head_start": screen.has_early_head_start,
        "tx_early_head_start": screen.has_early_head_start,
        "co_andso": screen.has_co_andso,
        "cesn_andso": screen.has_co_andso,
        "co_care": screen.has_co_care,
        "cesn_care": screen.has_co_care,
        "cfhc": screen.has_cfhc,
        "shitc": screen.has_shitc,
        "nc_medicare_savings": screen.has_nc_medicare_savings,
        "tx_dart": screen.has_tx_dart,
        "ccs": screen.has_ccs,
        "tx_ccs": screen.has_ccs,
        "tx_ssdi": screen.has_ssdi,
        "wa_ssdi": screen.has_ssdi,
        "wa_csfp": screen.has_csfp,
        "wa_eitc": screen.has_eitc,
        "wa_wftc": screen.has_eitc,
        "wa_wic": screen.has_wic,
        "wa_apple_health_medicaid": screen.has_medicaid,
        "wa_apple_health_for_kids": screen.has_chp,
        "wa_hcv": screen.has_section_8,
        "ma_ssp": screen.has_ma_ssp,
        "cesn_snap": screen.has_snap,
        "cesn_tanf": screen.has_tanf,
        "cesn_wic": screen.has_wic,
        "cesn_ssi": has_ssi_or_ssi_income,
        "cesn_ssdi": screen.has_ssdi,
        "cesn_oap": screen.has_oap,
        "cesn_section_8": screen.has_section_8,
        "cesn_rtdlive": screen.has_rtdlive,
        "cesn_andcs": screen.has_andcs,
        "nc_leap": screen.has_leap,
        "nc_cccap": screen.has_ccap,
    }


def _write_current_benefits(screen, current_benefits):
    """
    Write the CurrentBenefit join table for `screen`, replacing any existing rows.

    The join table is the primary write target as of Step 5a (MFB-869):

    * New frontend — passes `current_benefits` as a list of `name_abbreviated`
      strings (e.g. ["tx_snap", "tanf"]). Each is resolved to a Program via the
      WL-scoped unique (white_label, name_abbreviated) lookup and written directly.
      Unknown names are skipped (a name the current WL doesn't offer is a no-op,
      mirroring the old map's behavior of only writing programs in this WL).
    * Old frontend (backward compat) — passes `current_benefits=None`; we derive
      the program set from the legacy `has_*` columns via
      `_benefit_map_from_has_columns()`. Removed in Step 6 (MFB-720).

    Uses select_for_update() inside a transaction to serialize concurrent PATCH
    requests on the same screen and prevent races on the delete+bulk_create. The
    screen is re-fetched inside the atomic block so the write reflects the
    post-lock committed state.
    """
    with transaction.atomic():
        screen = Screen.objects.select_for_update().get(pk=screen.pk)

        if current_benefits is None:
            # Backward-compat path: mirror legacy has_* columns into the join table.
            benefit_map = _benefit_map_from_has_columns(screen)
            program_ids_to_write = [
                program.id
                for program in Program.objects.filter(white_label=screen.white_label)
                if benefit_map.get(program.name_abbreviated, False)
            ]
        else:
            # Primary path: frontend sent explicit program names. Resolve each in
            # this screen's white label; silently drop any this WL doesn't offer.
            requested = set(current_benefits)
            program_ids_to_write = list(
                Program.objects.filter(
                    white_label=screen.white_label,
                    name_abbreviated__in=requested,
                ).values_list("id", flat=True)
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
    # Primary write target for current benefits (Step 5a / MFB-869): a list of
    # `name_abbreviated` strings the household already receives. Write-only — reads
    # still surface per-program via the eligibility "already_has" flag. When absent
    # the legacy has_* columns drive the join-table write (backward compat, removed
    # in Step 6 / MFB-720).
    current_benefits = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)

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
            "has_tanf",
            "has_wic",
            "has_snap",
            "has_sunbucks",
            "has_lifeline",
            "has_acp",
            "has_eitc",
            "has_coeitc",
            "has_nslp",
            "has_ctc",
            "has_il_eitc",
            "has_il_ctc",
            "has_il_transit_reduced_fare",
            "has_il_bap",
            "has_il_hbwd",
            "has_harris_county_rides",
            "has_medicaid",
            "has_rtdlive",
            "has_ccap",
            "has_mydenver",
            "has_chp",
            "has_ssi",
            "has_andcs",
            "has_cpcr",
            "has_cdhcs",
            "has_dpp",
            "has_ede",
            "has_erc",
            "has_leap",
            "has_il_liheap",
            "has_ma_heap",
            "has_nc_lieap",
            "has_project_cope",
            "has_cesn_heap",
            "has_oap",
            "has_nccip",
            "has_coctc",
            "has_ncscca",
            "has_upk",
            "has_ssdi",
            "has_cowap",
            "has_ncwap",
            "has_wa_wap",
            "has_ubp",
            "has_rag",
            "has_nfp",
            "has_fatc",
            "has_cfhc",
            "has_shitc",
            "has_section_8",
            "has_csfp",
            "has_ccdf",
            "has_aca",
            "has_ma_eaedc",
            "has_ma_ssp",
            "has_ma_mbta",
            "has_ma_maeitc",
            "has_ma_macfc",
            "has_ma_homebridge",
            "has_ma_dhsp_afterschool",
            "has_ma_door_to_door",
            "has_ma_taxi_discount",
            "has_ma_cpp",
            "has_ma_middle_income_rental",
            "has_ma_cmsp",
            "has_head_start",
            "has_early_head_start",
            "has_co_andso",
            "has_co_care",
            "has_employer_hi",
            "has_private_hi",
            "has_medicaid_hi",
            "has_medicare_hi",
            "has_chp_hi",
            "has_no_hi",
            "has_va",
            "has_nc_medicare_savings",
            "has_tx_dart",
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

    def create(self, validated_data):
        household_members = validated_data.pop("household_members")
        expenses = validated_data.pop("expenses")
        energy_calculator_screen = validated_data.pop("energy_calculator", None)
        # None (key absent) → old frontend, mirror from has_*; a list → new frontend.
        current_benefits = validated_data.pop("current_benefits", None)
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
        return screen

    def update(self, instance, validated_data):
        if instance.frozen:
            return instance

        household_members = validated_data.pop("household_members")
        expenses = validated_data.pop("expenses")
        energy_calculator_screen = validated_data.pop("energy_calculator", None)
        # Not a Screen column — pop before the bulk .update(). None (key absent) →
        # old frontend, mirror from has_*; a list → new frontend writes directly.
        current_benefits = validated_data.pop("current_benefits", None)

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
        return instance


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
