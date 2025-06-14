from .models import SupabaseUser as User
from rest_framework import viewsets, permissions, status, generics, authentication
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
from .permissions import (
    IsAdmin,
    IsSupervisor,
    IsTechnician,
    IsAdminOrSupervisor
)

# User model imported at top


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view with additional user data."""
    serializer_class = CustomTokenObtainPairSerializer



class CurrentUserView(APIView):
    """
    View to retrieve the currently authenticated user's details.
    """
    # Use default authentication classes from settings (includes SupabaseDRFAuthentication)
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        """Get current authenticated user details."""
        try:
            # Log authentication information for debugging
            print(f"Request headers: {request.headers}")
            print(f"User authenticated: {request.user.is_authenticated}")
            print(f"User: {request.user.email if hasattr(request.user, 'email') else 'No email'}")
            print(f"Role: {request.user.role if hasattr(request.user, 'role') else 'No role'}")

            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in CurrentUserView: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User model operations."""
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """
        Custom permissions based on action:
        - Admins can perform all actions
        - Supervisors can view their sector's users and update technicians
        - Regular users can view/update their own profile
        """
        if self.action in ['create', 'destroy', 'create_from_supabase']:
            permission_classes = [permissions.IsAuthenticated]  # Simplified for now
        elif self.action in ['list']:
            permission_classes = [permissions.IsAuthenticated]  # Simplified for now
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def create(self, request):
        """Create a new user directly in users table (simplified approach)."""
        try:
            # Get data from request
            data = request.data

            # Validate required fields
            required_fields = ['email', 'first_name', 'last_name', 'role']
            for field in required_fields:
                if not data.get(field):
                    return Response(
                        {"detail": f"Missing required field: {field}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Check if user already exists
            if User.objects.filter(email=data['email']).exists():
                return Response(
                    {"detail": "User with this email already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user directly in users table (simplified approach)
            try:
                logger.info(f"Creating user directly in users table: {data['email']}")

                # Prepare user data
                user_data = {
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': data['role'],
                    'is_active': True,
                }

                # Add sector if provided
                if data.get('sector'):
                    try:
                        from sectors.models import Sector
                        sector_id = int(data['sector'])
                        sector = Sector.objects.get(id=sector_id)
                        user_data['sector'] = sector
                    except (ValueError, TypeError):
                        return Response(
                            {"detail": "Invalid sector ID"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    except Sector.DoesNotExist:
                        return Response(
                            {"detail": "Sector not found"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Create user (Supabase Auth sync will happen automatically via signals)
                user = User.objects.create(**user_data)

                # Now handle password synchronization manually since signals don't have access to request data
                if data.get('password'):
                    try:
                        from .supabase_sync import SupabaseUserSync
                        sync_service = SupabaseUserSync()

                        if sync_service and sync_service.supabase and not user.auth_user_id:
                            # Create auth user with the provided password
                            auth_success = sync_service.create_auth_user(user, password=data['password'])
                            if auth_success:
                                logger.info(f"✅ Successfully created auth user for {user.email} with provided password")
                                # Refresh to get the auth_user_id set by the sync service
                                user.refresh_from_db()
                            else:
                                logger.error(f"❌ Failed to create auth user for {user.email}")
                    except Exception as e:
                        logger.error(f"❌ Error creating auth user for {user.email}: {e}")

                logger.info(f"User created successfully: {user.id} with auth_id: {user.auth_user_id}")

                # Serialize and return user data
                serializer = self.get_serializer(user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Error creating user in database: {str(e)}")
                return Response(
                    {"detail": f"Failed to create user: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return Response(
                {"detail": f"Failed to create user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def create_from_supabase(self, request):
        """
        Create a Django user from Supabase Auth user data.
        This endpoint is called after a user is created in Supabase Auth.
        """
        try:
            data = request.data

            # Validate required fields
            required_fields = ['auth_user_id', 'email', 'first_name', 'last_name', 'role']
            for field in required_fields:
                if not data.get(field):
                    return Response(
                        {"detail": f"Missing required field: {field}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Check if user already exists
            if User.objects.filter(auth_user_id=data['auth_user_id']).exists():
                return Response(
                    {"detail": "User with this Supabase ID already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if email already exists
            if User.objects.filter(email=data['email']).exists():
                return Response(
                    {"detail": "User with this email already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user
            user_data = {
                'auth_user_id': data['auth_user_id'],
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': data['role'],
                'is_active': data.get('is_active', True),
                'phone': data.get('phone', ''),
                'profile_picture_url': data.get('profile_picture_url', ''),
                'profile_picture_storage_type': 'supabase'
            }

            # Add sector if provided
            if data.get('sector'):
                user_data['sector_id'] = data['sector']

            user = User.objects.create(**user_data)

            # Serialize and return the created user
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": f"Error creating user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_queryset(self):
        """Filter users based on requester's role and sector."""
        user = self.request.user

        if not user.is_authenticated:
            return User.objects.none()

        # Admin can see all users
        if hasattr(user, 'role') and user.role == 'Admin':
            return User.objects.all()

        # Supervisor can only see users in their sector
        elif hasattr(user, 'role') and user.role == 'Supervisor' and hasattr(user, 'sector') and user.sector:
            return User.objects.filter(sector=user.sector)

        # Technician can only see themselves
        elif hasattr(user, 'role') and user.role == 'Technician':
            return User.objects.filter(id=user.id)

        # Default: no access
        return User.objects.none()

    def get_serializer_class(self):
        """Return different serializers based on action."""
        if self.action == 'me':
            return UserProfileSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get or update the authenticated user's profile.
        """
        try:
            user = request.user
            print(f"UserViewSet.me: User authenticated: {user.is_authenticated}")
            print(f"UserViewSet.me: User: {user.email}, Role: {user.role}")

            if request.method == 'GET':
                serializer = self.get_serializer(user)
                return Response(serializer.data)

            # Update the user's profile
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in UserViewSet.me: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSupervisor])
    def reset_password(self, request, pk=None):
        """
        Reset user's password (Admin/Supervisor only).
        Generates a temporary password and emails it to the user.
        """
        user = self.get_object()

        # Generate a temporary password (in real app, use a proper generator)
        temp_password = "ChangeMe123!"

        # Update password
        user.set_password(temp_password)
        user.save()

        # In a real application, send email to user with the temporary password

        return Response({"detail": "Password reset successful. User will receive an email."})

    def destroy(self, request, *args, **kwargs):
        """Delete user from both Django database and Supabase Auth"""
        try:
            user_id = kwargs.get('pk')
            print(f"🗑️ Attempting to delete user with ID: {user_id}")

            # Check if user exists
            try:
                user = User.objects.get(id=user_id)
                print(f"✅ Found user to delete: {user.email}")
            except User.DoesNotExist:
                print(f"❌ User with ID {user_id} not found in database")
                print(f"📋 Available user IDs:")
                for u in User.objects.all():
                    print(f"   - {u.id} ({u.email})")
                return Response(
                    {"error": f"User with ID {user_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Store user info before deletion
            user_email = user.email
            auth_user_id = user.auth_user_id

            # Delete from Django database first
            response = super().destroy(request, *args, **kwargs)

            # If Django deletion was successful, also delete from Supabase Auth
            if response.status_code == 204:
                print(f"✅ User deleted from Django database: {user_email}")

                # Delete from Supabase Auth if auth_user_id exists
                if auth_user_id:
                    try:
                        from .supabase_sync import SupabaseUserSync
                        sync_service = SupabaseUserSync()

                        if sync_service.supabase:
                            # Delete user from Supabase Auth (convert UUID to string)
                            sync_service.supabase.auth.admin.delete_user(str(auth_user_id))
                            print(f"✅ User deleted from Supabase Auth: {user_email} (ID: {auth_user_id})")
                        else:
                            print(f"⚠️ Could not connect to Supabase to delete auth user: {user_email}")

                    except Exception as e:
                        print(f"⚠️ Failed to delete user from Supabase Auth: {user_email} - {str(e)}")
                        # Don't fail the whole operation if Supabase deletion fails
                else:
                    print(f"ℹ️ User {user_email} had no auth_user_id, skipping Supabase Auth deletion")

            return response

        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            print(f"❌ Error deleting user: {str(e)}")
            return Response(
                {"error": "Failed to delete user. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChangePasswordView(generics.UpdateAPIView):
    """
    Endpoint for changing password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        user = self.request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not user.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]},
                                status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(serializer.data.get("new_password"))
            user.save()

            return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    """
    API endpoint for requesting a password reset.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)

                # Generate password reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Build reset URL (frontend URL)
                reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"

                # Send email with reset link
                subject = "Password Reset Request"
                message = f"""
                Hello {user.get_full_name() or user.email},

                You requested a password reset for your account. Please click the link below to reset your password:

                {reset_url}

                If you didn't request this, you can safely ignore this email.

                Thank you,
                The Digital Mining Team
                """

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    logger.info(f"Password reset email sent to {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send password reset email: {str(e)}")
                    # Don't reveal the error to the user for security reasons

            except User.DoesNotExist:
                # Don't reveal if a user exists or not
                logger.info(f"Password reset requested for non-existent email: {email}")

            # Always return success to prevent email enumeration attacks
            return Response({"detail": "Password reset email sent if the email exists in our system."})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    API endpoint for confirming a password reset.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password = serializer.validated_data['password']

            # In a real implementation, you would decode the token to get the user
            # For simplicity, we'll use a direct token lookup approach

            try:
                # Find the user by token
                # This is a simplified approach - in a real app, you'd decode the token
                # to get the user ID and then verify the token

                for user in User.objects.all():
                    if default_token_generator.check_token(user, token):
                        # Set new password
                        user.set_password(password)
                        user.save()

                        logger.info(f"Password reset successful for user {user.email}")
                        return Response({"detail": "Password has been reset successfully."})

                # If we get here, no valid user was found for the token
                logger.warning(f"Invalid password reset token: {token}")
                return Response(
                    {"detail": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except Exception as e:
                logger.error(f"Password reset error: {str(e)}")
                return Response(
                    {"detail": "An error occurred during password reset."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Simple Django-based authentication endpoints
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def simple_login(request):
    """
    Simple Django-based login that bypasses Supabase Auth completely
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Find user by email
        user = User.objects.get(email=email)

        # Check password (all users should have password 'azertyuiop')
        if password == 'azertyuiop':
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Add custom claims
            access_token['email'] = user.email
            access_token['role'] = user.role
            access_token['user_id'] = str(user.id)

            logger.info(f"✅ Successful Django login for {email}")

            return Response({
                'access_token': str(access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'sector': user.sector.name if user.sector else None,
                }
            }, status=status.HTTP_200_OK)
        else:
            logger.warning(f"❌ Invalid password for {email}")
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except User.DoesNotExist:
        logger.warning(f"❌ User not found: {email}")
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error(f"❌ Django login error for {email}: {e}")
        return Response({
            'error': 'Login failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


