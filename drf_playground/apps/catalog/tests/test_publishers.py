import pytest

from drf_playground.apps.catalog.models import Publisher

pytestmark = pytest.mark.django_db


def test_list_uses_limit_offset_pagination(api_client, url, publisher):
    Publisher.objects.create(name="Gallimard", country="FR")
    response = api_client.get(url("publisher-list"), {"limit": 1})
    assert response.status_code == 200
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 1
    assert "limit=1&offset=1" in response.data["next"]


def test_book_count_annotation_and_ordering(api_client, url, publisher, book):
    Publisher.objects.create(name="Gallimard", country="FR")
    response = api_client.get(url("publisher-list"), {"ordering": "-book_count"})
    assert [p["book_count"] for p in response.data["results"]] == [1, 0]
    assert response.data["results"][0]["name"] == publisher.name


def test_search_filter(api_client, url, publisher):
    Publisher.objects.create(name="Gallimard", country="FR")
    response = api_client.get(url("publisher-list"), {"search": "FR"})
    assert [p["name"] for p in response.data["results"]] == ["Gallimard"]


def test_anonymous_and_regular_users_cannot_write(api_client, auth_client, url):
    payload = {"name": "New Press"}
    assert api_client.post(url("publisher-list"), payload).status_code == 401
    response = auth_client.post(url("publisher-list"), payload)
    assert response.status_code == 403
    assert response.data["detail"] == "Only staff members can modify this resource."


def test_staff_can_create_update_and_delete(staff_client, url):
    response = staff_client.post(url("publisher-list"), {"name": "New Press", "country": "GB"})
    assert response.status_code == 201
    pk = response.data["id"]

    response = staff_client.patch(url("publisher-detail", pk=pk), {"website": "https://example.com"})
    assert response.status_code == 200
    assert response.data["website"] == "https://example.com"

    assert staff_client.delete(url("publisher-detail", pk=pk)).status_code == 204
    assert not Publisher.objects.filter(pk=pk).exists()


def test_validation_errors_keep_standard_shape(staff_client, url, publisher):
    response = staff_client.post(url("publisher-list"), {"name": publisher.name, "website": "not-a-url"})
    assert response.status_code == 400
    assert set(response.data) == {"name", "website"}
