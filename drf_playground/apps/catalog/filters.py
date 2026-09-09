"""django-filter ``FilterSet`` classes, plugged in through ``DjangoFilterBackend``."""

import django_filters

from drf_playground.apps.catalog.models import Author, Book, Copy, Genre


class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    published_after = django_filters.DateFilter(field_name="published_on", lookup_expr="gte")
    published_before = django_filters.DateFilter(field_name="published_on", lookup_expr="lte")
    min_pages = django_filters.NumberFilter(field_name="page_count", lookup_expr="gte")
    max_pages = django_filters.NumberFilter(field_name="page_count", lookup_expr="lte")
    # ``?genre=fantasy&genre=horror`` -> books in *any* of those genres, looked up by slug.
    # ``field_name`` must include the lookup: django-filter builds ``{field_name: <slug value>}`` as the predicate.
    genre = django_filters.ModelMultipleChoiceFilter(
        field_name="genres__slug", to_field_name="slug", queryset=Genre.objects.all()
    )
    author = django_filters.ModelChoiceFilter(field_name="authors", queryset=Author.objects.all())
    # Method filters run arbitrary code; here it relies on the ``available_copies`` annotation from the view.
    available = django_filters.BooleanFilter(method="filter_available")

    class Meta:
        model = Book
        fields = ["language", "publisher"]

    def filter_available(self, queryset, name, value):
        return queryset.filter(available_copies__gt=0) if value else queryset.filter(available_copies=0)


class CopyFilter(django_filters.FilterSet):
    # Filters straight on the ``is_available`` annotation added by ``CopyQuerySet.with_availability()``.
    available = django_filters.BooleanFilter(field_name="is_available")

    class Meta:
        model = Copy
        fields = ["book", "condition"]
