"""Populate the database with a small, deterministic dataset for exploring the API.

Idempotent: re-running updates existing rows instead of duplicating them.
Creates two users (``admin`` / ``reader``, both with password ``password``).
"""

import datetime as dt

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from drf_playground.apps.catalog.models import Author, Book, Copy, Genre, Publisher
from drf_playground.apps.catalog.validators import isbn13_check_digit
from drf_playground.apps.library.models import Loan, Review, Shelf

PUBLISHERS = [
    ("Gnome Press", "US"),
    ("Chatto & Windus", "GB"),
    ("Gallimard", "FR"),
]

AUTHORS = [
    ("Ursula K.", "Le Guin", dt.date(1929, 10, 21)),
    ("Isaac", "Asimov", dt.date(1920, 1, 2)),
    ("Aldous", "Huxley", dt.date(1894, 7, 26)),
    ("Albert", "Camus", dt.date(1913, 11, 7)),
    ("Octavia E.", "Butler", dt.date(1947, 6, 22)),
]

GENRES = ["Science Fiction", "Dystopia", "Fantasy", "Philosophy", "Classics"]

# (title, publisher, [author last names], [genres], published_on, pages, language, number of copies)
BOOKS = [
    ("The Left Hand of Darkness", "Gnome Press", ["Le Guin"], ["Science Fiction"], dt.date(1969, 3, 1), 304, "en", 3),
    ("A Wizard of Earthsea", "Gnome Press", ["Le Guin"], ["Fantasy"], dt.date(1968, 11, 1), 205, "en", 2),
    ("Foundation", "Gnome Press", ["Asimov"], ["Science Fiction", "Classics"], dt.date(1951, 6, 1), 255, "en", 2),
    ("I, Robot", "Gnome Press", ["Asimov"], ["Science Fiction"], dt.date(1950, 12, 2), 253, "en", 1),
    ("Brave New World", "Chatto & Windus", ["Huxley"], ["Dystopia", "Classics"], dt.date(1932, 1, 1), 311, "en", 2),
    ("L'Étranger", "Gallimard", ["Camus"], ["Philosophy", "Classics"], dt.date(1942, 5, 19), 159, "fr", 1),
    ("La Peste", "Gallimard", ["Camus"], ["Philosophy", "Classics"], dt.date(1947, 6, 10), 308, "fr", 1),
    ("Kindred", "Gnome Press", ["Butler"], ["Science Fiction", "Fantasy"], dt.date(1979, 6, 1), 264, "en", 2),
    (
        "Parable of the Sower",
        "Gnome Press",
        ["Butler"],
        ["Science Fiction", "Dystopia"],
        dt.date(1993, 10, 1),
        299,
        "en",
        0,
    ),
]


def fake_isbn(index: int) -> str:
    """Build a syntactically valid (but fictional) ISBN-13 from a sequence number."""
    prefix = f"9780000{index:05d}"
    return prefix + isbn13_check_digit(prefix)


class Command(BaseCommand):
    help = "Seed the database with sample catalog and library data."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        admin, _ = user_model.objects.get_or_create(
            username="admin", defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.com"}
        )
        reader, _ = user_model.objects.get_or_create(username="reader", defaults={"email": "reader@example.com"})
        for user in (admin, reader):
            user.set_password("password")
            user.save(update_fields=["password"])

        publishers = {
            name: Publisher.objects.update_or_create(name=name, defaults={"country": country})[0]
            for name, country in PUBLISHERS
        }
        authors = {
            last: Author.objects.update_or_create(first_name=first, last_name=last, defaults={"birth_date": born})[0]
            for first, last, born in AUTHORS
        }
        genres = {name: Genre.objects.get_or_create(name=name)[0] for name in GENRES}

        books = []
        for index, (title, publisher, book_authors, book_genres, published_on, pages, language, copies) in enumerate(
            BOOKS, start=1
        ):
            book, _ = Book.objects.update_or_create(
                isbn=fake_isbn(index),
                defaults={
                    "title": title,
                    "publisher": publishers[publisher],
                    "published_on": published_on,
                    "page_count": pages,
                    "language": language,
                },
            )
            book.authors.set(authors[last] for last in book_authors)
            book.genres.set(genres[name] for name in book_genres)
            for copy_index in range(1, copies + 1):
                Copy.objects.get_or_create(book=book, barcode=f"BC-{index:03d}-{copy_index:02d}")
            books.append(book)

        # One active loan and one returned loan for the reader.
        first_copy = books[0].copies.first()
        Loan.objects.get_or_create(
            copy=first_copy,
            borrower=reader,
            returned_at=None,
            defaults={"due_on": dt.date.today() + dt.timedelta(days=14)},
        )
        Review.objects.update_or_create(book=books[0], author=reader, defaults={"rating": 5, "body": "A masterpiece."})
        Review.objects.update_or_create(book=books[2], author=admin, defaults={"rating": 4, "body": "Grand in scope."})

        shelf, _ = Shelf.objects.get_or_create(owner=reader, name="To read", defaults={"is_public": True})
        shelf.books.set(books[3:6])
        Shelf.objects.get_or_create(owner=reader, name="Secret favourites", defaults={"is_public": False})

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(books)} books, {Copy.objects.count()} copies."))
