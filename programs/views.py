from programs.models import Program, Navigator, ProgramCategory, UrgentNeed, UrgentNeedType
from rest_framework import viewsets, mixins
from rest_framework import permissions
from programs.serializers import (
    ProgramCategorySerializer,
    NavigatorAPISerializer,
    ProgramSerializerWithCategory,
    UrgentNeedAPISerializer,
    UrgentNeedTypeSerializer,
)
from django.db.models import OuterRef, Subquery, Value, IntegerField
from django.db.models.functions import Coalesce


class ProgramViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProgramSerializerWithCategory
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Program.objects.filter(
            active=True,
            show_on_current_benefits=True,
            category__isnull=False,
            white_label__code=self.kwargs["white_label"],
        )


class ProgramCategoryViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProgramCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProgramCategory.objects.filter(
            programs__isnull=False,
            programs__active=True,
            programs__show_on_current_benefits=True,
            white_label__code=self.kwargs["white_label"],
        ).distinct()


class NavigatorViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NavigatorAPISerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        white_label = self.kwargs["white_label"]

        # Through model for sorted relation
        Through = Program.navigators_sorted.through

        # Minimal sort_value across any Program within the same white_label
        sorted_link = (
            Through.objects.filter(navigator_id=OuterRef("pk"), program__white_label__code=white_label)
            .order_by("sort_value")
            .values("sort_value")[:1]
        )

        qs = (
            Navigator.objects.filter(programs_sorted__white_label__code=white_label, white_label__code=white_label)
            .annotate(effective_order=Subquery(sorted_link, output_field=IntegerField()))
            .annotate(order_key=Coalesce("effective_order", Value(1_000_000)))
            .order_by("order_key", "id")
            .distinct()
        )
        return qs


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
