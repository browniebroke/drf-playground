"""Serializers for the catalog.

Demonstrates: ``ModelSerializer``, ``HyperlinkedModelSerializer``, nested read serializers, nested *writable*
serializers, the different related-field flavours, field- and object-level validation, and reusing
validators between models and serializers.
"""

from django.utils import timezone
from rest_framework import serializers

from drf_playground.apps.catalog.models import Author, Book, Copy, Genre, Publisher
from drf_playground.apps.catalog.validators import normalize_isbn, validate_isbn13


class PublisherSerializer(serializers.ModelSerializer):
    # Populated by ``annotate(book_count=Count("books"))`` in the view queryset.
    book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Publisher
        fields = ["id", "name", "website", "country", "book_count"]


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]
        # ``slug`` is derived from ``name`` in ``Genre.save()``; clients never send it.
        read_only_fields = ["slug"]


class AuthorSummarySerializer(serializers.HyperlinkedModelSerializer):
    """Compact hyperlinked representation, used when nesting authors inside other resources."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ["url", "id", "full_name"]
        extra_kwargs = {"url": {"view_name": "author-detail"}}


class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    """Hyperlinked style: the resource identifies itself and its relations by URL rather than by pk."""

    full_name = serializers.ReadOnlyField()
    books = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="book-detail")

    class Meta:
        model = Author
        fields = ["url", "id", "first_name", "last_name", "full_name", "birth_date", "bio", "books"]
        extra_kwargs = {"url": {"view_name": "author-detail"}}


class CopySerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    book_title = serializers.CharField(source="book.title", read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Copy
        fields = ["id", "barcode", "book", "book_title", "condition", "acquired_on", "is_available"]


class BookCopySerializer(CopySerializer):
    """Same as ``CopySerializer`` minus the ``book`` fields, for nesting inside a book payload."""

    class Meta(CopySerializer.Meta):
        fields = ["id", "barcode", "condition", "acquired_on", "is_available"]


class BookListSerializer(serializers.ModelSerializer):
    """Compact representation for list endpoints. Relations are rendered as strings / slugs."""

    publisher = serializers.StringRelatedField()
    authors = serializers.StringRelatedField(many=True)
    genres = serializers.SlugRelatedField(many=True, read_only=True, slug_field="slug")
    available_copies = serializers.IntegerField(read_only=True)  # annotated in the view

    class Meta:
        model = Book
        fields = ["id", "title", "isbn", "publisher", "authors", "genres", "published_on", "available_copies"]


class BookDetailSerializer(serializers.ModelSerializer):
    """Rich representation with nested related objects and aggregated review data."""

    publisher = PublisherSerializer(read_only=True)
    authors = AuthorSummarySerializer(many=True, read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    copies = BookCopySerializer(many=True, read_only=True)
    available_copies = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "publisher",
            "authors",
            "genres",
            "published_on",
            "page_count",
            "language",
            "summary",
            "copies",
            "available_copies",
            "is_available",
            "average_rating",
            "review_count",
            "created_at",
            "updated_at",
        ]

    def get_is_available(self, obj) -> bool:
        return obj.available_copies > 0


class BookWriteSerializer(serializers.ModelSerializer):
    """Input representation: relations by pk / slug, plus optional nested copies on create."""

    # Declared explicitly so the model's ``max_length=13`` / ``validate_isbn13`` validators do not run on the raw
    # (possibly hyphenated) input; ``validate_isbn`` below normalises first, then validates.
    isbn = serializers.CharField(max_length=17)
    publisher = serializers.PrimaryKeyRelatedField(queryset=Publisher.objects.all(), allow_null=True, required=False)
    authors = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), many=True)
    genres = serializers.SlugRelatedField(queryset=Genre.objects.all(), many=True, slug_field="slug", required=False)
    copies = BookCopySerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "publisher",
            "authors",
            "genres",
            "published_on",
            "page_count",
            "language",
            "summary",
            "copies",
        ]

    def validate_isbn(self, value):
        """Field-level validation: normalise, reuse the model validator, then check uniqueness on the clean value."""
        digits = normalize_isbn(value)
        validate_isbn13(digits)
        duplicates = Book.objects.filter(isbn=digits)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A book with this ISBN already exists.", code="unique")
        return digits

    def validate(self, attrs):
        """Object-level validation runs after all field validators passed."""
        published_on = attrs.get("published_on")
        if published_on and published_on > timezone.localdate():
            raise serializers.ValidationError({"published_on": "Publication date cannot be in the future."})
        if self.instance is not None and "copies" in attrs:
            raise serializers.ValidationError({"copies": "Manage copies through the /copies/ endpoints."})
        return attrs

    def create(self, validated_data):
        copies_data = validated_data.pop("copies", [])
        # ``ModelSerializer.create`` handles the remaining many-to-many fields for us.
        book = super().create(validated_data)
        Copy.objects.bulk_create([Copy(book=book, **copy) for copy in copies_data])
        return book
