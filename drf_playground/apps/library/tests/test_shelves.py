import pytest

from drf_playground.apps.library.models import Shelf

pytestmark = pytest.mark.django_db


@pytest.fixture
def private_shelf(user, book):
    shelf = Shelf.objects.create(owner=user, name="Secret", is_public=False)
    shelf.books.add(book)
    return shelf


@pytest.fixture
def public_shelf(user):
    return Shelf.objects.create(owner=user, name="Favourites", is_public=True)


def test_custom_filter_backend_hides_private_shelves(
    api_client, auth_client, other_client, url, private_shelf, public_shelf
):
    def names(client):
        return [s["name"] for s in client.get(url("shelf-list")).data["results"]]

    assert names(api_client) == ["Favourites"]
    assert names(other_client) == ["Favourites"]
    assert names(auth_client) == ["Favourites", "Secret"]

    # The same backend runs inside get_object(), so a private shelf is a 404 for everyone else.
    assert other_client.get(url("shelf-detail", pk=private_shelf.pk)).status_code == 404
    assert auth_client.get(url("shelf-detail", pk=private_shelf.pk)).status_code == 200


def test_create_with_hidden_owner_and_unique_name(auth_client, other_client, user, url, public_shelf):
    response = auth_client.post(url("shelf-list"), {"name": "Favourites"})
    assert response.status_code == 400
    assert response.data["non_field_errors"] == ["You already have a shelf with this name."]

    response = other_client.post(url("shelf-list"), {"name": "Favourites", "is_public": True})
    assert response.status_code == 201  # uniqueness is per owner
    assert response.data["owner_name"] == "other"
    assert response.data["book_count"] == 0


def test_add_and_remove_books_actions(auth_client, other_client, url, public_shelf, book, book_factory):
    other_book = book_factory("A Wizard of Earthsea")
    payload = {"books": [book.pk, other_book.pk]}

    assert other_client.post(url("shelf-add-books", pk=public_shelf.pk), payload).status_code == 403
    response = auth_client.post(url("shelf-add-books", pk=public_shelf.pk), payload)
    assert response.status_code == 200
    assert response.data["book_count"] == 2

    response = auth_client.post(url("shelf-remove-books", pk=public_shelf.pk), {"books": [book.pk]})
    assert response.data["books"] == [other_book.pk]

    response = auth_client.post(url("shelf-add-books", pk=public_shelf.pk), {"books": []})
    assert response.status_code == 400


def test_books_action_reuses_book_list_serializer(api_client, url, private_shelf, auth_client, book):
    assert api_client.get(url("shelf-books", pk=private_shelf.pk)).status_code == 404
    response = auth_client.get(url("shelf-books", pk=private_shelf.pk))
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == book.title
    assert "available_copies" in response.data["results"][0]
