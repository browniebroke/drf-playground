import django_filters
from django.db.models import Q
from django.utils import timezone
from rest_framework.filters import BaseFilterBackend

from drf_playground.apps.library.models import Loan, Review


class LoanFilter(django_filters.FilterSet):
    STATUS_CHOICES = (("active", "Active"), ("returned", "Returned"))

    status = django_filters.ChoiceFilter(choices=STATUS_CHOICES, method="filter_status")
    book = django_filters.NumberFilter(field_name="copy__book")
    due_before = django_filters.DateFilter(field_name="due_on", lookup_expr="lte")
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = Loan
        fields = ["copy", "borrower"]

    def filter_status(self, queryset, name, value):
        return queryset.filter(returned_at__isnull=(value == "active"))

    def filter_overdue(self, queryset, name, value):
        overdue = Q(returned_at__isnull=True, due_on__lt=timezone.localdate())
        return queryset.filter(overdue) if value else queryset.exclude(overdue)


class ReviewFilter(django_filters.FilterSet):
    min_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="gte")

    class Meta:
        model = Review
        fields = ["book", "author", "rating"]


class OwnerOrPublicFilterBackend(BaseFilterBackend):
    """Custom DRF filter backend: restrict the queryset to public rows plus the requesting user's own rows.

    Because ``GenericAPIView.get_object()`` also runs ``filter_queryset``, this doubles as row-level
    access control for detail routes (other users' private shelves 404 rather than 403).
    """

    def filter_queryset(self, request, queryset, view):
        if request.user.is_authenticated:
            return queryset.filter(Q(is_public=True) | Q(owner=request.user))
        return queryset.filter(is_public=True)
