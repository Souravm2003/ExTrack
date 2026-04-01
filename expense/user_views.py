"""
User Management API — Admin only
=================================
Endpoints:
  GET    /api/users/           list all users       (admin)
  POST   /api/users/create/    create a user        (admin)
  GET    /api/users/me/        own profile          (all roles)
  GET    /api/users/<pk>/      user detail          (admin)
  PATCH  /api/users/<pk>/      update role/status   (admin)
  DELETE /api/users/<pk>/      deactivate user      (admin)
"""

from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from .models import UserProfile
from .permissions import IsAdminRole, IsViewerOrAbove
from .serializers import UserListSerializer, UserCreateSerializer, UserProfileUpdateSerializer


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'viewer'})
    return profile


# ---------------------------------------------------------------------------
# Own-profile endpoint (all roles)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsViewerOrAbove])
def my_profile(request):
    """Returns the current user's profile and role."""
    profile = _get_profile(request.user)
    return Response({
        'id':          request.user.id,
        'username':    request.user.username,
        'email':       request.user.email,
        'role':        profile.role,
        'is_active':   profile.is_active,
        'date_joined': request.user.date_joined,
    })


# ---------------------------------------------------------------------------
# Admin: list + create users
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAdminRole])
def list_users(request):
    """
    List all users. Supports optional query params:
      ?role=viewer|analyst|admin
      ?is_active=true|false
    """
    users = User.objects.select_related('userprofile').all().order_by('id')

    role_filter   = request.query_params.get('role')
    active_filter = request.query_params.get('is_active')

    if role_filter:
        valid = [r[0] for r in UserProfile.ROLE_CHOICES]
        if role_filter not in valid:
            return Response(
                {'error': f'Invalid role. Choose from: {", ".join(valid)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        users = users.filter(userprofile__role=role_filter)

    if active_filter is not None:
        is_active = active_filter.lower() in ('true', '1', 'yes')
        users = users.filter(userprofile__is_active=is_active)

    serializer = UserListSerializer(users, many=True)
    return Response({'count': users.count(), 'results': serializer.data})


@api_view(['POST'])
@permission_classes([IsAdminRole])
def create_user_api(request):
    """
    Create a new user with a specified role.
    Body: { username, password, email (optional), role (viewer|analyst|admin) }
    """
    serializer = UserCreateSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        profile = _get_profile(user)
        return Response({
            'id':       user.id,
            'username': user.username,
            'email':    user.email,
            'role':     profile.role,
            'message':  f'User "{user.username}" created with role "{profile.role}".',
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Admin: retrieve / update / deactivate a single user
# ---------------------------------------------------------------------------

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAdminRole])
def manage_user(request, pk):
    """
    GET    — retrieve user details
    PATCH  — update role and/or is_active  { role?, is_active? }
    DELETE — soft-deactivate (sets is_active=False, never destroys data)
    """
    try:
        user = User.objects.select_related('userprofile').get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Prevent self-modification via this endpoint
    if request.method in ('PATCH', 'DELETE') and user == request.user:
        return Response(
            {'error': 'You cannot modify your own account via this endpoint.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = _get_profile(user)

    if request.method == 'GET':
        return Response({
            'id':          user.id,
            'username':    user.username,
            'email':       user.email,
            'role':        profile.role,
            'is_active':   profile.is_active,
            'date_joined': user.date_joined,
            'last_login':  user.last_login,
        })

    if request.method == 'PATCH':
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            profile.refresh_from_db()
            return Response({
                'id':        user.id,
                'username':  user.username,
                'role':      profile.role,
                'is_active': profile.is_active,
                'message':   'User updated successfully.',
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        profile.is_active = False
        profile.save()
        return Response(
            {'message': f'User "{user.username}" has been deactivated.'},
            status=status.HTTP_200_OK,
        )
