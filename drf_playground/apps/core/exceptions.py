"""Custom API exceptions and the project-wide exception handler."""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class Conflict(APIException):
    """Raised when the request is valid but conflicts with the current state of the resource."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"


def api_exception_handler(exc, context):
    """Wrap DRF's default handler and add a machine-readable ``code`` next to ``detail``.

    Field validation errors (``{"field": ["msg"]}``) are left untouched so clients keep the standard shape.
    """
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and "detail" in response.data:
        response.data["code"] = _error_code(exc)
    return response


def _error_code(exc) -> str:
    if isinstance(exc, Http404):
        return "not_found"
    if isinstance(exc, PermissionDenied):
        return "permission_denied"
    if isinstance(exc, APIException):
        codes = exc.get_codes()
        return codes if isinstance(codes, str) else "error"
    return "error"
