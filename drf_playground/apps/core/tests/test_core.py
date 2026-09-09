import base64

import pytest

pytestmark = pytest.mark.django_db


def test_api_root_lists_router_endpoints(api_client, url):
    response = api_client.get(url("api-root"))
    assert response.status_code == 200
    assert set(response.data) >= {"authors", "books", "copies", "loans", "reviews", "shelves"}
    assert response.data["books"].endswith("/api/v1/books/")


def test_function_view_is_public_and_versioned(api_client, url):
    response = api_client.get(url("ping"))
    assert response.status_code == 200
    assert response.data == {"ping": "pong", "version": "v1"}


def test_format_suffix_selects_renderer(api_client):
    response = api_client.get("/api/v1/ping.json")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")


def test_unknown_version_is_rejected(api_client):
    response = api_client.get("/api/v2/ping/")
    assert response.status_code == 404
    assert response.data["code"] == "not_found"


def test_apiview_requires_authentication(api_client, url):
    response = api_client.get(url("whoami"))
    # TokenAuthentication is first in the list, so anonymous users get 401 (with WWW-Authenticate), not 403.
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Token"
    assert response.data["code"] == "not_authenticated"


def test_whoami_returns_current_user(auth_client, user, url):
    response = auth_client.get(url("whoami"))
    assert response.status_code == 200
    assert response.data["username"] == user.username
    assert response.data["is_staff"] is False


def test_token_authentication_flow(api_client, user, url):
    response = api_client.post(url("obtain-token"), {"username": "reader", "password": "password"})
    assert response.status_code == 200
    token = response.data["token"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    response = api_client.get(url("whoami"))
    assert response.status_code == 200
    assert response.data["username"] == "reader"


def test_basic_authentication(api_client, user, url):
    credentials = base64.b64encode(b"reader:password").decode()
    api_client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")
    response = api_client.get(url("whoami"))
    assert response.status_code == 200


def test_stats_uses_plain_serializer(api_client, copy, url):
    response = api_client.get(url("stats"))
    assert response.status_code == 200
    assert response.data == {"books": 1, "copies": 1, "authors": 1, "active_loans": 0, "members": 0}


def test_custom_exception_handler_adds_code(api_client, url):
    response = api_client.get(url("book-detail", pk=999))
    assert response.status_code == 404
    assert response.data["code"] == "not_found"
    assert "detail" in response.data


def test_openapi_schema_and_docs(api_client, url):
    schema = api_client.get(url("schema"))
    assert schema.status_code == 200
    assert b"openapi" in schema.content
    assert b"/api/v1/books/" in schema.content
    assert api_client.get(url("docs")).status_code == 200
