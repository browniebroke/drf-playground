from rest_framework.routers import SimpleRouter

from drf_playground.apps.library import views

router = SimpleRouter()
router.register("loans", views.LoanViewSet, basename="loan")
router.register("reviews", views.ReviewViewSet, basename="review")
router.register("shelves", views.ShelfViewSet, basename="shelf")

urlpatterns = []
