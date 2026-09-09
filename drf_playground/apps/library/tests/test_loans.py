import datetime as dt

import pytest
from django.utils import timezone
from rest_framework.throttling import ScopedRateThrottle

from drf_playground.apps.catalog.models import Copy
from drf_playground.apps.library.models import Loan

pytestmark = pytest.mark.django_db


def test_anonymous_cannot_use_loans(api_client, url, copy):
    assert api_client.get(url("loan-list")).status_code == 401
    assert api_client.post(url("loan-list"), {"copy": copy.pk}).status_code == 401


def test_checkout_sets_borrower_and_default_due_date(auth_client, user, url, copy):
    response = auth_client.post(url("loan-list"), {"copy": copy.pk})
    assert response.status_code == 201, response.data
    assert response.data["borrower"] == user.username
    assert response.data["book_title"] == "The Left Hand of Darkness"
    assert response.data["due_on"] == (timezone.localdate() + dt.timedelta(days=14)).isoformat()
    assert response.data["is_active"] is True
    assert response.data["is_overdue"] is False


def test_checkout_of_loaned_copy_fails_validation(auth_client, other_client, url, copy):
    assert other_client.post(url("loan-list"), {"copy": copy.pk}).status_code == 201
    response = auth_client.post(url("loan-list"), {"copy": copy.pk})
    assert response.status_code == 400
    assert response.data["copy"] == ["This copy is currently on loan."]


def test_due_date_must_be_in_future(auth_client, url, copy):
    response = auth_client.post(url("loan-list"), {"copy": copy.pk, "due_on": "2000-01-01"})
    assert response.status_code == 400
    assert "due_on" in response.data


def test_return_action_and_custom_conflict_exception(auth_client, url, copy):
    loan_id = auth_client.post(url("loan-list"), {"copy": copy.pk}).data["id"]
    response = auth_client.post(url("loan-return-loan", pk=loan_id))
    assert response.status_code == 200
    assert response.data["is_active"] is False
    assert response.data["returned_at"] is not None

    response = auth_client.post(url("loan-return-loan", pk=loan_id))
    assert response.status_code == 409
    assert response.data == {"detail": "This loan has already been returned.", "code": "conflict"}


def test_queryset_is_scoped_to_borrower_unless_staff(auth_client, other_client, staff_client, url, book):
    for index, client in enumerate((auth_client, other_client)):
        copy = Copy.objects.create(book=book, barcode=f"BC-{index}")
        assert client.post(url("loan-list"), {"copy": copy.pk}).status_code == 201

    assert [loan["barcode"] for loan in auth_client.get(url("loan-list")).data["results"]] == ["BC-0"]
    assert len(staff_client.get(url("loan-list")).data["results"]) == 2

    other_loan = Loan.objects.get(copy__barcode="BC-1")
    assert auth_client.get(url("loan-detail", pk=other_loan.pk)).status_code == 404
    assert staff_client.get(url("loan-detail", pk=other_loan.pk)).status_code == 200


def test_cursor_pagination(auth_client, user, url, book):
    for index in range(12):
        copy = Copy.objects.create(book=book, barcode=f"BC-{index:02d}")
        Loan.objects.create(copy=copy, borrower=user, due_on=timezone.localdate() + dt.timedelta(days=14))

    response = auth_client.get(url("loan-list"))
    assert response.status_code == 200
    assert "count" not in response.data  # cursor pagination has no total
    assert len(response.data["results"]) == 10
    assert "cursor=" in response.data["next"]

    response = auth_client.get(response.data["next"])
    assert len(response.data["results"]) == 2
    assert response.data["next"] is None
    assert response.data["previous"] is not None


def test_status_filter_and_overdue_action(auth_client, user, url, book):
    active = Copy.objects.create(book=book, barcode="BC-active")
    overdue = Copy.objects.create(book=book, barcode="BC-overdue")
    returned = Copy.objects.create(book=book, barcode="BC-returned")
    Loan.objects.create(copy=active, borrower=user, due_on=timezone.localdate() + dt.timedelta(days=1))
    Loan.objects.create(copy=overdue, borrower=user, due_on=timezone.localdate() - dt.timedelta(days=1))
    Loan.objects.create(copy=returned, borrower=user, due_on=timezone.localdate(), returned_at=timezone.now())

    def barcodes(name, **params):
        return sorted(loan["barcode"] for loan in auth_client.get(url(name), params).data["results"])

    assert barcodes("loan-list", status="active") == ["BC-active", "BC-overdue"]
    assert barcodes("loan-list", status="returned") == ["BC-returned"]
    assert barcodes("loan-list", overdue="true") == ["BC-overdue"]
    assert barcodes("loan-overdue") == ["BC-overdue"]


def test_scoped_throttle_on_checkout(auth_client, url, book, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"checkout": "1/minute"})
    first, second = (Copy.objects.create(book=book, barcode=f"BC-{i}") for i in range(2))

    assert auth_client.post(url("loan-list"), {"copy": first.pk}).status_code == 201
    response = auth_client.post(url("loan-list"), {"copy": second.pk})
    assert response.status_code == 429
    assert response.data["code"] == "throttled"
    assert "Retry-After" in response
    # Other actions are not affected by the scoped throttle.
    assert auth_client.get(url("loan-list")).status_code == 200
