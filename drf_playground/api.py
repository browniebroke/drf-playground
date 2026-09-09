"""Versioned API root: combines every app's router into a single ``DefaultRouter`` and adds hand-wired routes.

Mounted at ``/api/<version>/`` by the project ``urls.py``; ``request.version`` is populated by
``URLPathVersioning`` and used by DRF's ``reverse()`` so hyperlinked serializers stay version-aware.
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from drf_playground.apps.catalog.urls import router as catalog_router
from drf_playground.apps.catalog.urls import urlpatterns as catalog_urlpatterns
from drf_playground.apps.library.urls import router as library_router

router = DefaultRouter()
router.registry.extend(catalog_router.registry)
router.registry.extend(library_router.registry)

urlpatterns = [
    path("", include(router.urls)),
    path("", include(catalog_urlpatterns)),
    path("", include("drf_playground.apps.core.urls")),
    # POST {"username": ..., "password": ...} -> {"token": ...}; then send ``Authorization: Token <key>``.
    path("auth/token/", obtain_auth_token, name="obtain-token"),
    # OpenAPI schema and interactive docs (drf-spectacular).
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
