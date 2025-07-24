from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r"programs/(?P<white_label>.+)", views.ProgramViewSet, basename="Programs")
router.register(r"program_categories/(?P<white_label>.+)", views.ProgramCategoryViewSet, basename="Program Categories")
router.register(r"navigators/(?P<white_label>.+)", views.NavigatorViewSet, basename="Navigator")
router.register(r"urgent_needs/(?P<white_label>.+)", views.UrgentNeedViewSet, basename="Urgent Need")
router.register(r"urgent_need_types/(?P<white_label>.+)", views.UrgentNeedTypeViewSet, basename="Urgent Need Types")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [path("", include(router.urls))]
