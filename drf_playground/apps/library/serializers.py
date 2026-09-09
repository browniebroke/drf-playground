import datetime as dt

from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from drf_playground.apps.catalog.models import Book, Copy
from drf_playground.apps.library.models import Loan, Review, Shelf

LOAN_PERIOD = dt.timedelta(days=14)


class LoanSerializer(serializers.ModelSerializer):
    copy = serializers.PrimaryKeyRelatedField(queryset=Copy.objects.select_related("book"))
    barcode = serializers.CharField(source="copy.barcode", read_only=True)
    book_title = serializers.CharField(source="copy.book.title", read_only=True)
    borrower = serializers.StringRelatedField(read_only=True)  # set from ``request.user`` in the view
    is_active = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id",
            "copy",
            "barcode",
            "book_title",
            "borrower",
            "loaned_at",
            "due_on",
            "returned_at",
            "is_active",
            "is_overdue",
        ]
        read_only_fields = ["loaned_at", "returned_at"]
        extra_kwargs = {"due_on": {"required": False}}

    def validate_copy(self, copy):
        if copy.loans.filter(returned_at__isnull=True).exists():
            raise serializers.ValidationError("This copy is currently on loan.", code="unavailable")
        return copy

    def validate_due_on(self, due_on):
        if due_on <= timezone.localdate():
            raise serializers.ValidationError("Due date must be in the future.")
        return due_on

    def create(self, validated_data):
        validated_data.setdefault("due_on", timezone.localdate() + LOAN_PERIOD)
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    # ``HiddenField`` is never rendered nor accepted as input, but takes part in validation with its default.
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    author_name = serializers.ReadOnlyField(source="author.username")
    book_title = serializers.ReadOnlyField(source="book.title")

    class Meta:
        model = Review
        fields = ["id", "book", "book_title", "author", "author_name", "rating", "body", "created_at", "updated_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=Review.objects.all(),
                fields=["book", "author"],
                message="You have already reviewed this book.",
            )
        ]


class ShelfSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    owner_name = serializers.ReadOnlyField(source="owner.username")
    books = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), many=True, required=False)
    book_count = serializers.IntegerField(read_only=True)  # annotated in the view

    class Meta:
        model = Shelf
        fields = ["id", "owner", "owner_name", "name", "description", "is_public", "books", "book_count", "created_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=Shelf.objects.all(),
                fields=["owner", "name"],
                message="You already have a shelf with this name.",
            )
        ]


class ShelfBooksSerializer(serializers.Serializer):
    """Input-only serializer for the add/remove books actions."""

    books = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), many=True, allow_empty=False)
