"""benefits URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path, re_path

from benefits.views import redirect_legacy_co_energy_calculator
from sesame.views import LoginView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

handler403 = "benefits.views.catch_403_view"
handler400 = "benefits.views.catch_400_view"

schema_view = get_schema_view(
    openapi.Info(
        default_version="v1",
        title="Colorado Open Benefits API",
        description="API calculates eligibility across over 40 benefit programs in Colorado",
        version="0.0.1",
    ),
    public=True,
    permission_classes=[],
    authentication_classes=[],
)

urlpatterns = [
    # Redirect legacy co_energy_calculator URLs to cesn
    re_path(r"^api/.*co_energy_calculator", redirect_legacy_co_energy_calculator),
    path("api/", include("configuration.urls")),
    path("api/", include("screener.urls")),
    path("api/", include("programs.urls")),
    path("api/", include("authentication.urls")),
    path("api/", include("validations.urls")),
    path("api/translations/", include("translations.urls")),
    path("admin/", admin.site.urls),
    path("sesame/login/", LoginView.as_view(), name="sesame-login"),
    path(
        "api/documentation/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
]
