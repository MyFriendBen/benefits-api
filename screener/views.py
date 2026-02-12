from typing import Optional
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from integrations.services.communications import MessageUser
from programs.programs.helpers import STATE_MEDICAID_OPTIONS
from programs.programs.policyengine.calculators.registry import all_calculators
from programs.programs.urgent_needs.base import UrgentNeedFunction
from screener.models import (
    Screen,
    HouseholdMember,
    IncomeStream,
    Expense,
    Message,
    EligibilitySnapshot,
    ProgramEligibilitySnapshot,
)
from rest_framework import viewsets, views, status, mixins
from rest_framework import permissions
from rest_framework.response import Response
from screener.serializers import (
    ScreenSerializer,
    HouseholdMemberSerializer,
    IncomeStreamSerializer,
    ExpenseSerializer,
    EligibilitySerializer,
    MessageSerializer,
    ResultsSerializer,
    WarningMessageSerializer,
)
from programs.programs.policyengine.policy_engine import calc_pe_eligibility
from programs.util import DependencyError, Dependencies
from programs.programs.urgent_needs import urgent_need_functions
from programs.models import (
    Document,
    Navigator,
    ProgramCategory,
    UrgentNeed,
    UrgentNeedType,
    Program,
    Referrer,
    WarningMessage,
    TranslationOverride,
)
from programs.programs.categories import ProgramCategoryCapCalculator, category_cap_calculators
from django.core.exceptions import ObjectDoesNotExist
from programs.programs.warnings import warning_calculators
from validations.serializers import ValidationSerializer
from .webhooks import get_web_hook
from drf_yasg.utils import swagger_auto_schema
import math
import json
from datetime import datetime, timezone
from django.conf import settings


def index(request):
    return HttpResponse("Colorado Benefits Screener API")


class ScreenViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint that allows screens to be viewed or edited.
    """

    queryset = Screen.objects.all().order_by("-submission_date")
    serializer_class = ScreenSerializer
    permission_classes = [permissions.DjangoModelPermissions]
    filterset_fields = ["agree_to_tos", "is_test"]
    paginate_by = 10
    paginate_by_param = "page_size"
    max_paginate_by = 100

    def retrieve(self, request, pk=None):
        queryset = self.queryset
        screen = get_object_or_404(queryset, uuid=pk)
        serializer = ScreenSerializer(screen)
        return Response(serializer.data)

    def update(self, request, pk=None):
        queryset = self.queryset
        user = get_object_or_404(queryset, uuid=pk)
        body = json.loads(request.body.decode())
        serializer = ScreenSerializer(user, data=body)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HouseholdMemberViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows screens to be viewed or edited.
    """

    queryset = HouseholdMember.objects.all()
    serializer_class = HouseholdMemberSerializer
    permission_classes = [permissions.DjangoModelPermissions]
    filterset_fields = ["has_income"]


class IncomeStreamViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows income streams to be viewed or edited.
    """

    queryset = IncomeStream.objects.all()
    serializer_class = IncomeStreamSerializer
    permission_classes = [permissions.DjangoModelPermissions]
    filterset_fields = ["screen"]


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows expenses to be viewed or edited.
    """

    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.DjangoModelPermissions]
    filterset_fields = ["screen"]


class EligibilityView(views.APIView):
    def get(self, request, id):
        data = eligibility_results(id)
        results = EligibilitySerializer(data, many=True).data
        return Response(results)


class EligibilityTranslationView(views.APIView):
    @swagger_auto_schema(responses={200: ResultsSerializer()})
    def get(self, request, id):
        screen = Screen.objects.prefetch_related(
            "household_members",
            "household_members__income_streams",
            "household_members__insurance",
            "household_members__energy_calculator",
            "expenses",
            "energy_calculator",
        ).get(uuid=id)

        is_admin = request.query_params.get("admin")
        results = all_results(screen, is_admin=is_admin)

        if screen.submission_date is None:
            screen.submission_date = datetime.now(timezone.utc)

        hook = get_web_hook(screen)
        if hook is not None:
            hook.send(screen, results)

        screen.completed = True
        screen.save()

        return Response(results)


class MessageViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that logs messages sent.
    """

    queryset = Message.objects.all().order_by("-sent")
    serializer_class = MessageSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    def create(self, request):
        body = json.loads(request.body.decode())
        screen = Screen.objects.get(uuid=body["screen"])

        message = MessageUser(screen, screen.get_language_code())
        if "email" in body:
            message.email(body["email"], send_tests=True)
        if "phone" in body:
            message.text("+1" + body["phone"], send_tests=True)

        return Response({}, status=status.HTTP_201_CREATED)


def all_results(screen: Screen, batch=False, is_admin: bool = False):
    eligibility, missing_programs, categories, _pe_data = eligibility_results(screen, batch)
    urgent_needs = urgent_need_results(screen, eligibility)
    validations = ValidationSerializer(screen.validations.all(), many=True).data

    results = {
        "programs": eligibility,
        "urgent_needs": urgent_needs,
        "screen_id": screen.id,
        "default_language": screen.request_language_code,
        "missing_programs": missing_programs,
        "validations": validations,
        "program_categories": categories,
        "pe_data": _pe_data,
    }

    if not is_admin:
        results.pop("pe_data", None)

    return results


def translations_prefetch_name(prefix: str, fields):
    return [f"{prefix}{f}__translations" for f in fields]


def eligibility_results(screen: Screen, batch=False):
    try:
        referrer = Referrer.objects.prefetch_related("remove_programs", "primary_navigators").get(
            referrer_code=screen.referrer_code
        )
    except ObjectDoesNotExist:
        referrer = None

    excluded_programs = []
    if referrer is not None:
        excluded_programs = [p.id for p in referrer.remove_programs.all()]

    all_programs = (
        Program.objects.filter(active=True, category__isnull=False, white_label=screen.white_label)
        .prefetch_related(
            "legal_status_required",
            "year",
            "required_programs",
            "excludes_programs",
            *translations_prefetch_name("", Program.objects.translated_fields),
            "program_navigators",
            "program_navigators__navigator",
            "program_navigators__navigator__counties",
            "program_navigators__navigator__languages",
            *translations_prefetch_name("program_navigators__navigator__", Navigator.objects.translated_fields),
            "documents",
            *translations_prefetch_name("documents__", Document.objects.translated_fields),
            "warning_messages",
            "warning_messages__counties",
            "warning_messages__legal_statuses",
            *translations_prefetch_name("warning_messages__", WarningMessage.objects.translated_fields),
            "translation_overrides",
            "translation_overrides__counties",
            *translations_prefetch_name("translation_overrides__", TranslationOverride.objects.translated_fields),
            "category",
            *translations_prefetch_name("category__", ProgramCategory.objects.translated_fields),
        )
        .exclude(id__in=excluded_programs)
    )
    data = []

    try:
        previous_snapshot = (
            EligibilitySnapshot.objects.prefetch_related("program_snapshots")
            .filter(is_batch=False, screen=screen, had_error=False)
            .latest("submission_date")
        )
        previous_results = None if previous_snapshot is None else previous_snapshot.program_snapshots.all()
    except ObjectDoesNotExist:
        previous_snapshot = None
    snapshot = EligibilitySnapshot.objects.create(screen=screen, is_batch=batch, had_error=True)

    missing_dependencies = screen.missing_fields()

    pe_calculators = {}
    for calculator_name, Calculator in all_calculators.items():
        program: Optional[Program] = None
        for p in all_programs:
            if calculator_name == p.name_abbreviated:
                program = p

        if program is not None:
            pe_calculators[calculator_name] = Calculator(screen, program, missing_dependencies)

    result = calc_pe_eligibility(screen, pe_calculators)
    pe_eligibility = result["eligibility"]
    pe_data = result["_pe_data"]

    pe_programs = pe_calculators.keys()

    def sort_first(program):
        calc_order = (
            "tanf",
            "ssi",
            "nslp",
            "leap",
            "chp",
            *STATE_MEDICAID_OPTIONS,
            "emergency_medicaid",
            "wic",
            "andcs",
            "co_energy_calculator_leap",
            "co_energy_calculator_eoc",
            "co_energy_calculator_cowap",
            "co_energy_calculator_ubp",
            "co_energy_calculator_care",
        )

        if program.name_abbreviated not in calc_order:
            return len(calc_order)

        return calc_order.index(program.name_abbreviated)

    missing_programs = False

    # make certain benifits calculate first so that they can be used in other benefits
    all_programs = sorted(all_programs, key=sort_first)

    program_snapshots = []

    program_eligibility = {}

    for program in all_programs:
        skip = False
        if program.name_abbreviated not in pe_programs and program.active:
            try:
                eligibility = program.eligibility(screen, program_eligibility, missing_dependencies)
            except DependencyError:
                missing_programs = True
                continue
        elif program.active:
            if program.name_abbreviated not in pe_eligibility:
                missing_programs = True
                continue

            eligibility = pe_eligibility[program.name_abbreviated]

        program_eligibility[program.name_abbreviated] = eligibility

        if previous_snapshot is not None:
            new = True
            for previous_snapshot in previous_results:
                if (
                    previous_snapshot.name_abbreviated == program.name_abbreviated
                    and eligibility.eligible == previous_snapshot.eligible
                ):
                    new = False
        else:
            new = False

        warnings = []
        navigators = []

        # don't calculate navigator and warnings for ineligible programs
        if eligibility.eligible:
            # Get navigators through ordered relationship (automatically sorted by order field)
            # program_navigators uses ProgramNavigator through table with Meta.ordering
            program_navigators = program.program_navigators.all()
            all_navigators = [pn.navigator for pn in program_navigators]

            county_navigators = []
            for nav in all_navigators:
                counties = nav.counties.all()
                if len(counties) == 0 or (
                    screen.county is not None and any(screen.county in county.name for county in counties)
                ):
                    county_navigators.append(nav)

            if referrer is None:
                navigators = county_navigators
            else:
                primary_navigators = referrer.primary_navigators.all()
                referrer_navigators = [nav for nav in primary_navigators if nav in county_navigators]
                if len(referrer_navigators) == 0:
                    navigators = county_navigators
                else:
                    navigators = referrer_navigators

            for warning in program.warning_messages.all():
                if warning.calculator not in warning_calculators:
                    raise Exception(f"{warning.calculator} is not a valid calculator name")

                warning_calculator = warning_calculators[warning.calculator](
                    screen, warning, eligibility, missing_dependencies
                )

                if warning_calculator.calc():
                    warnings.append(WarningMessageSerializer(warning).data)

        if not skip and program.active:
            legal_status = [status.status for status in program.legal_status_required.all()]
            program_snapshots.append(
                ProgramEligibilitySnapshot(
                    eligibility_snapshot=snapshot,
                    name=program.name.text,
                    name_abbreviated=program.name_abbreviated,
                    value_type=program.value_type.text,
                    estimated_value=eligibility.value,
                    estimated_delivery_time=program.estimated_delivery_time.text,
                    estimated_application_time=program.estimated_application_time.text,
                    eligible=eligibility.eligible,
                    failed_tests=json.dumps(eligibility.fail_messages),
                    passed_tests=json.dumps(eligibility.pass_messages),
                    new=new,
                )
            )
            program_translations = GetProgramTranslation(screen, program, missing_dependencies)

            member_data = []
            for member_eligibility in eligibility.eligible_members:
                member_data.append(
                    {
                        "frontend_id": str(member_eligibility.member.frontend_id),
                        "eligible": member_eligibility.eligible,
                        "value": member_eligibility.value,
                        "already_has": member_eligibility.member.has_benefit(program.name_abbreviated),
                    }
                )

            data.append(
                {
                    "program_id": program.id,
                    "name": program_translations.get_translation("name"),
                    "name_abbreviated": program.name_abbreviated,
                    "external_name": program.external_name,
                    "estimated_value": eligibility.value,
                    "household_value": eligibility.household_value,
                    "estimated_delivery_time": program_translations.get_translation("estimated_delivery_time"),
                    "estimated_application_time": program_translations.get_translation("estimated_application_time"),
                    "description_short": program_translations.get_translation("description_short"),
                    "short_name": program.name_abbreviated,
                    "description": program_translations.get_translation("description"),
                    "value_type": program_translations.get_translation("value_type"),
                    "learn_more_link": program_translations.get_translation("learn_more_link"),
                    "apply_button_link": program_translations.get_translation("apply_button_link"),
                    "apply_button_description": program_translations.get_translation("apply_button_description"),
                    "legal_status_required": legal_status,
                    "estimated_value_override": program_translations.get_translation("estimated_value"),
                    "eligible": eligibility.eligible,
                    "members": member_data,
                    "failed_tests": eligibility.fail_messages,
                    "passed_tests": eligibility.pass_messages,
                    "navigators": [serialized_navigator(navigator) for navigator in navigators],
                    "already_has": screen.has_benefit(program.name_abbreviated),
                    "new": new,
                    "low_confidence": program.low_confidence,
                    "documents": [serialized_document(document) for document in program.documents.all()],
                    "warning_messages": warnings,
                    "required_programs": [p.id for p in program.required_programs.all()],
                    "excludes_programs": [p.id for p in program.excludes_programs.all()],
                    "value_format": program.value_format,
                }
            )

    category_map = {}
    program_ids = [p["program_id"] for p in data]
    for program in all_programs:
        if program.id not in program_ids:
            continue

        category = program.category
        if category.id in category_map:
            category_map[category.id]["programs"].append(program.id)
            continue

        CategoryCalculator = ProgramCategoryCapCalculator
        if category.calculator is not None and category.calculator != "":
            CategoryCalculator = category_cap_calculators[category.calculator]

        calculator = CategoryCalculator(program_eligibility)

        caps = []
        for cap in calculator.caps():
            caps.append({"programs": cap.programs, "household_cap": cap.household_cap, "member_caps": cap.member_caps})

        category_map[category.id] = {
            "external_name": category.external_name,
            "icon": category.icon_name,
            "name": default_message(category.name),
            "description": default_message(category.description),
            "caps": caps,
            "tax_category": category.tax_category,
            "priority": category.priority,
            "programs": [program.id],
        }
    categories = list(category_map.values())

    ProgramEligibilitySnapshot.objects.bulk_create(program_snapshots)
    snapshot.had_error = False
    snapshot.save()

    eligible_programs = []
    for program in data:
        clean_program = program
        clean_program["estimated_value"] = math.trunc(clean_program["estimated_value"])
        eligible_programs.append(clean_program)

    return eligible_programs, missing_programs, categories, pe_data


class GetProgramTranslation:
    def __init__(self, screen: Screen, program: Program, missing_dependencies: Dependencies):
        self.screen = screen
        self.program = program
        self.missing_dependencies = missing_dependencies

    def get_translation(self, field: str):
        return default_message(self.program.get_translation(self.screen, self.missing_dependencies, field))


def default_message(translation):
    translation.set_current_language(settings.LANGUAGE_CODE)
    d = {"default_message": translation.text, "label": translation.label}
    return d


def serialized_navigator(navigator):
    phone_number = str(navigator.phone_number) if navigator.phone_number else None
    langs = [lang.code for lang in navigator.languages.all()]
    return {
        "id": navigator.id,
        "name": default_message(navigator.name),
        "phone_number": phone_number,
        "email": default_message(navigator.email),
        "assistance_link": default_message(navigator.assistance_link),
        "description": default_message(navigator.description),
        "languages": langs,
    }


def serialized_document(document):
    return {
        "text": default_message(document.text),
        "link_url": default_message(document.link_url),
        "link_text": default_message(document.link_text),
    }


def urgent_need_results(screen: Screen, data):
    """
    These keys are used to determine which urgent needs
    programs to show based on the selected options in the
    immediate needs page.
    """
    possible_needs = {
        "food": screen.needs_food,
        "baby supplies": screen.needs_baby_supplies,
        "housing": screen.needs_housing_help,
        "mental health": screen.needs_mental_health_help,
        "child dev": screen.needs_child_dev_help,
        "funeral": screen.needs_funeral_help,
        "family planning": screen.needs_family_planning_help,
        "job resources": screen.needs_job_resources,
        "dental care": screen.needs_dental_care,
        "legal services": screen.needs_legal_services,
        "veteran services": screen.needs_veteran_services,
        "savings": screen.needs_college_savings,
    }

    missing_dependencies = screen.missing_fields()

    list_of_needs = []
    for need, has_need in possible_needs.items():
        if has_need:
            list_of_needs.append(need)

    urgent_need_resources = (
        UrgentNeed.objects.prefetch_related(
            "functions", "counties", *translations_prefetch_name("", UrgentNeed.objects.translated_fields)
        )
        .filter(
            type_short__name__in=list_of_needs, category_type__isnull=False, active=True, white_label=screen.white_label
        )
        .distinct()
    )

    eligible_urgent_needs = []
    for need in urgent_need_resources:
        eligible = True

        calculators = [urgent_need_functions[f.name] for f in need.functions.all()]

        if len(calculators) == 0:
            calculators = [UrgentNeedFunction]

        for Calculator in calculators:
            calculator = Calculator(screen, need, missing_dependencies, data)

            if not calculator.calc():
                eligible = False
        if eligible:
            phone_number = str(need.phone_number) if need.phone_number else None
            need_data = {
                "name": default_message(need.name),
                "description": default_message(need.description),
                "link": default_message(need.link),
                "category_type": default_message(need.category_type.name),
                "icon": need.category_type.icon_name,
                "warning": default_message(need.warning),
                "phone_number": phone_number,
                "notification_message": (
                    default_message(need.notification_message) if need.notification_message else None
                ),
            }
            eligible_urgent_needs.append(need_data)

    return eligible_urgent_needs
