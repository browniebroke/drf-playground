import datetime as dt

import pytest
from django.utils import timezone

from drf_playground.apps.catalog.models import Copy, Genre
from drf_playground.apps.library.models import Loan

pytestmark = pytest.mark.django_db


@pytest.fixture
def loaned_copy(copy, other_user):
    Loan.objects.create(copy=copy, borrower=other_user, due_on=timezone.localdate() + dt.timedelta(days=7))
    return copy


def test_list_uses_compact_serializer(api_client, url, book, copy):
    response = api_client.get(url("book-list"))
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0] == {
        "id": book.id,
        "title": "The Left Hand of Darkness",
        "isbn": book.isbn,
        "publisher": "Gnome Press",
        "authors": ["Ursula K. Le Guin"],
        "genres": ["science-fiction"],
        "published_on": "1969-03-01",
        "available_copies": 1,
    }


def test_detail_uses_nested_serializer(api_client, url, book, loaned_copy):
    response = api_client.get(url("book-detail", pk=book.pk))
    assert response.status_code == 200
    data = response.data
    assert data["publisher"]["name"] == "Gnome Press"
    assert data["authors"][0]["full_name"] == "Ursula K. Le Guin"
    assert data["authors"][0]["url"].endswith(url("author-detail", pk=book.authors.first().pk))
    assert data["genres"] == [{"id": book.genres.first().id, "name": "Science Fiction", "slug": "science-fiction"}]
    assert data["copies"][0]["barcode"] == "BC-001"
    assert data["copies"][0]["is_available"] is False
    assert data["available_copies"] == 0
    assert data["is_available"] is False
    assert data["average_rating"] is None
    assert data["review_count"] == 0


def test_create_with_nested_copies_and_slug_genres(auth_client, url, publisher, author, genre):
    payload = {
        "title": "The Dispossessed",
        "isbn": "978-0-06-051275-0",  # hyphenated input is normalised
        "publisher": publisher.pk,
        "authors": [author.pk],
        "genres": [genre.slug],
        "published_on": "1974-05-01",
        "page_count": 341,
        "copies": [{"barcode": "BC-100", "condition": "new"}, {"barcode": "BC-101"}],
    }
    response = auth_client.post(url("book-list"), payload, format="json")
    assert response.status_code == 201, response.data
    assert response.data["isbn"] == "9780060512750"
    assert response.data["genres"][0]["slug"] == "science-fiction"
    assert [c["barcode"] for c in response.data["copies"]] == ["BC-100", "BC-101"]
    assert response.data["available_copies"] == 2
    assert Copy.objects.filter(book_id=response.data["id"]).count() == 2


def test_create_requires_authentication(api_client, url):
    assert api_client.post(url("book-list"), {}).status_code == 401


def test_field_level_validation_rejects_bad_isbn(auth_client, url, author):
    payload = {"title": "Bad", "isbn": "9780060512751", "authors": [author.pk]}
    response = auth_client.post(url("book-list"), payload, format="json")
    assert response.status_code == 400
    assert response.data["isbn"] == ["ISBN-13 checksum does not match."]


def test_duplicate_isbn_is_rejected_after_normalisation(auth_client, url, book, author):
    hyphenated = f"{book.isbn[:3]}-{book.isbn[3:]}"
    payload = {"title": "Dup", "isbn": hyphenated, "authors": [author.pk]}
    response = auth_client.post(url("book-list"), payload, format="json")
    assert response.status_code == 400
    assert response.data["isbn"] == ["A book with this ISBN already exists."]


def test_object_level_validation_rejects_future_dates(auth_client, url, author):
    tomorrow = (timezone.localdate() + dt.timedelta(days=1)).isoformat()
    payload = {"title": "Future", "isbn": "9780060512750", "authors": [author.pk], "published_on": tomorrow}
    response = auth_client.post(url("book-list"), payload, format="json")
    assert response.status_code == 400
    assert response.data["published_on"] == ["Publication date cannot be in the future."]


def test_update_rejects_nested_copies(auth_client, url, book):
    response = auth_client.patch(url("book-detail", pk=book.pk), {"copies": []}, format="json")
    assert response.status_code == 400
    assert "copies" in response.data

    response = auth_client.patch(url("book-detail", pk=book.pk), {"title": "Renamed"}, format="json")
    assert response.status_code == 200
    assert response.data["title"] == "Renamed"


def test_django_filter_filterset(api_client, url, book_factory, genre, copy):
    fantasy = Genre.objects.create(name="Fantasy")
    book_factory("A Wizard of Earthsea", genres=[fantasy], page_count=205, language="en")
    book_factory("La Peste", genres=[], page_count=308, language="fr")

    def titles(**params):
        return [b["title"] for b in api_client.get(url("book-list"), params).data["results"]]

    assert titles(genre="fantasy") == ["A Wizard of Earthsea"]
    assert titles(genre=["fantasy", "science-fiction"]) == ["A Wizard of Earthsea", "The Left Hand of Darkness"]
    assert titles(min_pages=300) == ["La Peste", "The Left Hand of Darkness"]
    assert titles(language="fr") == ["La Peste"]
    assert titles(available="true") == ["The Left Hand of Darkness"]  # only one has a copy
    assert titles(title="peste") == ["La Peste"]


def test_search_and_ordering(api_client, url, book_factory):
    book_factory("A Wizard of Earthsea", page_count=205, summary="Ged the sparrowhawk")
    book_factory("The Left Hand of Darkness", page_count=304)
    response = api_client.get(url("book-list"), {"search": "sparrowhawk"})
    assert [b["title"] for b in response.data["results"]] == ["A Wizard of Earthsea"]
    response = api_client.get(url("book-list"), {"ordering": "-page_count"})
    assert [b["title"] for b in response.data["results"]] == ["The Left Hand of Darkness", "A Wizard of Earthsea"]


def test_page_number_pagination_with_page_size(api_client, url, book_factory):
    for index in range(3):
        book_factory(f"Book {index}")
    response = api_client.get(url("book-list"), {"page_size": 2})
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 2
    assert "page=2" in response.data["next"]
    response = api_client.get(response.data["next"])
    assert len(response.data["results"]) == 1
    assert response.data["previous"] is not None


def test_recently_added_list_action(api_client, url, book_factory):
    for index in range(7):
        book_factory(f"Book {index}")
    response = api_client.get(url("book-recently-added"))
    assert response.status_code == 200
    assert [b["title"] for b in response.data] == ["Book 6", "Book 5", "Book 4", "Book 3", "Book 2"]


def test_copies_detail_action(api_client, auth_client, staff_client, url, book, copy):
    response = api_client.get(url("book-copies", pk=book.pk))
    assert response.status_code == 200
    assert [c["barcode"] for c in response.data] == ["BC-001"]

    payload = {"barcode": "BC-002", "condition": "worn"}
    assert auth_client.post(url("book-copies", pk=book.pk), payload).status_code == 403
    response = staff_client.post(url("book-copies", pk=book.pk), payload)
    assert response.status_code == 201
    assert response.data["is_available"] is True
    assert book.copies.count() == 2


def test_copy_lookup_by_barcode_and_availability_filter(api_client, url, loaned_copy, book):
    Copy.objects.create(book=book, barcode="BC-002")
    response = api_client.get(url("copy-detail", barcode="BC-001"))
    assert response.status_code == 200
    assert response.data["book_title"] == "The Left Hand of Darkness"
    assert response.data["is_available"] is False

    response = api_client.get(url("copy-list"), {"available": "true"})
    assert [c["barcode"] for c in response.data["results"]] == ["BC-002"]
    response = api_client.get(url("copy-list"), {"available": "false"})
    assert [c["barcode"] for c in response.data["results"]] == ["BC-001"]
