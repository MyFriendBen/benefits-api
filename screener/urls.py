from django.urls import include, path
from rest_framework import routers
from . import views
from . import assistant

router = routers.DefaultRouter()
router.register(r"screens", views.ScreenViewSet)
router.register(r"messages", views.MessageViewSet)

urlpatterns = [
    path("", views.index, name="index"),
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("eligibility/<id>", views.EligibilityTranslationView.as_view(), name="translated screen eligibility endpoint"),
    path("screens/<uuid:screen_uuid>/nps/", views.NPSScoreView.as_view(), name="nps-score"),
    # Benbot assistant — proxies to mfb-ai-service; gated by the 'benbot' feature flag.
    path(
        "screens/<uuid:screen_uuid>/assistant/conversations/",
        assistant.AssistantStartView.as_view(),
        name="assistant-start",
    ),
    path(
        "screens/<uuid:screen_uuid>/assistant/conversations/<str:conversation_id>/messages/",
        assistant.AssistantMessageView.as_view(),
        name="assistant-message",
    ),
    path(
        "screener-options/<str:white_label>/has-benefits-programs/",
        views.HasBenefitsProgramsView.as_view(),
        name="has-benefits-programs",
    ),
    path(
        "screener-options/<str:white_label>/referral-options/",
        views.ReferralSourcesView.as_view(),
        name="referral-options",
    ),
    path(
        "screener-options/<str:white_label>/rem-impact/",
        views.RemImpactView.as_view(),
        name="rem-impact",
    ),
]
