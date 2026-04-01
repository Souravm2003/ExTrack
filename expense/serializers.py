from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Expense, Income, UserProfile


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


# ---------------------------------------------------------------------------
# User Management Serializers
# ---------------------------------------------------------------------------

class UserListSerializer(serializers.ModelSerializer):
    """Read-only serializer for listing users with their role info."""
    role      = serializers.CharField(source='userprofile.role', read_only=True)
    is_active = serializers.BooleanField(source='userprofile.is_active', read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'role', 'is_active', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new user (admin only)."""
    password = serializers.CharField(write_only=True, min_length=8)
    role     = serializers.ChoiceField(
        choices=[r[0] for r in UserProfile.ROLE_CHOICES],
        default='viewer',
        write_only=True,
    )

    class Meta:
        model  = User
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role', 'viewer')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        # Signal creates profile as 'viewer'; override with requested role
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
        if profile.role != role:
            profile.role = role
            profile.save()
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for partial updates to a user's role or active status."""
    class Meta:
        model  = UserProfile
        fields = ['role', 'is_active']

    def validate_role(self, value):
        valid = [r[0] for r in UserProfile.ROLE_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f'Invalid role. Choose from: {", ".join(valid)}'
            )
        return value
