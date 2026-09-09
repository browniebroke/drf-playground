from django.db import models
from django.db.models import Exists, OuterRef
from django.utils.text import slugify

from drf_playground.apps.catalog.validators import validate_isbn13


class Publisher(models.Model):
    name = models.CharField(max_length=200, unique=True)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=2, blank=True, help_text="ISO 3166-1 alpha-2 code")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Book(models.Model):
    title = models.CharField(max_length=255)
    isbn = models.CharField("ISBN-13", max_length=13, unique=True, validators=[validate_isbn13])
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True, related_name="books")
    authors = models.ManyToManyField(Author, related_name="books")
    genres = models.ManyToManyField(Genre, related_name="books", blank=True)
    published_on = models.DateField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=8, default="en")
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class CopyQuerySet(models.QuerySet):
    def with_availability(self):
        """Annotate ``is_available``: no open loan exists for the copy. Filterable and cheap (single EXISTS)."""
        loan_model = self.model.loans.rel.related_model
        active_loans = loan_model.objects.filter(copy=OuterRef("pk"), returned_at__isnull=True)
        return self.annotate(is_available=~Exists(active_loans))


class Copy(models.Model):
    """A physical copy of a book. Loans are made against copies, not books."""

    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        WORN = "worn", "Worn"
        DAMAGED = "damaged", "Damaged"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    barcode = models.CharField(max_length=32, unique=True)
    condition = models.CharField(max_length=10, choices=Condition.choices, default=Condition.GOOD)
    acquired_on = models.DateField(auto_now_add=True)

    objects = CopyQuerySet.as_manager()

    class Meta:
        ordering = ["barcode"]
        verbose_name_plural = "copies"

    def __str__(self):
        return f"{self.book.title} [{self.barcode}]"
