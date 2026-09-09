import pytest

from drf_playground.apps.catalog.models import Author

pytestmark = pytest.mark.django_db


def test_hyperlinked_representation(api_client, url, author, book):
    response = api_client.get(url("author-detail", pk=author.pk))
    assert response.status_code == 200
    assert response.data["url"] == f"http://testserver{url('author-detail', pk=author.pk)}"
    assert response.data["full_name"] == "Ursula K. Le Guin"
    assert response.data["books"] == [f"http://testserver{url('book-detail', pk=book.pk)}"]


def test_books_action_is_paginated(api_client, url, author, book_factory):
    book_factory("A Wizard of Earthsea")
    book_factory("The Dispossessed")
    response = api_client.get(url("author-books", pk=author.pk), {"page_size": 2})
    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["next"] is None
    assert {b["title"] for b in response.data["results"]} == {"A Wizard of Earthsea", "The Dispossessed"}


def test_search_and_ordering(api_client, url, author):
    Author.objects.create(first_name="Isaac", last_name="Asimov")
    response = api_client.get(url("author-list"), {"search": "guin"})
    assert [a["last_name"] for a in response.data["results"]] == ["Le Guin"]
    response = api_client.get(url("author-list"), {"ordering": "-last_name"})
    assert [a["last_name"] for a in response.data["results"]] == ["Le Guin", "Asimov"]


def test_write_is_staff_only(auth_client, staff_client, url):
    payload = {"first_name": "Octavia E.", "last_name": "Butler"}
    assert auth_client.post(url("author-list"), payload).status_code == 403
    assert staff_client.post(url("author-list"), payload).status_code == 201
