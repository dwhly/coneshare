from django.conf import settings
from rest_framework import permissions
from core.models import APIKey


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to organization admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin')


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to all authenticated users,
    but restricts mutating operations (POST, PUT, PATCH, DELETE) to organization admin users.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(getattr(request.user, 'role', '') == 'admin')


class APIKeyTierPermission(permissions.BasePermission):
    """
    DRF permission class that enforces API key scope tiers (read_only, read_write, full_access).
    Placed in the Permission phase to guarantee HTTP 403 response without breaking 401 challenge headers.
    """
    message = "API key tier permissions do not permit this operation."

    def has_permission(self, request, view):
        if getattr(settings, 'DEALROOM_ENABLED', False):
            return True  # dealroom.hooks is the single operation-ID tier boundary.
        if not isinstance(request.auth, APIKey):
            return True  # Request not authenticated via API Key (e.g. Session/JWT)

        tier = request.auth.tier
        method = request.method.upper()

        if tier == 'read_only' and method not in ('GET', 'HEAD', 'OPTIONS'):
            self.message = f"API key tier 'read_only' does not permit {method} requests."
            return False

        if tier == 'read_write':
            if method == 'DELETE':
                self.message = "API key tier 'read_write' does not permit DELETE requests."
                return False

            # API key management requires 'full_access' tier
            if getattr(view, 'basename', None) == 'api-key' and method not in ('GET', 'HEAD', 'OPTIONS'):
                self.message = "API key tier 'read_write' does not permit managing API keys. 'full_access' tier is required."
                return False

            # Administrative mutations require 'full_access' tier
            view_module = getattr(view, '__module__', '')
            is_admin_view = 'admin_views' in view_module or any(
                perm is IsAdmin or (isinstance(perm, type) and issubclass(perm, IsAdmin))
                for perm in getattr(view, 'permission_classes', [])
            )
            if is_admin_view and method not in ('GET', 'HEAD', 'OPTIONS'):
                self.message = "API key tier 'read_write' does not permit administrative modifications. 'full_access' tier is required."
                return False

        return True
