"""
Custom JWT Authentication for SupabaseUser model
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth.models import AnonymousUser
from .models import SupabaseUser
import logging

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that works with our SupabaseUser model
    """
    
    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token.get('user_id')
            if user_id is None:
                logger.error("Token does not contain user_id")
                return None
                
            user = SupabaseUser.objects.get(id=user_id)
            logger.info(f"✅ JWT Auth: Found user {user.email}")
            return user
            
        except SupabaseUser.DoesNotExist:
            logger.error(f"❌ JWT Auth: User with ID {user_id} not found")
            return None
        except Exception as e:
            logger.error(f"❌ JWT Auth: Error getting user: {e}")
            return None
    
    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            
            if user is None:
                logger.error("❌ JWT Auth: User not found or invalid")
                return None
                
            if not user.is_active:
                logger.error(f"❌ JWT Auth: User {user.email} is not active")
                return None
                
            logger.info(f"✅ JWT Auth: Successfully authenticated {user.email}")
            return (user, validated_token)
            
        except TokenError as e:
            logger.error(f"❌ JWT Auth: Token error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ JWT Auth: Unexpected error: {e}")
            return None
