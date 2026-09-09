from django.contrib import admin

from drf_playground.apps.library.models import Loan, Review, Shelf


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["copy", "borrower", "loaned_at", "due_on", "returned_at"]
    list_filter = ["returned_at"]
    autocomplete_fields = ["copy"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["book", "author", "rating", "created_at"]
    list_filter = ["rating"]


@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "is_public", "created_at"]
    list_filter = ["is_public"]
    filter_horizontal = ["books"]
