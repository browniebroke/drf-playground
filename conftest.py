"""Shared pytest fixtures. ``pytest-django`` picks up ``DJANGO_SETTINGS_MODULE`` from pyproject.toml."""

import datetime as dt

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from drf_playground.apps.catalog.models import Author, Book, Copy, Genre, Publisher
from drf_playground.apps.catalog.validators import isbn13_check_digit


def make_isbn(index: int) -> str:
    prefix = f"9780000{index:05d}"
    return prefix + isbn13_check_digit(prefix)


def api_url(name: str, **kwargs) -> str:
    """Reverse a versioned API route. Every route under /api/<version>/ needs the ``version`` kwarg."""
    return reverse(name, kwargs={"version": "v1", **kwargs})


@pytest.fixture(autouse=True)
def _clear_cache():
    """Throttle counters live in the cache; isolate tests from one another."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def url():
    return api_url


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="reader", password="password")


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="other", password="password")


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(username="admin", password="password", is_staff=True)


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def publisher():
    return Publisher.objects.create(name="Gnome Press", country="US")


@pytest.fixture
def author():
    return Author.objects.create(first_name="Ursula K.", last_name="Le Guin", birth_date=dt.date(1929, 10, 21))


@pytest.fixture
def genre():
    return Genre.objects.create(name="Science Fiction")


@pytest.fixture
def book_factory(publisher, author, genre):
    """Callable fixture: ``book_factory("Title", page_count=100, genres=[...])``."""

    def make(title="The Left Hand of Darkness", *, authors=None, genres=None, **fields):
        fields.setdefault("isbn", make_isbn(Book.objects.count() + 1))
        fields.setdefault("publisher", publisher)
        fields.setdefault("published_on", dt.date(1969, 3, 1))
        fields.setdefault("page_count", 304)
        book = Book.objects.create(title=title, **fields)
        book.authors.set(authors if authors is not None else [author])
        book.genres.set(genres if genres is not None else [genre])
        return book

    return make


@pytest.fixture
def book(book_factory):
    return book_factory()


@pytest.fixture
def copy(book):
    return Copy.objects.create(book=book, barcode="BC-001")
