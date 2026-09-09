import pytest

from drf_playground.apps.library.models import Review

pytestmark = pytest.mark.django_db


def test_create_uses_hidden_current_user(auth_client, user, url, book):
    response = auth_client.post(url("review-list"), {"book": book.pk, "rating": 5, "body": "Superb."})
    assert response.status_code == 201, response.data
    assert response.data["author_name"] == user.username
    assert "author" not in response.data  # HiddenField never appears in output
    assert Review.objects.get().author == user


def test_unique_together_validator(auth_client, url, book):
    assert auth_client.post(url("review-list"), {"book": book.pk, "rating": 5}).status_code == 201
    response = auth_client.post(url("review-list"), {"book": book.pk, "rating": 3})
    assert response.status_code == 400
    assert response.data["non_field_errors"] == ["You have already reviewed this book."]


def test_model_validators_are_enforced(auth_client, url, book):
    response = auth_client.post(url("review-list"), {"book": book.pk, "rating": 6})
    assert response.status_code == 400
    assert "rating" in response.data


def test_object_level_permission(auth_client, other_client, api_client, url, book):
    review_id = auth_client.post(url("review-list"), {"book": book.pk, "rating": 4}).data["id"]
    detail = url("review-detail", pk=review_id)

    assert api_client.get(detail).status_code == 200  # read is public
    response = other_client.patch(detail, {"rating": 1})
    assert response.status_code == 403
    assert response.data["detail"] == "You do not own this object."
    assert auth_client.patch(detail, {"rating": 3}).status_code == 200
    assert other_client.delete(detail).status_code == 403
    assert auth_client.delete(detail).status_code == 204


def test_filters_and_book_aggregates(auth_client, other_client, api_client, url, book):
    auth_client.post(url("review-list"), {"book": book.pk, "rating": 5})
    other_client.post(url("review-list"), {"book": book.pk, "rating": 2})

    response = api_client.get(url("review-list"), {"min_rating": 3})
    assert [r["rating"] for r in response.data["results"]] == [5]
    response = api_client.get(url("review-list"), {"book": book.pk, "ordering": "rating"})
    assert [r["rating"] for r in response.data["results"]] == [2, 5]

    detail = api_client.get(url("book-detail", pk=book.pk)).data
    assert detail["average_rating"] == 3.5
    assert detail["review_count"] == 2
