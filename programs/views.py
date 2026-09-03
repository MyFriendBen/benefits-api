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
        # Scope by the *programs'* white label rather than the category's own.
        # A shared category has no white label, so filtering on it would drop
        # every shared row; the programs it contains are what belong to a
        # white label.
        return ProgramCategory.objects.filter(
            programs__isnull=False,
            programs__active=True,
            programs__show_on_current_benefits=True,
            programs__white_label__code=self.kwargs["white_label"],
        ).distinct()

    def get_serializer_context(self):
        # The serializer needs the white label to filter a shared category's
        # programs down to the ones this white label owns.
        return {**super().get_serializer_context(), "white_label": self.kwargs["white_label"]}


class NavigatorViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NavigatorAPISerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Navigator.objects.filter(programs__isnull=False, white_label__code=self.kwargs["white_label"])


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
