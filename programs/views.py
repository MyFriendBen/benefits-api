from typing import Any

from django.db.models import QuerySet
from rest_framework.request import Request

from programs.models import Program, Navigator, ProgramCategory, UrgentNeed, UrgentNeedType
from rest_framework import viewsets, mixins
from programs.federal import filter_programs_by_name, visible_to_code
from rest_framework.response import Response
from rest_framework import permissions
from programs.serializers import (
    ProgramCategorySerializer,
    NavigatorAPISerializer,
    ProgramSerializerWithCategory,
    UrgentNeedAPISerializer,
    UrgentNeedTypeSerializer,
)


class ProgramViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProgramSerializerWithCategory
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet[Program]:
        return Program.objects.filter(
            visible_to_code(self.kwargs["white_label"]),
            active=True,
            show_on_current_benefits=True,
            category__isnull=False,
        )

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # One program per name, the federal row winning (see `filter_programs_by_name`). Overridden here
        # rather than in get_queryset, which `retrieve` needs to stay a queryset.
        programs = filter_programs_by_name(
            self.filter_queryset(self.get_queryset()).select_related("white_label"), "current benefits programs"
        )
        return Response(self.get_serializer(programs, many=True).data)


class ProgramCategoryViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProgramCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet[ProgramCategory]:
        # Scope by the *programs'* white label rather than the category's own.
        # A shared category has no white label, so filtering on it would drop
        # every shared row; the programs it contains are what belong to a
        # white label (or to `federal`, which every white label sees).
        return ProgramCategory.objects.filter(
            visible_to_code(self.kwargs["white_label"], prefix="programs__"),
            programs__isnull=False,
            programs__active=True,
            programs__show_on_current_benefits=True,
        ).distinct()

    def get_serializer_context(self):
        # The serializer needs the white label to filter a shared category's
        # programs down to the ones this white label owns.
        return {**super().get_serializer_context(), "white_label": self.kwargs["white_label"]}


class NavigatorViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NavigatorAPISerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet[Navigator]:
        return Navigator.objects.filter(visible_to_code(self.kwargs["white_label"]), programs__isnull=False)


class UrgentNeedViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UrgentNeedAPISerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UrgentNeed.objects.filter(
            active=True, show_on_current_benefits=True, white_label__code=self.kwargs["white_label"]
        )


class UrgentNeedTypeViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UrgentNeedTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UrgentNeedType.objects.filter(
            urgent_needs__isnull=False,
            urgent_needs__active=True,
            urgent_needs__show_on_current_benefits=True,
            white_label__code=self.kwargs["white_label"],
        ).distinct()
