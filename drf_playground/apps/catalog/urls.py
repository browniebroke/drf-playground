from django.urls import path
from rest_framework.routers import SimpleRouter

from drf_playground.apps.catalog import views

# The app exposes its ViewSets through a router. The project-level API combines every app's router into one.
router = SimpleRouter()
router.register("authors", views.AuthorViewSet, basename="author")
router.register("books", views.BookViewSet, basename="book")
router.register("copies", views.CopyViewSet, basename="copy")

# Non-ViewSet views are wired up by hand.
urlpatterns = [
    path("publishers/", views.PublisherListCreateView.as_view(), name="publisher-list"),
    path("publishers/<int:pk>/", views.PublisherDetailView.as_view(), name="publisher-detail"),
    path("genres/", views.GenreListView.as_view(), name="genre-list"),
    path("genres/<slug:slug>/", views.GenreDetailView.as_view(), name="genre-detail"),
]
