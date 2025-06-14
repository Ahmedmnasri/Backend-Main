from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import SupabaseUser

User = SupabaseUser


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'phone', 'profile_picture_url',
                  'sector', 'password', 'last_login', 'date_joined', 'auth_user_id', 'is_active')
        read_only_fields = ('id', 'last_login', 'date_joined', 'auth_user_id')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        """Create user and sync to Supabase Auth with provided password."""
        # Extract password before creating user
        password = validated_data.pop('password', None)

        # Create user in Django
        user = User.objects.create(**validated_data)

        # Store password temporarily for signal to use
        if password:
            user._temp_password = password

        return user

    def update(self, instance, validated_data):
        """Update user (password handled by Supabase)."""
        # Remove password from validated_data since it's handled by Supabase
        validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for User Profile (limited data for frontend)."""

    full_name = serializers.SerializerMethodField()
    sector_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name', 'role',
                  'phone', 'profile_picture_url', 'sector', 'sector_name')
        read_only_fields = ('id', 'email', 'role', 'sector', 'sector_name')

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_sector_name(self, obj):
        if obj.sector:
            return obj.sector.name
        return None


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user data in response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['name'] = user.get_full_name()

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add extra responses
        user = self.user
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'name': user.get_full_name(),
            'role': user.role,
        }

        if user.sector:
            data['user']['sector'] = {
                'id': user.sector.id,
                'name': user.sector.name
            }

        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        # Check if user with this email exists
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            # We don't want to reveal if a user exists or not for security reasons
            # So we'll just pass silently
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value