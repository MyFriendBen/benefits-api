from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r"configuration/(?P<white_label>.+)", views.ConfigurationView, basename="Configuration")

urlpatterns = [
    path("", include(router.urls)),
    path("<str:white_label_code>/form-options/", views.get_form_options, name="form-options"),
]
