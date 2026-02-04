from django.shortcuts import get_object_or_404
from configuration.models import Configuration
from configuration.serializers import ConfigurationSerializer
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import viewsets


class ConfigurationView(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows configurations to be viewed.
    """

    serializer_class = ConfigurationSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        return Configuration.objects.select_related("white_label").filter(
            active=True, white_label__code=self.kwargs["white_label"]
        )

    def retrieve(self, request, pk=None):
        configuration = get_object_or_404(self.get_queryset(), name=pk)
        serializer = ConfigurationSerializer(configuration)
        return Response(serializer.data)
