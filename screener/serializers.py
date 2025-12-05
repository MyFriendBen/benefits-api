from datetime import datetime, timedelta
from programs.models import WarningMessage
from screener.models import (
    EnergyCalculatorMember,
    EnergyCalculatorScreen,
    Screen,
    HouseholdMember,
    IncomeStream,
    Expense,
    Message,
    Insurance,
    WhiteLabel,
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

        birth_year_month = datetime(year=birth_year, month=birth_month, day=1)

        # add a day for timezones
        today = datetime.now() + timedelta(days=1)

        if birth_year_month > today:
            raise serializers.ValidationError("Birth year and month are in the future")

        data["birth_year_month"] = birth_year_month.date()

        if "age" not in data or data["age"] is None:
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
        )
        read_only_fields = ("screen", "id")


class ScreenSerializer(serializers.ModelSerializer):
    household_members = HouseholdMemberSerializer(many=True)
    expenses = ExpenseSerializer(many=True)
    user = UserOffersSerializer(read_only=True)
    white_label = serializers.CharField(source="white_label.code")
    energy_calculator = EnergyCalculatorScreenSerializer(required=False, allow_null=True)

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
            "has_medicaid",
            "has_rtdlive",
            "has_cccap",
            "has_mydenver",
            "has_chp",
            "has_ssi",
            "has_andcs",
            "has_chs",
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
            "has_head_start",
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
        return screen

    def update(self, instance, validated_data):
        if instance.frozen:
            return instance

        household_members = validated_data.pop("household_members")
        expenses = validated_data.pop("expenses")
        energy_calculator_screen = validated_data.pop("energy_calculator", None)

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
    value_type = TranslationSerializer()
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
