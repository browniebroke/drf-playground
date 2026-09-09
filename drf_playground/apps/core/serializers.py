from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email", "is_staff"]
        read_only_fields = fields


class StatsSerializer(serializers.Serializer):
    """Plain (non-model) serializer used purely to shape and document an output payload."""

    books = serializers.IntegerField()
    copies = serializers.IntegerField()
    authors = serializers.IntegerField()
    active_loans = serializers.IntegerField()
    members = serializers.IntegerField()
