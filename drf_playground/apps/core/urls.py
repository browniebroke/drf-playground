from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from drf_playground.apps.core import views

urlpatterns = [
    path("ping/", views.ping, name="ping"),
    path("whoami/", views.WhoAmIView.as_view(), name="whoami"),
    path("stats/", views.StatsView.as_view(), name="stats"),
]

# Allows ``/ping.json`` / ``/ping.api`` style explicit format selection on these plain views.
urlpatterns = format_suffix_patterns(urlpatterns)
