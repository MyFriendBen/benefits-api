from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r"screens", views.ScreenViewSet)
router.register(r"messages", views.MessageViewSet)

urlpatterns = [
    path("", views.index, name="index"),
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("eligibility/<id>", views.EligibilityTranslationView.as_view(), name="translated screen eligibility endpoint"),
    path("screens/<uuid:screen_id>/results/benefits/<int:program_id>/", views.ProgramSpecificEligibilityView.as_view(), name="program-specific eligibility endpoint"),
]
