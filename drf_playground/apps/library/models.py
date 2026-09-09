from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from drf_playground.apps.catalog.models import Book, Copy


class Loan(models.Model):
    copy = models.ForeignKey(Copy, on_delete=models.PROTECT, related_name="loans")
    borrower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="loans")
    loaned_at = models.DateTimeField(default=timezone.now)
    due_on = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-loaned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["copy"], condition=models.Q(returned_at__isnull=True), name="unique_active_loan_per_copy"
            )
        ]

    def __str__(self):
        return f"{self.copy} -> {self.borrower}"

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    @property
    def is_overdue(self) -> bool:
        return self.is_active and self.due_on < timezone.localdate()


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["book", "author"], name="one_review_per_user_per_book")]

    def __str__(self):
        return f"{self.book} - {self.rating}/5 by {self.author}"


class Shelf(models.Model):
    """A user-curated list of books. Private by default, optionally public."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shelves")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    books = models.ManyToManyField(Book, related_name="shelves", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "shelves"
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_shelf_name_per_owner")]

    def __str__(self):
        return f"{self.owner}: {self.name}"
