"""
DRF Permission Classes for Role-Based Access Control.
Used with @permission_classes([...]) on @api_view endpoints.
"""
from rest_framework.permissions import BasePermission


def _get_profile(user):
    from .models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'viewer'})
    return profile


class IsActiveUser(BasePermission):
    """Base: user must be authenticated and have an active profile."""
    message = 'Your account is inactive or not found.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _get_profile(request.user).is_active


class IsViewerOrAbove(IsActiveUser):
    """Any active authenticated user (viewer, analyst, admin)."""
    message = 'Active account required.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _get_profile(request.user).role in ('viewer', 'analyst', 'admin')


class IsAnalystOrAbove(IsActiveUser):
    """Analyst or Admin only."""
    message = 'Analyst or Admin role required.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _get_profile(request.user).role in ('analyst', 'admin')


class IsAdminRole(IsActiveUser):
    """Admin role only."""
    message = 'Admin role required.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _get_profile(request.user).role == 'admin'
