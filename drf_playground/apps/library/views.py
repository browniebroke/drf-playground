from django.db.models import Count
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from drf_playground.apps.catalog.serializers import BookListSerializer
from drf_playground.apps.catalog.views import books_with_stats
from drf_playground.apps.core.exceptions import Conflict
from drf_playground.apps.core.permissions import IsOwnerOrReadOnly
from drf_playground.apps.library.filters import LoanFilter, OwnerOrPublicFilterBackend, ReviewFilter
from drf_playground.apps.library.models import Loan, Review, Shelf
from drf_playground.apps.library.pagination import LoanCursorPagination
from drf_playground.apps.library.serializers import (
    LoanSerializer,
    ReviewSerializer,
    ShelfBooksSerializer,
    ShelfSerializer,
)


class LoanViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Loans can be created, listed and returned, but never edited or deleted: pick mixins accordingly."""

    queryset = Loan.objects.select_related("copy__book", "borrower")
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LoanCursorPagination
    filterset_class = LoanFilter
    ordering_fields = ["loaned_at", "due_on"]
    ordering = ["-loaned_at"]
    throttle_scope = "checkout"  # rate configured under DEFAULT_THROTTLE_RATES["checkout"]

    def get_queryset(self):
        """Staff see every loan; members only see their own."""
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(borrower=self.request.user)

    def get_throttles(self):
        """Apply the scoped "checkout" throttle only to loan creation."""
        if self.action == "create":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        serializer.save(borrower=self.request.user)

    @action(detail=True, methods=["post"], url_path="return")
    def return_loan(self, request, pk=None, **kwargs):
        """POST /loans/{pk}/return/ - close the loan. Raises a custom 409 if already returned."""
        loan = self.get_object()
        if not loan.is_active:
            raise Conflict("This loan has already been returned.")
        loan.returned_at = timezone.now()
        loan.save(update_fields=["returned_at"])
        return Response(self.get_serializer(loan).data)

    @action(detail=False)
    def overdue(self, request, **kwargs):
        """GET /loans/overdue/ - active loans past their due date, paginated like the list endpoint."""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            returned_at__isnull=True, due_on__lt=timezone.localdate()
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("author", "book")
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    owner_field = "author"  # consumed by IsOwnerOrReadOnly
    filterset_class = ReviewFilter
    search_fields = ["body"]
    ordering_fields = ["rating", "created_at"]


class ShelfViewSet(viewsets.ModelViewSet):
    queryset = Shelf.objects.select_related("owner").prefetch_related("books").annotate(book_count=Count("books"))
    serializer_class = ShelfSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [OwnerOrPublicFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]  # Meta.ordering is ignored on GROUP BY queries, so be explicit

    def _shelf_response(self, shelf, status_code=status.HTTP_200_OK):
        shelf = self.get_queryset().get(pk=shelf.pk)  # refresh the ``book_count`` annotation
        return Response(ShelfSerializer(shelf, context=self.get_serializer_context()).data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._shelf_response(serializer.save(), status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        return self._shelf_response(serializer.save())

    @action(detail=True, serializer_class=BookListSerializer)
    def books(self, request, pk=None, **kwargs):
        """GET /shelves/{pk}/books/ - the shelf's books with the standard book list representation."""
        shelf = self.get_object()
        page = self.paginate_queryset(books_with_stats().filter(shelves=shelf))
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=True, methods=["post"], url_path="add-books", serializer_class=ShelfBooksSerializer)
    def add_books(self, request, pk=None, **kwargs):
        shelf = self.get_object()  # object permission check happens here: only the owner may POST
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shelf.books.add(*serializer.validated_data["books"])
        return self._shelf_response(shelf)

    @action(detail=True, methods=["post"], url_path="remove-books", serializer_class=ShelfBooksSerializer)
    def remove_books(self, request, pk=None, **kwargs):
        shelf = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shelf.books.remove(*serializer.validated_data["books"])
        return self._shelf_response(shelf)
