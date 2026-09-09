import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_api_root_requires_auth():
    response = APIClient().get(reverse("core:api-root"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_api_root_authenticated(django_user_model):
    user = django_user_model.objects.create_user(username="alice", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("core:api-root"))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}
