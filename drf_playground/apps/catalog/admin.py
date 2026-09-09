from django.contrib import admin

from drf_playground.apps.catalog.models import Author, Book, Copy, Genre, Publisher


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "website"]
    search_fields = ["name"]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["last_name", "first_name", "birth_date"]
    search_fields = ["first_name", "last_name"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]


class CopyInline(admin.TabularInline):
    model = Copy
    extra = 0


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "isbn", "publisher", "published_on", "language"]
    list_filter = ["language", "genres"]
    search_fields = ["title", "isbn"]
    filter_horizontal = ["authors", "genres"]
    inlines = [CopyInline]


@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display = ["barcode", "book", "condition", "acquired_on"]
    list_filter = ["condition"]
    search_fields = ["barcode", "book__title"]
