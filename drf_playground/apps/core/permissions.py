"""Reusable permission classes.

DRF permission classes come in two flavours:

* ``has_permission`` runs before the view body, for request-level checks.
* ``has_object_permission`` runs when a single object is retrieved via ``get_object()``,
  for row-level checks. It is *not* called for list endpoints; filter the queryset instead.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Anyone can read, only staff users can write."""

    message = "Only staff members can modify this resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrReadOnly(BasePermission):
    """Anyone can read, only the owner of the object can write.

    The owning field defaults to ``owner``; a view may override it with an ``owner_field`` attribute.
    """

    message = "You do not own this object."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_field = getattr(view, "owner_field", "owner")
        return getattr(obj, owner_field) == request.user
