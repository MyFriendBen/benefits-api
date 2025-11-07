from sentry_sdk import capture_exception
from authentication.models import User
from integrations.services.cms_integration import get_cms_integration
from integrations.services.communications import MessageUser
from screener.models import Screen
from rest_framework import viewsets, permissions, mixins
from rest_framework.response import Response
from authentication.serializers import UserSerializer, UserOffersSerializer
import logging

logger = logging.getLogger(__name__)


class UserViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().order_by("-email_or_cell")
    serializer_class = UserSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    def update(self, request, pk=None):
        if pk is None:
            return Response("Must have an associated screen", status=400)

        screen: Screen = Screen.objects.get(uuid=pk)
        user = screen.user
        serializer = UserOffersSerializer(user, data=request.data) if user else UserSerializer(data=request.data)

        if serializer.is_valid():
            screen.user = serializer.save()
            screen.save()
            user: User = screen.user

            try:
                Integration = get_cms_integration(screen.white_label)
                integration = Integration(user, screen)
                message = MessageUser(screen, screen.get_language_code())

                if user and user.external_id:
                    logger.info(f"Updating existing contact for user {user.id}")
                    integration.update()
                elif integration.should_add():
                    logger.info(f"Adding new contact for user {user.id}")
                    external_id = integration.add()

                    # don't delete the user if there is an error sending a text/email
                    try:
                        if screen.user.email is not None:
                            message.email(screen.user.email)
                        if screen.user.cell is not None:
                            message.text(str(screen.user.cell))
                    except Exception as e:
                        capture_exception(e, level="error")
                    finally:
                        user.anonomize(external_id)
                else:
                    logger.info(f"Should not add user {user.id} to CMS")
                    if not user.is_staff and not user.is_superuser:
                        # you should not be able to create a user with an admin email,
                        # but just incase you can this prevents admin acounts from being deleted
                        user.delete()

            except Exception as e:
                logger.error(f"Error in user update workflow: {str(e)}", exc_info=True)
                if not user.is_staff and not user.is_superuser:
                    user.delete()
                raise e

            return Response(status=204)
        return Response(serializer.errors, status=400)
