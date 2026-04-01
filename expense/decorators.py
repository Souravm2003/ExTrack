"""
Role-based decorators for standard Django (HTML) views.
For DRF @api_view endpoints, use permission classes from permissions.py instead.
"""
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout


def require_role(*allowed_roles):
    """
    Restrict a view to users with one of the specified roles.

    Usage:
        @require_role('admin')
        @require_role('analyst', 'admin')

    - Redirects to login if unauthenticated.
    - Deactivates session and redirects to login if profile is inactive.
    - Returns JSON 403 for AJAX/API requests; redirects to dashboard for HTML.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(
                user=request.user, defaults={'role': 'viewer'}
            )

            if not profile.is_active:
                logout(request)
                messages.error(request, 'Your account has been deactivated. Contact an administrator.')
                return redirect('login')

            if profile.role not in allowed_roles:
                is_api = (
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    or 'application/json' in request.headers.get('Accept', '')
                )
                if is_api:
                    return JsonResponse({
                        'error': 'Permission denied',
                        'detail': f'Required role: {" or ".join(r.title() for r in allowed_roles)}',
                        'your_role': profile.role,
                    }, status=403)
                messages.error(
                    request,
                    f'Access denied. Required role: {" or ".join(r.title() for r in allowed_roles)}.'
                )
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
