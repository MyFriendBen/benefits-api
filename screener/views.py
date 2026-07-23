import hashlib
import requests
from typing import Optional
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from integrations.clients.rewiring_america import RewiringAmericaClient
from integrations.clients.google_places import GooglePlacesClient
from integrations.services.communications import MessageUser
from programs.programs.policyengine import versions as pe_versions
from programs.models import Referrer
from programs.programs.helpers import STATE_MEDICAID_OPTIONS
from programs.programs.policyengine.calculators.registry import all_calculators
from programs.programs.urgent_needs.base import UrgentNeedFunction
from django.db import transaction
from screener.models import (
    Screen,
    HouseholdMember,
    IncomeStream,
    Expense,
    Message,
    CurrentBenefit,
    EligibilitySnapshot,
    ProgramEligibilitySnapshot,
)
from rest_framework import viewsets, views, status, mixins, throttling
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
    NPSScoreSerializer,
    NPSScoreReasonSerializer,
    RemImpactSerializer,
    CurrentBenefitToggleSerializer,
)
from programs.programs.policyengine.policy_engine import calc_pe_eligibility
from integrations.external_api_status import track_external_api_failures, get_external_api_failures
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
from programs.serializers import HasBenefitsProgramSerializer
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

    queryset = (
        Screen.objects.all()
        .select_related("user", "white_label")
        .prefetch_related(
            "current_benefits__program",
            "household_members__income_streams",
            "household_members__insurance",
            "household_members__energy_calculator",
            "expenses",
            "energy_calculator",
        )
        .order_by("-submission_date")
    )
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


class ScreenCurrentBenefitsView(views.APIView):
    """
    PATCH /api/screens/<uuid>/current-benefits/

    Lightweight single-benefit toggle for the results-page "already have this"
    control (MFB-871). Adds or removes exactly one CurrentBenefit row instead of
    revalidating and rewriting the whole screen the way the Screen PATCH path does.
    Idempotent — repeating the same payload is a no-op:

        body: {"name_abbreviated": "snap", "has": true}   # ensure the row exists
        body: {"name_abbreviated": "snap", "has": false}  # ensure the row is absent

    `name_abbreviated` is a program name resolved against the screen's white label;
    an unknown name (or one offered only by another white label) is a 404, so a
    toggle can't write a cross-WL program. Returns the updated current-benefits
    list as {"current_benefits": [...sorted name_abbreviated...]}.

    Unlike the bulk write path (`_write_current_benefits`), this does NOT OR in
    derived benefits (e.g. SSI implied by an sSI income stream) — it's a targeted
    single-row operation. The next full Screen PATCH reapplies those compound rules.
    """

    # Same gate as the Screen PATCH path: DjangoModelPermissions maps PATCH to
    # `screener.change_screen`, so whoever may edit the screen may toggle its
    # benefits. The queryset is required for DjangoModelPermissions to resolve
    # the model the permission is checked against.
    permission_classes = [permissions.DjangoModelPermissions]
    queryset = Screen.objects.all()

    def patch(self, request, screen_uuid):
        serializer = CurrentBenefitToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name_abbreviated = serializer.validated_data["name_abbreviated"]
        has = serializer.validated_data["has"]

        # Lock the screen for the read-modify-write so concurrent toggles (or a
        # toggle racing a Screen PATCH) can't interleave on the join table. The
        # locked fetch also serves as the screen-missing 404 (an empty
        # transaction just rolls back), and the program lookup resolves against
        # the locked screen's white label rather than a pre-lock read.
        with transaction.atomic():
            screen = get_object_or_404(Screen.objects.select_for_update(), uuid=screen_uuid)
            program = get_object_or_404(Program, white_label=screen.white_label, name_abbreviated=name_abbreviated)
            if has:
                CurrentBenefit.objects.get_or_create(screen=screen, program=program)
            else:
                CurrentBenefit.objects.filter(screen=screen, program=program).delete()
            current_benefits = sorted(
                CurrentBenefit.objects.filter(screen=screen).values_list("program__name_abbreviated", flat=True)
            )

        return Response({"current_benefits": current_benefits})


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
        """
        A ?pe_version= override is a test-only preview of a specific PolicyEngine
        version. We validate it (rejecting typos rather than silently testing the wrong
        version) and promote the screen to a test screen so the resulting snapshot is
        excluded from exports/marts; the referrer webhook is also skipped for test
        screens (see below). The flip must happen before all_results(), which writes the
        EligibilitySnapshot — that ordering is locked by
        screener/tests/test_pe_version_override.py.
        """
        screen = (
            Screen.objects.select_related("white_label")
            .prefetch_related(
                "household_members",
                "household_members__income_streams",
                "household_members__insurance",
                "household_members__energy_calculator",
                "expenses",
                "energy_calculator",
                "current_benefits__program",
            )
            .get(uuid=id)
        )

        is_admin = request.query_params.get("admin")

        pe_version = request.query_params.get("pe_version")
        if pe_version:
            if not pe_versions.is_valid_override(pe_version):
                return Response(
                    {"pe_version": "must be a version number like '1.715.2', or 'current'/'frontier'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Flip before the calc so the snapshot is born under is_test (see docstring).
            if not screen.is_test:
                screen.is_test = True
                screen.save(update_fields=["is_test"])

        results = all_results(screen, is_admin=is_admin, pe_version=pe_version)

        if screen.submission_date is None:
            screen.submission_date = datetime.now(timezone.utc)

        # Never deliver a test screen's results to a partner's webhook — covers the
        # ?pe_version= preview (which flips is_test above) and any other test screen.
        if not screen.is_test:
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
            message.text(body["phone"], send_tests=True)

        return Response({}, status=status.HTTP_201_CREATED)


def all_results(screen: Screen, batch=False, is_admin: bool = False, pe_version: Optional[str] = None):
    # Track any external-API failure (e.g. PolicyEngine) that occurs while computing
    # this screen's results, so we can tell the frontend results may be incomplete.
    with track_external_api_failures():
        eligibility, missing_programs, categories, _pe_data = eligibility_results(screen, batch, pe_version=pe_version)
        urgent_needs = urgent_need_results(screen, eligibility)
        external_api_failures = get_external_api_failures()
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
        # Unlike pe_data (admin-only, popped below), this is sent to all users so the
        # results page can show a "some results may be unavailable" banner.
        "external_api_failures": external_api_failures,
    }

    if not is_admin:
        results.pop("pe_data", None)

    return results


def translations_prefetch_name(prefix: str, fields):
    return [f"{prefix}{f}__translations" for f in fields]


def filter_by_county(navigators: list, county: Optional[str]) -> list:
    result = []
    for nav in navigators:
        counties = nav.counties.all()
        if len(counties) == 0 or (county is not None and any(county in c.name for c in counties)):
            result.append(nav)
    return result


def filter_by_required_programs_eligibility(navigators: list, program_eligibility: dict) -> list:
    result = []
    for nav in navigators:
        required = nav.eligibility_programs.all()
        if not required or all(
            getattr(program_eligibility.get(p.name_abbreviated), "eligible", False) for p in required
        ):
            result.append(nav)
    return result


def referrer_prioritization(eligibility_filtered: list, primary_navigators: list) -> list:
    if not primary_navigators:
        return eligibility_filtered
    referrer_navigators = [nav for nav in primary_navigators if nav in eligibility_filtered]
    return referrer_navigators if referrer_navigators else eligibility_filtered


def update_navigators(
    eligible_program_data: list,
    program_eligibility: dict,
    data: list,
    screen_county: Optional[str],
    referrer,
) -> None:
    primary_navs = list(referrer.primary_navigators.all()) if referrer is not None else []
    for program, idx in eligible_program_data:
        all_navigators = [pn.navigator for pn in program.program_navigators.all()]
        county_filtered = filter_by_county(all_navigators, screen_county)
        eligibility_filtered = filter_by_required_programs_eligibility(county_filtered, program_eligibility)
        navigators = referrer_prioritization(eligibility_filtered, primary_navs)
        data[idx]["navigators"] = [serialized_navigator(navigator) for navigator in navigators]


def eligibility_results(screen: Screen, batch=False, pe_version: Optional[str] = None):
    try:
        referrer = Referrer.objects.prefetch_related("remove_programs", "primary_navigators").get(
            white_label=screen.white_label,
            referrer_code=screen.referrer_code,
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
            "program_navigators__navigator__eligibility_programs",
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

    program_by_abbr = {p.name_abbreviated: p for p in all_programs}
    pe_calculators = {}
    for calculator_name, Calculator in all_calculators.items():
        program = program_by_abbr.get(calculator_name)

        if program is not None:
            pe_calculators[calculator_name] = Calculator(screen, program, missing_dependencies)

    result = calc_pe_eligibility(screen, pe_calculators, pe_version=pe_version)
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
            "cesn_leap",
            "cesn_eoc",
            "cesn_cowap",
            "cesn_care",
        )

        if program.name_abbreviated not in calc_order:
            return len(calc_order)

        return calc_order.index(program.name_abbreviated)

    missing_programs = False

    # make certain benifits calculate first so that they can be used in other benefits
    all_programs = sorted(all_programs, key=sort_first)

    program_snapshots = []
    eligible_program_data: list[tuple] = []  # (program, data_index) for post-loop navigator pass

    program_eligibility = {}

    for program in all_programs:
        # Tracking-only programs (has_calculator=False) and disabled programs
        # (active=False) are skipped before any eligibility lookup. Without this
        # guard, the loop would fall through and reuse the previous iteration's
        # `eligibility` value when writing program_snapshots.
        if not (program.active and program.has_calculator):
            continue
        skip = False
        if program.name_abbreviated not in pe_programs:
            try:
                eligibility = program.eligibility(screen, program_eligibility, missing_dependencies)
            except DependencyError:
                missing_programs = True
                continue
        else:
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

        # don't calculate warnings for ineligible programs
        if eligibility.eligible:
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
                        "already_has": member_eligibility.member.has_insurance(program.name_abbreviated),
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
                    "learn_more_link": program_translations.get_translation("learn_more_link"),
                    "apply_button_link": program_translations.get_translation("apply_button_link"),
                    "apply_button_description": program_translations.get_translation("apply_button_description"),
                    "legal_status_required": legal_status,
                    "estimated_value_override": program_translations.get_translation("estimated_value"),
                    "eligible": eligibility.eligible,
                    "members": member_data,
                    "failed_tests": eligibility.fail_messages,
                    "passed_tests": eligibility.pass_messages,
                    "navigators": [],  # populated in second pass once program_eligibility is complete
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

            if eligibility.eligible:
                eligible_program_data.append((program, len(data) - 1))

    update_navigators(eligible_program_data, program_eligibility, data, screen.county, referrer)

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
        "disability resources": screen.needs_disability_resources,
        "aging resources": screen.needs_aging_resources,
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


class HashedIPAnonRateThrottle(throttling.AnonRateThrottle):
    """AnonRateThrottle that keys on a hashed IP so raw IPs aren't stored."""

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        if ident is None:
            return None
        hashed = hashlib.sha256(ident.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": hashed}


class RemRateThrottle(HashedIPAnonRateThrottle):
    scope = "rem"


class NPSRateThrottle(HashedIPAnonRateThrottle):
    scope = "nps"


class PlacesRateThrottle(HashedIPAnonRateThrottle):
    scope = "places"


class NPSScoreView(views.APIView):
    """
    API endpoint for submitting NPS (Net Promoter Score) feedback.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [NPSRateThrottle]

    def post(self, request, screen_uuid):
        # Inject UUID from URL into request data
        data = {**request.data, "uuid": str(screen_uuid)}
        serializer = NPSScoreSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, screen_uuid):
        # Inject UUID from URL into request data
        data = {**request.data, "uuid": str(screen_uuid)}
        serializer = NPSScoreReasonSerializer(data=data)
        if serializer.is_valid():
            uuid = serializer.validated_data.pop("uuid")
            nps_score = serializer.get_nps_score(uuid)
            serializer.update(nps_score, serializer.validated_data)
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HasBenefitsProgramsView(views.APIView):
    """Returns programs shown in the 'already has benefits' screener step.

    Response is a flat, unsorted list. Each program includes its `category`.
    Callers are responsible for sorting and grouping by the user-facing
    `default_message` of `name` and `category` (sorting server-side would order
    by translation label, which is the internal i18n key, not the display text).

    Response shape:
        [
            {
                "name_abbreviated": "SNAP",
                "name": {"label": "...", "default_message": "Supplemental Nutrition Assistance Program"},
                "website_description": {"label": "...", "default_message": "Monthly food assistance for groceries"},
                "category": {"label": "...", "default_message": "Food and Nutrition"}
            },
            ...
        ]
    """

    permission_classes = [permissions.DjangoModelPermissions]
    queryset = Program.objects.none()  # Required for DjangoModelPermissions

    def get(self, request, white_label):
        programs = Program.objects.filter(
            active=True,
            show_in_has_benefits_step=True,
            white_label__code=white_label,
        ).select_related("name", "website_description", "category__name")

        serializer = HasBenefitsProgramSerializer(programs, many=True)
        return Response(serializer.data)


class ReferralSourcesView(views.APIView):
    """Returns referral source options for the screener dropdown, grouped by type.

    Response shape:
        {
            "generic": {"friend": "Friend / Family", ...},
            "partners": {"bia": "Benefits in Action", ...}
        }

    Both groups are sorted alphabetically by display name.
    """

    permission_classes = [permissions.DjangoModelPermissions]
    queryset = Referrer.objects.none()  # Required for DjangoModelPermissions

    def get(self, request, white_label):
        referrers = Referrer.objects.filter(
            white_label__code=white_label,
            show_in_dropdown=True,
        ).order_by("name")

        generic = {}
        partners = {}
        for ref in referrers:
            if ref.is_partner:
                partners[ref.referrer_code] = ref.name
            else:
                generic[ref.referrer_code] = ref.name

        return Response({"generic": generic, "partners": partners})


class RemImpactView(views.APIView):
    """
    Proxies a request to the Rewiring America REM /api/v1/rem/address endpoint
    and returns only the total cost delta (bill impact) and total emissions delta
    that the frontend needs to render the Calculate Impact results view.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [RemRateThrottle]

    def get(self, request, **_kwargs) -> Response:
        upgrade = request.query_params.get("upgrade")
        address = request.query_params.get("address")
        heating_fuel = request.query_params.get("heating_fuel")
        water_heater_fuel = request.query_params.get("water_heater_fuel") or None

        if not all([upgrade, address, heating_fuel]):
            return Response(
                {"error": "upgrade, address, and heating_fuel are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client = RewiringAmericaClient()
            raw = client.fetch_rem_impact(upgrade, address, heating_fuel, water_heater_fuel)
        except requests.HTTPError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = e.response.text
            # REM returns 400 with a typed detail dict for address-level errors the frontend
            # can surface meaningfully. Known types (per docs.rewiringamerica.org/api/
            # residential-electrification-model#get-by-address):
            #   multifamily_not_supported, building_type_not_supported,
            #   address_not_parsable, building_not_supported
            # Return 422 so the frontend can distinguish these from backend/network failures.
            _ADDRESS_ERROR_TYPES = {
                "multifamily_not_supported",
                "building_type_not_supported",
                "address_not_parsable",
                "building_not_supported",
            }
            nested = detail.get("detail") if isinstance(detail, dict) else None
            if e.response.status_code < 500 and isinstance(nested, dict) and nested.get("type") in _ADDRESS_ERROR_TYPES:
                return Response(
                    {"error": "address_not_supported", "detail": detail},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            return Response(
                {"error": f"Rewiring America API error: {e.response.status_code}", "detail": detail},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except requests.RequestException as e:
            return Response(
                {"error": "Rewiring America request failed.", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as e:
            return Response(
                {"error": "Rewiring America returned an invalid response.", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        serializer = RemImpactSerializer(raw)
        return Response(serializer.data)


class PlacesAutocompleteView(views.APIView):
    """
    Proxies address autocomplete requests to the Google Places API,
    keeping the API key server-side. Returns US street address predictions
    restricted to street-level addresses.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [PlacesRateThrottle]

    def get(self, request, **_kwargs) -> Response:
        input_text = request.query_params.get("input", "").strip()

        if not input_text:
            return Response([], status=status.HTTP_200_OK)

        try:
            client = GooglePlacesClient()
            predictions = client.autocomplete_address(input_text)
        except requests.HTTPError as e:
            http_status = e.response.status_code if e.response is not None else "unknown"
            return Response(
                {"error": f"Google Places API error: {http_status}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except requests.RequestException as e:
            return Response(
                {"error": "Google Places request failed.", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(predictions)
