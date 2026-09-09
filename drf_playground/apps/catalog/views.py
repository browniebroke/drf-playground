"""Catalog views, deliberately written in several styles to compare them.

* ``Publisher``: concrete generic views (``ListCreateAPIView`` / ``RetrieveUpdateDestroyAPIView``).
* ``Genre``: ``GenericAPIView`` + explicit mixins, custom ``lookup_field``.
* ``Author``, ``Book``, ``Copy``: ``ModelViewSet`` with routers and ``@action`` extras.
"""

from django.db.models import Avg, Count, OuterRef, Prefetch, Q, Subquery
from rest_framework import filters, generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from drf_playground.apps.catalog.filters import BookFilter, CopyFilter
from drf_playground.apps.catalog.models import Author, Book, Copy, Genre, Publisher
from drf_playground.apps.catalog.serializers import (
    AuthorSerializer,
    BookCopySerializer,
    BookDetailSerializer,
    BookListSerializer,
    BookWriteSerializer,
    CopySerializer,
    GenreSerializer,
    PublisherSerializer,
)
from drf_playground.apps.core.permissions import IsAdminOrReadOnly

# --- Publishers: concrete generic views ------------------------------------------------------------------------


class PublisherListCreateView(generics.ListCreateAPIView):
    queryset = Publisher.objects.annotate(book_count=Count("books"))
    serializer_class = PublisherSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = LimitOffsetPagination  # ``?limit=10&offset=20`` instead of the project default
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "country"]
    ordering_fields = ["name", "book_count"]
    ordering = ["name"]


class PublisherDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Publisher.objects.annotate(book_count=Count("books"))
    serializer_class = PublisherSerializer
    permission_classes = [IsAdminOrReadOnly]


# --- Genres: GenericAPIView + mixins ---------------------------------------------------------------------------


class GenreListView(mixins.ListModelMixin, mixins.CreateModelMixin, generics.GenericAPIView):
    """Mixins provide ``.list()`` / ``.create()``; we wire them to HTTP verbs ourselves."""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None  # small, unpaginated list

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class GenreDetailView(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, generics.GenericAPIView
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"  # /genres/science-fiction/ instead of /genres/3/

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


# --- Authors / Books / Copies: ViewSets ------------------------------------------------------------------------


def books_with_stats():
    """Shared base queryset: prefetch relations and annotate availability & review aggregates.

    ``available_copies`` uses conditional aggregates; the review numbers use correlated subqueries so the
    joins needed for the copy counts cannot skew them.
    """
    same_book = Book.objects.filter(pk=OuterRef("pk"))
    return (
        Book.objects.order_by("title")  # Meta.ordering is ignored on GROUP BY queries, so be explicit
        .select_related("publisher")
        .prefetch_related("authors", "genres", Prefetch("copies", queryset=Copy.objects.with_availability()))
        .annotate(
            available_copies=Count("copies", distinct=True)
            - Count("copies__loans", filter=Q(copies__loans__returned_at__isnull=True), distinct=True),
            average_rating=Subquery(same_book.annotate(value=Avg("reviews__rating")).values("value")[:1]),
            review_count=Subquery(same_book.annotate(value=Count("reviews")).values("value")[:1]),
        )
    )


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.prefetch_related("books")
    serializer_class = AuthorSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name"]
    ordering_fields = ["last_name", "birth_date"]

    @action(detail=True, serializer_class=BookListSerializer)
    def books(self, request, pk=None, **kwargs):
        """GET /authors/{pk}/books/ - paginated list of this author's books, reusing the view's paginator."""
        author = self.get_object()
        queryset = books_with_stats().filter(authors=author)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class BookViewSet(viewsets.ModelViewSet):
    queryset = books_with_stats()
    serializer_class = BookDetailSerializer
    filterset_class = BookFilter
    search_fields = ["title", "summary", "authors__last_name"]
    ordering_fields = ["title", "published_on", "page_count", "average_rating"]
    ordering = ["title"]

    def get_serializer_class(self):
        """Different shapes for list, detail and write operations.

        Falls back to ``super()`` so ``@action(serializer_class=...)`` overrides keep working.
        """
        if self.action == "list":
            return BookListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return BookWriteSerializer
        return super().get_serializer_class()

    def _detail_response(self, book, status_code):
        # Re-fetch through the annotated queryset so the response carries the computed fields.
        book = self.get_queryset().get(pk=book.pk)
        return Response(BookDetailSerializer(book, context=self.get_serializer_context()).data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return self._detail_response(book, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return self._detail_response(book, status.HTTP_200_OK)

    @action(detail=False, url_path="recently-added", serializer_class=BookListSerializer)
    def recently_added(self, request, **kwargs):
        """GET /books/recently-added/ - a list-level action, unpaginated."""
        queryset = self.filter_queryset(self.get_queryset()).order_by("-created_at")[:5]
        return Response(self.get_serializer(queryset, many=True).data)

    @action(
        detail=True,
        methods=["get", "post"],
        serializer_class=BookCopySerializer,
        permission_classes=[IsAdminOrReadOnly],
    )
    def copies(self, request, pk=None, **kwargs):
        """GET lists the copies of a book; POST registers a new copy (staff only)."""
        book = self.get_object()
        if request.method == "GET":
            return Response(self.get_serializer(book.copies.all(), many=True).data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        copy = serializer.save(book=book)
        copy = Copy.objects.with_availability().get(pk=copy.pk)  # pick up the ``is_available`` annotation
        return Response(self.get_serializer(copy).data, status=status.HTTP_201_CREATED)


class CopyViewSet(viewsets.ModelViewSet):
    queryset = Copy.objects.select_related("book").with_availability()
    serializer_class = CopySerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = CopyFilter
    lookup_field = "barcode"  # /copies/BC-0001/ - barcodes are the natural identifier here
