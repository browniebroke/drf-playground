"""URL configuration for drf_playground project."""

from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Versioned API: /api/v1/... - the ``version`` kwarg is consumed by ``URLPathVersioning``.
    re_path(r"^api/(?P<version>v[0-9]+)/", include("drf_playground.api")),
    # Login/logout views for the browsable API.
    path("api-auth/", include("rest_framework.urls")),
]
