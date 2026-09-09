import pytest

pytestmark = pytest.mark.django_db


def test_list_is_unpaginated(api_client, url, genre):
    response = api_client.get(url("genre-list"))
    assert response.status_code == 200
    assert response.data == [{"id": genre.id, "name": "Science Fiction", "slug": "science-fiction"}]


def test_create_derives_slug(staff_client, url):
    response = staff_client.post(url("genre-list"), {"name": "Space Opera", "slug": "ignored"})
    assert response.status_code == 201
    assert response.data["slug"] == "space-opera"


def test_retrieve_by_slug_lookup_field(api_client, url, genre):
    response = api_client.get(url("genre-detail", slug="science-fiction"))
    assert response.status_code == 200
    assert response.data["name"] == "Science Fiction"


def test_update_and_delete(staff_client, url, genre):
    response = staff_client.patch(url("genre-detail", slug=genre.slug), {"name": "Sci-Fi"})
    assert response.status_code == 200
    assert response.data["name"] == "Sci-Fi"
    assert response.data["slug"] == "science-fiction"  # slug is stable
    assert staff_client.delete(url("genre-detail", slug=genre.slug)).status_code == 204
