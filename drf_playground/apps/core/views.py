"""Lowest-level DRF view styles: function-based ``@api_view`` and class-based ``APIView``."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_playground.apps.catalog.models import Author, Book, Copy
from drf_playground.apps.core.serializers import StatsSerializer, UserSerializer
from drf_playground.apps.library.models import Loan


@extend_schema(
    responses=inline_serializer("Ping", {"ping": serializers.CharField(), "version": serializers.CharField()})
)
@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request, **kwargs):
    """Function-based view. ``request`` is a DRF ``Request``; ``Response`` handles content negotiation.

    URL kwargs (``version`` from the versioned prefix, ``format`` from suffix patterns) arrive in ``kwargs``.
    """
    return Response({"ping": "pong", "version": request.version})


class WhoAmIView(APIView):
    """Class-based view: one method per HTTP verb, explicit permission classes."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, **kwargs):
        return Response(UserSerializer(request.user).data)


class StatsView(APIView):
    permission_classes = [AllowAny]
    serializer_class = StatsSerializer  # used by drf-spectacular for the response schema

    def get(self, request, **kwargs):
        data = {
            "books": Book.objects.count(),
            "copies": Copy.objects.count(),
            "authors": Author.objects.count(),
            "active_loans": Loan.objects.filter(returned_at__isnull=True).count(),
            "members": get_user_model().objects.count(),
        }
        return Response(StatsSerializer(data).data)
